# AI prompt and architecture audit

**Tool:** ChatGPT (Codex). The input was the assignment brief. Its exact architecture prompt is reproduced in [the prompt appendix](docs/assignment-prompt.md). Docker Compose was selected for the primary demonstration because the target machine already has Docker Desktop. Kubernetes manifests provide the HPA alternative.

**Draft artifact:** [Initial design excerpt](docs/initial-draft.txt). This compact review sketch preserves the draft decisions and pseudo-code. It is not an executed earlier release. The QA evidence was collected from the final implementation.

| Review item | Draft observation | Change in the final system |
|---|---|---|
| Cache location | The design correctly chose an external Redis service. | All worker replicas read the same Redis key. The QA probe sends the same lookup to different workers and compares the actual response bodies. |
| Expiration | The draft called SET without an expiration. A computed report could remain stale until eviction. | The worker writes the value and its 60-second expiration together using SET with EX. QA records a decreasing TTL and checks eventual expiry. |
| Scaling stability | The draft immediately decreased capacity whenever CPU dropped below 50%. At 51%, then 49%, the pool could alternate between two and four workers. | The Compose policy requires two high samples for growth. A separate 20% threshold and 30 continuous low seconds protect scale-in. A rebound resets the timer. |
| CPU denominator | A raw CPU percentage is ambiguous for a fractional-core worker. | Compose reserves 0.20 core per worker and caps it at 0.50. The controller divides actual CPU-seconds per wall second by the total requested cores. The Kubernetes container defines requests.cpu: 200m and its HPA targets 50% of that request. |
| Verification | A fixed sleep alone would produce a miss without meaningfully increasing CPU. | Cold reports also perform bounded CPU work. The load tool uses fresh keys and records status codes. Successful repeat reads skip both the delay and computation. |

The cooldown regression test feeds measurements just below and above the low threshold. The integration run measures real CPU across worker processes and records the first high samples, promotions, cooldown and return to baseline. See the README for platform-specific verification limits.
