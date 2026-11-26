"""Cache-aside report service. The origin is a deterministic simulated query."""
import asyncio
import hashlib
import json
import os
import re
import socket
import time

from aiohttp import web
from redis.asyncio import Redis
from redis.exceptions import RedisError

NAME = os.getenv("INSTANCE_ID", socket.gethostname())
TTL = 60
VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,80}")


async def cache_resources(app):
    client = Redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
                            max_connections=96, socket_connect_timeout=1, socket_timeout=2)
    app["redis"] = client
    app["compute_slots"] = asyncio.Semaphore(4)
    yield
    await client.aclose()


async def data(request):
    item = request.match_info["id"]
    if not VALID_ID.fullmatch(item):
        raise web.HTTPBadRequest(text="Use 1–80 letters, numbers, underscores or hyphens.")
    key = "report:v1:" + item
    client = request.app["redis"]
    try:
        cached = await client.get(key)
        if cached is not None:
            return web.Response(body=cached, content_type="application/json",
                                headers={"X-Cache":"HIT", "X-Replica":NAME,"Cache-Control":"no-store"})
        await asyncio.sleep(0.50)
        async with request.app["compute_slots"]:
            digest = await asyncio.to_thread(hashlib.pbkdf2_hmac, "sha256", item.encode(), b"report-v1", 90000)
        payload = json.dumps({"report":item, "checksum":digest.hex()}).encode()
        await client.set(key, payload, ex=TTL)
        return web.Response(body=payload, content_type="application/json",
                            headers={"X-Cache":"MISS", "X-Replica":NAME,"Cache-Control":"no-store"})
    except RedisError:
        raise web.HTTPServiceUnavailable(text="Shared cache unavailable", headers={"Retry-After":"2"})


async def health(request):
    try:
        await request.app["redis"].ping()
    except RedisError:
        raise web.HTTPServiceUnavailable(text="Redis unavailable")
    return web.json_response({"ready":True, "worker":NAME, "cpu_seconds":time.process_time()})


def create():
    app = web.Application()
    app.cleanup_ctx.append(cache_resources)
    app.router.add_get("/api/data/{id}", data)
    app.router.add_get("/healthz", health)
    return app


if __name__ == "__main__":
    web.run_app(create(), port=int(os.getenv("PORT", "8000")), access_log=None)
