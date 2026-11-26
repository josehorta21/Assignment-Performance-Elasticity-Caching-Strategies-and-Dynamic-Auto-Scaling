"""Ready-target discovery, round-robin routing and per-process CPU samples."""
import asyncio
from collections import deque
from contextlib import suppress
import os
from pathlib import Path
import socket
import time

from aiohttp import ClientError, ClientSession, ClientTimeout, web
from app.policy import CPU_REQUEST, Policy

ROOT = Path(__file__).parent
INTERVAL = 2


class Fleet:
    def __init__(self):
        self.policy = Policy()
        self.targets = []
        self.cursor = 0
        self.previous = {}
        self.history = deque(maxlen=150)
        self.snapshot = {"ready":0, "desired":2, "cpu":None, "reason":"Discovering workers",
                         "hold_seconds":0, "workers":[]}

    async def discover(self):
        # The local integration runner writes host:port entries atomically.
        if path := os.getenv("LOCAL_TARGET_FILE"):
            return sorted(set(Path(path).read_text().splitlines()))
        rows = await asyncio.get_running_loop().getaddrinfo(
            os.getenv("WORKER_DNS", "app"), 8000, family=socket.AF_INET, type=socket.SOCK_STREAM)
        return sorted({f"{row[4][0]}:8000" for row in rows})

    async def probe(self, target, client):
        async with client.get(f"http://{target}/healthz", timeout=ClientTimeout(total=1.8)) as r:
            r.raise_for_status()
            return target, await r.json(), time.monotonic()

    async def monitor(self, client):
        while True:
            try:
                targets = await self.discover()
            except (OSError, ValueError):
                targets = []
            results = await asyncio.gather(*(self.probe(t, client) for t in targets), return_exceptions=True)
            valid = [r for r in results if isinstance(r, tuple)]
            current, shares, names = {}, [], []
            for target, stat, moment in valid:
                name = stat["worker"]
                names.append(name)
                value = stat["cpu_seconds"]
                current[name] = (value, moment)
                if name in self.previous:
                    prev, then = self.previous[name]
                    if moment > then and value >= prev:
                        shares.append((value - prev) / (moment - then))
            self.targets = [r[0] for r in valid]
            self.previous = current
            count = len(current)
            cpu = 100 * sum(shares) / (count * CPU_REQUEST) if count and len(shares) == count else None
            now = time.monotonic()
            reason = self.policy.observe(count, cpu, now)
            self.snapshot = dict(ready=count, desired=self.policy.desired,
                cpu=round(cpu,1) if cpu is not None else None, reason=reason,
                hold_seconds=round(now-self.policy.low_since,1) if self.policy.low_since is not None else 0,
                workers=names, time=time.strftime("%H:%M:%S",time.gmtime()))
            if os.getenv("SCALING_MODE") == "hpa":
                self.snapshot.update(desired=None, hold_seconds=None, reason="Kubernetes HPA controls replicas; inspect kubectl get hpa")
            self.history.append(self.snapshot)
            await asyncio.sleep(INTERVAL)

    async def route(self, request):
        if not self.targets:
            raise web.HTTPServiceUnavailable(text="No ready workers")
        targets = self.targets
        start = self.cursor % len(targets)
        self.cursor += 1
        # A single bounded failover retry for this read-only report route.
        for offset in range(min(2, len(targets))):
            target = targets[(start + offset) % len(targets)]
            try:
                async with request.app["client"].get(f"http://{target}"+request.rel_url.raw_path) as r:
                    body = await r.read()
                    headers = {k:r.headers[k] for k in ("X-Cache","X-Replica","Content-Type","Cache-Control","Retry-After") if k in r.headers}
                    return web.Response(body=body,status=r.status,headers=headers)
            except (ClientError, TimeoutError):
                continue
        raise web.HTTPBadGateway(text="Upstream unavailable")


async def services(app):
    async with ClientSession(timeout=ClientTimeout(total=8)) as client:
        app["client"] = client
        task = asyncio.create_task(app["fleet"].monitor(client))
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def home(request):
    return web.FileResponse(ROOT / "index.html")


async def status(request):
    f = request.app["fleet"]
    return web.json_response({**f.snapshot,"history":list(f.history)},headers={"Cache-Control":"no-store"})


async def desired(request):
    return web.Response(text=str(request.app["fleet"].policy.desired))


async def health(request):
    ok = bool(request.app["fleet"].targets)
    return web.json_response({"ready":ok},status=200 if ok else 503)


def create():
    app = web.Application()
    fleet = Fleet()
    app["fleet"] = fleet
    app.cleanup_ctx.append(services)
    for url, handler in [("/",home),("/api/data/{id}",fleet.route),("/status",status),
                         ("/desired",desired),("/healthz",health)]:
        app.router.add_get(url, handler)
    return app


if __name__ == "__main__":
    web.run_app(create(), port=8087, access_log=None)
