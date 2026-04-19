import io
import time
import csv
import json
from typing import List
from uuid import UUID
from app.models.schemas import EventCreate
from app.db.session import engine

def bulk_ingest_events(tenant_id: UUID, events: List[EventCreate]):
    start_time = time.perf_counter()
    
    # Get the underlying psycopg2 connection
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            # Use a StringIO buffer to hold TSV (Tab Separated Values) data
            f = io.StringIO()
            # Use the csv writer to handle escaping/special characters correctly
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            
            for event in events:
                # Convert properties dict to a JSON string for Postgres JSONB column
                properties_json = json.dumps(event.properties)
                
                writer.writerow([
                    tenant_id,
                    event.customer_id,
                    event.event_type,
                    event.product_id if event.product_id else "",
                    properties_json,
                    event.timestamp
                ])
            
            # Reset buffer pointer to the beginning
            f.seek(0)
            
            # Psycopg2 syntax for COPY:
            sql = """
                COPY interactionevent (
                    tenant_id, customer_id, event_type, product_id, properties, timestamp
                ) FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')
            """
            cur.copy_expert(sql, f)
                
        raw_conn.commit()
        
    except Exception as e:
        raw_conn.rollback()
        raise e
    finally:
        raw_conn.close()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    return len(events), duration_ms