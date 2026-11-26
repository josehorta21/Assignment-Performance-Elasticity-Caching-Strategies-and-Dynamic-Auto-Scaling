import asyncio
import os
import statistics
import time
import uuid

from aiohttp import ClientSession
from redis.asyncio import Redis


async def check():
    key = "qa-" + uuid.uuid4().hex[:10]
    cache = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    async with ClientSession() as client:
        async def lookup():
            started = time.perf_counter()
            async with client.get("http://127.0.0.1:8087/api/data/"+key) as r:
                body = await r.json()
                assert r.status==200 and body["report"]==key
                return (r.headers["X-Cache"], r.headers["X-Replica"],
                        round((time.perf_counter()-started)*1000,2), body)
        try:
            miss=await lookup()
            hits=[await lookup() for _ in range(8)]
            ttl1=await cache.ttl("report:v1:"+key)
            await asyncio.sleep(2.1)
            ttl2=await cache.ttl("report:v1:"+key)
        finally:
            await cache.aclose()
    median=round(statistics.median(r[2] for r in hits),2)
    result={"key":key,"miss_ms":miss[2],"first_hit_ms":hits[0][2],"median_hit_ms":median,
            "miss_replica":miss[1],"hit_replicas": sorted({r[1] for r in hits}),"ttl_seconds":[ttl1,ttl2]}
    print(result,flush=True)
    assert miss[0]=="MISS" and miss[2]>=500 and hits[0][2]<15 and median<15
    assert all(r[0]=="HIT" and r[3]==miss[3] for r in hits)
    assert any(r[1]!=miss[1] for r in hits) and 0<ttl2<ttl1<=60
    return result


if __name__=="__main__":
    asyncio.run(check())
