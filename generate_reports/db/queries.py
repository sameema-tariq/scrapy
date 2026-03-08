
# ─────────────────────────────────────────────
#  FETCH ALL COMPANIES
# ─────────────────────────────────────────────

def generate_company_query(cur):
    """
    Fetch all company UUIDs from the database.
    Raises ValueError if no companies found.
    """
    cur.execute("""
        SELECT company_uuid
        FROM companies
    """)
    companies = cur.fetchall()
    if not companies:
        raise ValueError("No company found")
    return companies


# ─────────────────────────────────────────────
#  FETCH TOP 3 SIGNALS — SINGLE COMPANY
#  Original function — kept for single use cases.
#  Fires 2 queries per call — use batch version
#  when processing multiple companies.
# ─────────────────────────────────────────────

def generate_top_3_signals(cur, c_uuid):
    """
    Fetch top 3 signals for a single company.
    Uses 2 separate queries.
    """
    cur.execute("""
        SELECT signal_id, confidence_level
        FROM company_signal_detections
        WHERE is_detected = TRUE
          AND company_uuid = %s
        ORDER BY
            CASE confidence_level
                WHEN 'High'   THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low'    THEN 3
                ELSE 4
            END
        LIMIT 3
    """, (c_uuid,))

    signal_rows        = cur.fetchall()
    signal_ids         = [row["signal_id"] for row in signal_rows]
    signal_confidences = [row["confidence_level"] for row in signal_rows]

    cur.execute("""
        SELECT name
        FROM ref_signals
        WHERE signal_id = ANY(%s)
    """, (signal_ids,))

    signal_names = [row["name"] for row in cur.fetchall()]
    return {
        "signals"   : signal_names,
        "confidence": signal_confidences,
    }


# ─────────────────────────────────────────────
#  FETCH TOP 3 SIGNALS — ALL COMPANIES (BATCH)
#  Optimized: single query for all companies
#  using ROW_NUMBER() window function + JOIN.
#  Use this when looping over many companies.
# ─────────────────────────────────────────────

def fetch_signals_for_all_companies(cur, company_uuids):
    if not company_uuids:
        return {}

    cur.execute("""
        WITH ranked AS (
            SELECT
                csd.company_uuid,
                rs.name              AS signal_name,
                csd.confidence_level,
                ROW_NUMBER() OVER (
                    PARTITION BY csd.company_uuid
                    ORDER BY
                        CASE csd.confidence_level
                            WHEN 'High'   THEN 1
                            WHEN 'Medium' THEN 2
                            WHEN 'Low'    THEN 3
                            ELSE 4
                        END
                ) AS rn
            FROM company_signal_detections csd
            JOIN ref_signals rs ON rs.signal_id = csd.signal_id
            WHERE csd.is_detected = TRUE
              AND csd.company_uuid = ANY(%s::uuid[])
        )
        SELECT company_uuid, signal_name, confidence_level
        FROM ranked
        WHERE rn <= 3
        ORDER BY company_uuid, rn
    """, (company_uuids,))

    signals_map = {}
    for row in cur.fetchall():
        uuid_str = str(row["company_uuid"])          # safer for dict keys
        if uuid_str not in signals_map:
            signals_map[uuid_str] = {"signals": [], "confidence": []}
        signals_map[uuid_str]["signals"].append(row["signal_name"])
        signals_map[uuid_str]["confidence"].append(row["confidence_level"])

    return signals_map
