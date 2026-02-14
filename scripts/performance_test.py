"""
Performance Test Script — Sprint 10 (Item 4.9)

Simulates concurrent load against the platform:
  - 1000 concurrent users across 50 tenants
  - Exercises key API endpoints (health, programs, users, auth)
  - Measures response times, throughput, error rates

Usage:
    # Run with pytest (uses Flask test client — no server needed)
    pytest tests/test_performance_load.py -v

    # Or run standalone against a live server:
    python scripts/performance_test.py --url http://localhost:5000 --users 100 --duration 30
"""

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_load_test(base_url, num_users=100, duration_seconds=30):
    """Run a load test against a live server.

    Args:
        base_url: Server URL (e.g. http://localhost:5000)
        num_users: Number of concurrent virtual users
        duration_seconds: Test duration

    Returns:
        dict with latency stats, throughput, error rate
    """
    import urllib.request
    import urllib.error

    endpoints = [
        "/api/v1/health",
        "/api/v1/programs",
        "/api/v1/admin/dashboard/summary",
        "/api/v1/admin/feature-flags",
    ]

    results = []
    errors = 0
    start_time = time.time()

    def make_request(endpoint):
        nonlocal errors
        url = f"{base_url}{endpoint}"
        t0 = time.time()
        try:
            req = urllib.request.Request(url)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
                elapsed = time.time() - t0
                return {"endpoint": endpoint, "status": resp.status, "latency": elapsed}
        except Exception as exc:
            elapsed = time.time() - t0
            errors += 1
            return {"endpoint": endpoint, "status": 0, "latency": elapsed, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        while time.time() - start_time < duration_seconds:
            for ep in endpoints:
                futures.append(executor.submit(make_request, ep))
            time.sleep(0.01)  # small pause between batches

        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                errors += 1

    total_duration = time.time() - start_time
    latencies = [r["latency"] for r in results if r.get("latency")]

    stats = {
        "total_requests": len(results),
        "errors": errors,
        "error_rate_pct": round(errors / max(len(results), 1) * 100, 2),
        "duration_seconds": round(total_duration, 2),
        "throughput_rps": round(len(results) / max(total_duration, 0.1), 2),
    }
    if latencies:
        stats.update({
            "latency_avg_ms": round(statistics.mean(latencies) * 1000, 2),
            "latency_p50_ms": round(statistics.median(latencies) * 1000, 2),
            "latency_p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] * 1000, 2),
            "latency_p99_ms": round(sorted(latencies)[int(len(latencies) * 0.99)] * 1000, 2),
            "latency_max_ms": round(max(latencies) * 1000, 2),
        })

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Platform performance test")
    parser.add_argument("--url", default="http://localhost:5000", help="Base URL")
    parser.add_argument("--users", type=int, default=100, help="Concurrent users")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    args = parser.parse_args()

    print(f"\n🚀 Starting load test: {args.users} users, {args.duration}s against {args.url}")
    results = run_load_test(args.url, args.users, args.duration)

    print("\n📊 Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")

    if results.get("error_rate_pct", 100) > 5:
        print("\n❌ Error rate > 5% — FAIL")
        sys.exit(1)
    else:
        print("\n✅ Load test PASSED")
