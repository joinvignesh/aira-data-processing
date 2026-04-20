import urllib.request
import urllib.error
import json
import time
import argparse
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Modified fetch_url snippet
import httpx

# Create a global client to reuse connections
client = httpx.Client(limits=httpx.Limits(max_connections=100))

def fetch_url(url, headers, data=None, method="POST"):
    start_time = time.perf_counter()
    try:
        response = client.request(method, url, json=data, headers=headers)
        return response.status_code, time.perf_counter() - start_time, None
    except Exception as e:
        return 0, time.perf_counter() - start_time, str(e)

def fetch_url_old(url, headers, data=None, method="POST"):
    start_time = time.perf_counter()
    try:
        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            response.read()
            end_time = time.perf_counter()
            return status, end_time - start_time, None
    except urllib.error.HTTPError as e:
        end_time = time.perf_counter()
        # Read the server's detailed error message
        try:
            error_details = e.read().decode('utf-8')
        except:
            error_details = e.reason
        return e.code, end_time - start_time, error_details
    except Exception as e:
        end_time = time.perf_counter()
        return 0, end_time - start_time, str(e)


def percentile(sorted_values, p):
    if not sorted_values:
        return 0
    index = min(int(len(sorted_values) * p), len(sorted_values) - 1)
    return sorted_values[index]


def run_benchmark(url, headers, data, requests_count, concurrency, method="POST"):
    print(f"\nRunning benchmark: {requests_count} requests with concurrency {concurrency}...")
    print(f"URL: {url}")
    start_time = time.perf_counter()

    statuses = {}
    latencies = []
    errors = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(fetch_url, url, headers, data, method)
            for _ in range(requests_count)
        ]

        for future in concurrent.futures.as_completed(futures):
            status, latency, error = future.result()

            statuses[status] = statuses.get(status, 0) + 1
            latencies.append(latency)

            if error:
                errors.append(error)

    total_time = time.perf_counter() - start_time

    print("\n--- Summary ---")
    print(f"Total time:       {total_time:.4f} secs")
    print(f"Requests per sec: {len(latencies) / total_time:.2f} req/s")

    if latencies:
        latencies.sort()
        avg = sum(latencies) / len(latencies)
        print(f"Fastest:          {latencies[0]:.4f} secs")
        print(f"Slowest:          {latencies[-1]:.4f} secs")
        print(f"Average:          {avg:.4f} secs")
        print(f"50th percentile:  {percentile(latencies, 0.50):.4f} secs")
        print(f"90th percentile:  {percentile(latencies, 0.90):.4f} secs")
        print(f"95th percentile:  {percentile(latencies, 0.95):.4f} secs")
        print(f"99th percentile:  {percentile(latencies, 0.99):.4f} secs")

    print("\n--- Status Codes ---")
    for code, count in sorted(statuses.items()):
        print(f"[{code}] {count} responses")

    if errors:
        print("\n--- Errors ---")
        unique_errors = list(set(errors))
        for err in unique_errors[:10]:
            print(f"- {err}")
        if len(unique_errors) > 10:
            print(f"... and {len(unique_errors) - 10} more.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple benchmark tool")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--payload", required=True, help="Path to JSON payload file")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID header value")
    parser.add_argument("-n", "--requests", type=int, default=1000, help="Number of requests")
    parser.add_argument("-c", "--concurrency", type=int, default=50, help="Concurrency level")
    parser.add_argument("-X", "--method", default="POST", help="HTTP method, default POST")

    args = parser.parse_args()

    headers = {
        "Content-Type": "application/json",
        "x-tenant-id": args.tenant_id,
    }

    with open(args.payload, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_benchmark(
        url=args.url,
        headers=headers,
        data=data,
        requests_count=args.requests,
        concurrency=args.concurrency,
        method=args.method.upper(),
    )