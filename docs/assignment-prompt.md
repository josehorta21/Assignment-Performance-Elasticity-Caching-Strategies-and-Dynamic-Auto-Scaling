Act as a senior cloud infrastructure and scalability architect. I need to build a high-performance, auto-scaling web application with an external distributed caching layer.

The project must include:

1. Web Service (Node.js, Python FastAPI, or Go):

   - An endpoint (/api/data/:id or /api/compute) that simulates an expensive operation (e.g., a complex DB query with a 500ms delay or mathematical computation).

   - Implements the Cache-Aside pattern using an external Redis instance:

     \* Check Redis for the key.

     \* On Cache Hit: Return data immediately with an HTTP header 'X-Cache: HIT'.

     \* On Cache Miss: Run the slow operation, store the result in Redis with a 60-second TTL, and return with 'X-Cache: MISS'.

2. Distributed Caching Layer:

   - An external Redis service (configured in Docker Compose or Kubernetes).

3. Dynamic Auto-Scaling (Choose Option A or Option B):

   - Option A (Kubernetes / Minikube): A Deployment with resource requests/limits (CPU/RAM), a metrics-server setup, and a HorizontalPodAutoscaler (HPA) targeting 50% CPU utilization (min 2, max 6 replicas).

   - Option B (Docker Compose / Cloud): Multi-container service with an automated scaling script or target-tracking policy based on CPU/request load.

4. Load Generation Tool:

   - A lightweight script (e.g., using Autocannon, k6, Apache Bench 'ab', or Python Locust) to generate synthetic traffic spikes and trigger auto-scaling.



Provide the application source code, Redis integration, orchestration/HPA YAML manifests, load-testing script, and step-by-step commands to run and test it.
