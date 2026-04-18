import io
import time
import csv
from typing import List
from uuid import UUID
from app.models.schemas import EventCreate
from app.db.session import engine

def bulk_ingest_events(tenant_id: UUID, events: List[EventCreate]):
    start_time = time.perf_counter()
    
    # We use the raw psycopg connection for maximum speed
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            # Prepare the data in CSV format in memory
            # This is significantly faster than standard inserts
            f = io.StringIO()
            for event in events:
                # Format: id, tenant_id, customer_id, event_type, product_id, properties, timestamp
                # Note: properties (dict) must be converted to JSON string
                f.write(f"{tenant_id}\t{event.customer_id}\t{event.event_type}\t"
                        f"{event.product_id or ''}\t{event.properties}\t{event.timestamp}\n")
            
            f.seek(0)
            
            # Use the COPY command
            with cur.copy("COPY interactionevent (tenant_id, customer_id, event_type, product_id, properties, timestamp) FROM STDIN") as copy:
                copy.write(f.read())
                
        raw_conn.commit()
        
    finally:
        raw_conn.close()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    return len(events), duration_ms