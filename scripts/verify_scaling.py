"""Exercise the running Compose controller and assert observed fleet changes."""
import argparse
import asyncio
import json
import time

from aiohttp import ClientSession
from scripts.load import URL, spike


async def verify(duration, clients=24):
    async with ClientSession() as client:
        async def sample():
            async with client.get(URL+"/status") as r:
                r.raise_for_status()
                return await r.json()
        first=await sample()
        if first["ready"]!=2 or first["desired"]!=2:
            raise SystemExit("Start the Compose controller and wait for two ready replicas.")
        load=asyncio.create_task(spike(duration,clients))
        samples=[]
        last=None
        seen_max=False
        deadline=time.monotonic()+duration+100
        try:
            while time.monotonic()<deadline:
                s=await sample()
                if s.get("time")!=last:
                    last=s.get("time")
                    row={k:s.get(k) for k in ("time","ready","desired","cpu","hold_seconds","reason","workers")}
                    samples.append(row)
                    print(json.dumps(row),flush=True)
                seen_max=seen_max or s["ready"]==6
                if seen_max and load.done() and s["ready"]==2:
                    break
                await asyncio.sleep(.8)
            result=await load
        finally:
            if not load.done():
                load.cancel()
                await asyncio.gather(load,return_exceptions=True)
        assert result.get("200",0)>0 and set(result)=={"200","MISS"},result
        assert {2,6}<={s["ready"] for s in samples}
        assert max(s["cpu"] or 0 for s in samples)>50
        assert any(s["hold_seconds"]>=26 for s in samples) and samples[-1]["ready"]==2
        assert any(s["reason"].startswith("Scale in after 30") for s in samples)
        print("PASS: real CPU spike, six ready workers, cooldown and return to two.",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--seconds",type=int,choices=range(30,101),default=75,metavar="30–100")
    parser.add_argument("--clients",type=int,choices=range(1,33),default=24,metavar="1–32")
    args=parser.parse_args()
    asyncio.run(verify(args.seconds,args.clients))
