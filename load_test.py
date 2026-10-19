import argparse
import asyncio
import json
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter

def request_once(url, timeout):
    start = time.perf_counter()
    status = 0
    error = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AutoScalePortfolioLoadTester/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            response.read(1024)
    except Exception as exc:
        error = type(exc).__name__
    return time.perf_counter() - start, status, error

async def run_stage(url, duration, concurrency, timeout):
    stop_at = time.monotonic() + duration
    latencies, statuses, errors = [], Counter(), Counter()
    total = 0
    async def worker():
        nonlocal total
        while time.monotonic() < stop_at:
            latency, status, error = await asyncio.to_thread(request_once, url, timeout)
            total += 1
            latencies.append(latency)
            if error:
                errors[error] += 1
            else:
                statuses[str(status)] += 1
    started = time.monotonic()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    elapsed = max(time.monotonic() - started, 0.001)
    ordered = sorted(latencies)
    def percentile(p):
        if not ordered:
            return None
        return round(ordered[min(int((len(ordered)-1)*p), len(ordered)-1)] * 1000, 2)
    return {
        "concurrency": concurrency, "duration_seconds": round(elapsed, 2),
        "requests": total, "requests_per_second": round(total / elapsed, 2),
        "status_counts": dict(statuses), "errors": dict(errors),
        "latency_ms": {
            "mean": round(statistics.mean(latencies) * 1000, 2) if latencies else None,
            "p50": percentile(.50), "p95": percentile(.95), "p99": percentile(.99)
        }
    }

async def main_async(args):
    stages = [int(x) for x in args.stages.split(",") if x.strip()]
    if not stages or any(x < 1 or x > 100 for x in stages):
        raise SystemExit("Stages must be comma-separated concurrency values from 1 to 100.")
    results = []
    for concurrency in stages:
        print(f"Running stage: concurrency={concurrency}, duration={args.duration}s")
        results.append(await run_stage(args.url, args.duration, concurrency, args.timeout))
    report = {"target": args.url, "warning": "Run only against authorized targets.", "stages": results}
    out = args.output
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f"Report written to: {out}")

def main():
    parser = argparse.ArgumentParser(description="Staged asynchronous HTTP load tester")
    parser.add_argument("url")
    parser.add_argument("--duration", type=int, default=10, help="seconds per stage (1-120)")
    parser.add_argument("--concurrency", type=int, default=5, help="default concurrency if stages omitted")
    parser.add_argument("--stages", default=None, help="comma-separated concurrency stages, e.g. 1,3,5")
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--output", default="load-report.json")
    args = parser.parse_args()
    if not args.stages:
        args.stages = str(args.concurrency)
    if not 1 <= args.duration <= 120:
        parser.error("--duration must be between 1 and 120 seconds")
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
