"""Record lightweight local benchmark metadata without retraining the model."""
from __future__ import annotations

import platform
import time
from pathlib import Path


def main() -> None:
    start = time.perf_counter()
    time.sleep(0)
    elapsed = time.perf_counter() - start
    result = f"""# Benchmarks

These are execution measurements for this machine, not model training results.

- Machine: {platform.platform()} ({platform.processor() or 'unknown CPU'})
- Python: {platform.python_version()}
- Benchmark harness overhead: {elapsed:.6f}s
- Streaming throughput and end-to-end Cassandra latency: run with the local Kafka/Cassandra stack and record externally.
- Batch classifier comparison: see [model/metrics.md](../model/metrics.md); it is not re-run here.
"""
    path = Path(__file__).with_name("results.md")
    path.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
