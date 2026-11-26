"""Sampling policy shared by the Compose actuator and the integration harness."""
from dataclasses import dataclass

MINIMUM = 2
MAXIMUM = 6
CPU_REQUEST = 0.20
UP = 50.0
DOWN = 20.0
WINDOW = 30.0


@dataclass
class Policy:
    desired: int = MINIMUM
    hot_samples: int = 0
    low_since: float | None = None

    def observe(self, ready, utilization, now):
        if ready != self.desired or utilization is None:
            self.hot_samples = 0
            self.low_since = None
            return "Waiting for ready replicas and a complete CPU sample"
        if utilization > UP:
            self.low_since = None
            self.hot_samples += 1
            if self.hot_samples >= 2 and ready < MAXIMUM:
                self.desired = min(MAXIMUM, ready + 2)
                self.hot_samples = 0
                return "Scale out after two high CPU samples"
            return "High CPU"
        self.hot_samples = 0
        if utilization < DOWN and ready > MINIMUM:
            if self.low_since is None:
                self.low_since = now
            if now - self.low_since >= WINDOW:
                self.desired = MINIMUM
                self.low_since = None
                return "Scale in after 30 continuous low-CPU seconds"
            return "Holding capacity during scale-down cooldown"
        self.low_since = None
        return "Within policy bounds"
