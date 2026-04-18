import asyncio
import httpx
import time
from uuid import uuid4
from datetime import datetime

API_URL = "http://localhost:8000/api/v1/events/batch"
TENANT_ID = str(uuid4()) # A fake tenant for the test

def generate_batch(size=1000):
    """Generates a batch of dummy events for testing."""
    return {
        "events": [
            {
                "customer_id": f"cust_{i}",
                "event_type": "product_view",
                "product_id": str(uuid4()),
                "properties": {"pos": i, "ref": "benchmark"},
                "timestamp": datetime.utcnow().isoformat()
            } for i in range(size)
        ]
    }

async def run_benchmark():
    total_events = 10000
    batch_size = 1000
    num_batches = total_events // batch_size
    
    headers = {"X-Tenant-ID": TENANT_ID}
    
    print(f"🚀 Starting benchmark: Sending {total_events} events in {num_batches} batches...")
    
    start_time = time.perf_counter()
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for _ in range(num_batches):
            payload = generate_batch(batch_size)
            tasks.append(client.post(API_URL, json=payload, headers=headers))
        
        responses = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    total_duration = end_time - start_time
    
    # Check if all batches were accepted
    success_count = sum(1 for r in responses if r.status_code == 200)
    
    print(f"--- Results ---")
    print(f"Total Time: {total_duration:.2f} seconds")
    print(f"Successful Batches: {success_count}/{num_batches}")
    print(f"Events Per Second: {total_events / total_duration:.0f}")
    
    if total_duration < 2.0:
        print("✅ Performance Goal Met: Under 2 seconds!")
    else:
        print("❌ Performance Goal Failed: Over 2 seconds.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())