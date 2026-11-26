"""Bounded local traffic generator. Fresh keys exercise the simulated origin."""
import argparse
import asyncio
from collections import Counter
import time
import uuid

from aiohttp import ClientError, ClientSession, ClientTimeout

URL = "http://127.0.0.1:8087"


async def spike(seconds=60, clients=24):
    if not 1 <= seconds <= 100 or not 1 <= clients <= 32:
        raise ValueError("Choose 1–100 seconds and 1–32 clients.")
    stop = time.monotonic()+seconds
    prefix = uuid.uuid4().hex[:12]
    counts = Counter()
    async with ClientSession(timeout=ClientTimeout(total=10)) as http:
        async def run(index):
            n = 0
            while time.monotonic() < stop:
                try:
                    async with http.get(f"{URL}/api/data/{prefix}-{index}-{n}") as r:
                        await r.read()
                        counts[str(r.status)] += 1
                        counts[r.headers.get("X-Cache","NO_HEADER")] += 1
                except (ClientError, TimeoutError):
                    counts["transport_error"] += 1
                n += 1
        print(f"Starting {seconds}s of localhost traffic with {clients} clients.", flush=True)
        await asyncio.gather(*(run(i) for i in range(clients)))
    print(dict(counts), flush=True)
    return dict(counts)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--seconds",type=int,default=60)
    parser.add_argument("--clients",type=int,default=24)
    args=parser.parse_args()
    summary=asyncio.run(spike(args.seconds,args.clients))
    if summary.get("200",0)==0 or any(k not in {"200","MISS"} for k in summary):
        raise SystemExit(1)
