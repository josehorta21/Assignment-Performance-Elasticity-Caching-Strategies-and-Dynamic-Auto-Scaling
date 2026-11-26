# QA checklist and measured results

**Run environment:** Linux, Python 3.12, real Redis Server 6.2.14, aiohttp gateway, separate API processes on TCP ports, and headless Chromium. A local actuator started/stopped independent worker processes based on the policy's desired count. The Compose deployment uses Redis 7.4 and applies the same desired count to containers. These numbers describe the measured process deployment. Docker Compose and Minikube runtime results must be captured in the target environment.

| Check | Observed evidence |
|---|---|
| Cold → warm request | Cold lookup **515.59 ms**, first HTTP hit **1.44 ms**, median of eight hits **0.61 ms**. The body stayed identical. Worker 1 created the value. Both workers served it. |
| Real Redis TTL | TTL fell from **60 to 58 seconds**. The initial probe key was absent after the load/cooldown run. A separate redis-cli observation also returned 60 and 58. |
| Trigger CPU and grow | 24 clients issued fresh keys for 32 seconds. The gateway observed **175.4%** of requested CPU on two workers at the 2→4 decision and **77.2%** on four at the 4→6 decision. Six distinct worker IDs became ready. |
| Hold, then shrink | At 01:26:53 UTC the gateway first held six ready workers at low CPU. At 01:27:21 it still held six after 28.1 seconds. It requested two at 01:27:23, and two were ready at 01:27:25. |
| Request outcomes | **1,488 HTTP 200** cold responses. The load client recorded zero failed requests. The gateway health route returned HTTP 200 after scale-in. |
| Browser and logs | Chromium observed 200 responses for the page, status endpoint and both report requests. The form displayed **MISS 517.2 ms** on worker A, then **HIT 13.8 ms** on worker B. Console errors: 0. The process lifecycle check recorded no unexpected exits and no Redis pool errors or tracebacks. |
| Scaling policy tests | Three tests passed: two-sample growth and maximum bound, low-CPU window reset on rebound, and a hold during incomplete samples. |

Raw samples: [fleet and cache evidence](qa-run.json) and [browser and CLI evidence](browser-qa.json). Browser end-to-end duration includes front-end scheduling. The terminal probe measures the HTTP round trip from a client connected to the gateway.

## Repeat on the Mac used for recording

1. Keep `bash scripts/start.sh` running in Terminal A.
2. In Terminal B run `docker compose exec -T gateway python -m scripts.cache_check`. Use the README curl pair and Redis CLI commands to show headers and TTL.
3. Run `docker compose exec -T gateway python -m scripts.verify_scaling --seconds 95`. The verifier requires a CPU signal over 50%, six ready workers, a sustained cooldown, and a return to two. Observe the actual containers with `docker compose ps app`.
4. Open the browser's Console and Network tabs, send a fresh ID twice, and inspect both HTTP responses. Check `curl -fsS http://localhost:8087/healthz` and `docker compose logs --tail=30 app redis gateway`.
5. Report the readings visible in your own recording. A local CPU percentage represents usage relative to the requested share; it may exceed 100%.

The packaged live scaling verifier also passed in a second run against the real process fleet. All seven Kubernetes resources passed strict schema validation against Kubernetes 1.31. The Compose YAML was parsed and its service definitions checked. These checks did not start Docker containers or Kubernetes pods.
