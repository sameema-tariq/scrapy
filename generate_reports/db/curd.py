import json
from datetime import datetime

from generate_reports.db.connections   import get_conn, release_conn




# ── Config ────────────────────────────────────────────────────────────────────

def insert_values(record):

    INSERT_SQL = """
        INSERT INTO company_reports (company_uuid, signals, confidence, scrape_info, llm_data, created_at)
        VALUES (%(company_uuid)s, %(signals)s, %(confidence)s, %(scrape_info)s, %(llm_data)s, %(created_at)s)
        ON CONFLICT (company_uuid) DO UPDATE SET
            signals     = EXCLUDED.signals,
            confidence  = EXCLUDED.confidence,
            scrape_info = EXCLUDED.scrape_info,
            llm_data    = EXCLUDED.llm_data,
            created_at  = EXCLUDED.created_at;
    """

    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(INSERT_SQL, {
            "company_uuid": record["id"],
            "signals":     json.dumps(record["signals"]),
            "confidence":  json.dumps(record["confidence"]),
            "scrape_info": json.dumps(record["scrape_info"]),
            "llm_data":    json.dumps(record.get("llm_data")),
            "created_at":  datetime.now(),
        })
    conn.commit()
    print(f"✓ {len(record)} record(s) inserted into prospect_reports")

    cur.close()
    release_conn(conn)

