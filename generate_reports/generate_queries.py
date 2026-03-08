
import os
import json

import psycopg2
import psycopg2.extras

from generate_reports.config import SOURCE
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from datetime import datetime

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres_password@postgres:5432/postgres",
)

def get_conn() -> psycopg2.extensions.connection:
    """Return a new psycopg2 connection using RealDictCursor."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def generate_company_query(cur: psycopg2.extensions.cursor) -> list[dict]:
    """Fetch all companies (uuid, domain, name) from the companies table."""
    cur.execute("""
                SELECT company_uuid, domain, company_name
                FROM companies
            """)
    company = cur.fetchall()
    if not company:
        raise ValueError(f"No company found")
    
    return company

def generate_raw_enrichment_query(cur: psycopg2.extensions.cursor, c_uuid: str, source: str) -> dict:
    """Fetch and parse enrichment attributes (location, revenue, employees) for a company."""
    cur.execute("""
                SELECT raw_response
                FROM raw_enrichment
                WHERE company_uuid = %s AND source = %s
            """, (c_uuid, source))
    r_enrich = cur.fetchall()

    if not r_enrich:
        print('No raw_enrichment data found')
        return {}
    
    try:
        attributes = r_enrich[0]['raw_response']['data'][0]['attributes']
    except:
        print('No raw_enrichment data found')
        return {}

    city    = attributes.get('city', '') or ''
    country = attributes.get('country', '') or ''
    if city and country:
        hq_location = f"{city}, {country}"
    elif city or country:
        hq_location = city or country
    else:
        hq_location = 'N/A'

    return {
        'description': attributes.get('description',''),
        'founded_year': attributes.get('foundedYear','-'),
        'employee_count': attributes.get('employeeCount', '-'),
        'revenue': attributes.get("revenue", 0)*1000,
        'raw_funding_amount': attributes.get("recentFundingAmount", 0) * 1000,
        'hq_location': hq_location,
    }

def generate_cloud_estimates_query(cur: psycopg2.extensions.cursor, c_uuid: str) -> dict:
    """Fetch the latest cloud spend estimate and key calculation inputs for a company."""
    cur.execute("""
                SELECT estimated_cloud_spend, calculation_log
                FROM company_cloud_estimates
                WHERE company_uuid = %s 
                ORDER BY created_at DESC
                LIMIT 1
            """, (c_uuid,))
    c_estimate = cur.fetchall()
    if not c_estimate:
        print('No companycloud_estimates data found')
        return {}
    
    calc = c_estimate[0]["calculation_log"]

    return {
        "it_spend_reported":     calc.get("it_budget_reported"),
        "it_spend_blended":      calc.get("it_spend"),
        "cloud_spend":           calc.get("cloud_cap_value"),
        "cloud_growth":          calc.get("cloud_growth"),
        "funding_date":          calc.get("funding_date"),
        "funding_amount":        calc.get("recent_funding"),
        "employee_growth":       calc.get("employee_growth"),
        "tech_stack_tokens":     calc.get("canonical_tokens", []),
        "tech_stack_count":      calc.get("bw_tech_count"),
        "tech_count_normalized": calc.get("tech_count_normalized"),
    }

def generate_cloud_breakdown_query(cur: psycopg2.extensions.cursor, c_uuid: str) -> dict:
    """Fetch and build a step-by-step cloud spend breakdown including GPU/AI and growth details."""
    cur.execute("""
        SELECT estimated_cloud_spend, estimated_gpu_spend,
               estimated_cloud_spend_growth, calculation_log
        FROM company_cloud_estimates
        WHERE company_uuid = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (c_uuid,))
    row = cur.fetchone()
    if not row:
        print('No cloud breakdown data found')
        return {}

    calc = row["calculation_log"] or {}
    est_cloud  = float(row["estimated_cloud_spend"] or 0)
    est_gpu    = float(row["estimated_gpu_spend"] or 0)
    est_growth = float(row["estimated_cloud_spend_growth"] or 0)

    # ── Industry ─────────────────────────────────────────────────────────────
    industry = {
        "classified": calc.get("industry_classified"),
        "raw":        calc.get("industry_raw"),
    }

    # ── GPU / AI workload ────────────────────────────────────────────────────
    gpu_ai = {
        "has_ai_ml":          calc.get("has_ai_ml", False),
        "ai_keyword_matches": calc.get("ai_keyword_matches", []),
        "gpu_fraction":       calc.get("gpu_fraction", 0.08),
        "estimated_gpu_spend": f"${est_gpu:,.2f} /yr",
    }

    # ── Shorthand helpers ────────────────────────────────────────────────────
    industry_label = (calc.get("industry_classified") or "").title()
    revenue        = calc.get("revenue_dollars") or 0
    it_spend       = calc.get("it_spend") or 0
    base_it_pct    = calc.get("base_it_pct") or 0
    cloud_intensity = calc.get("cloud_intensity") or 1.0
    growth_factor  = calc.get("growth_factor") or 1.0
    base_cloud_pct = calc.get("base_cloud_pct") or 0.4
    raw_cloud      = calc.get("raw_cloud_pre_cap") or est_cloud
    gpu_fraction   = calc.get("gpu_fraction") or 0.08
    cloud_growth   = calc.get("cloud_growth") or est_growth

    if revenue > 500_000_000:
        rev_label = ">500M"
    elif revenue < 50_000_000:
        rev_label = "<50M"
    else:
        rev_label = "50M–500M"

    # Step 2 detail
    if calc.get("it_spend_mode") == "estimated_only":
        it_detail = (
            f"No ZoomInfo IT budget → estimated only: "
            f"revenue × base IT% = ${revenue:,.2f} × {base_it_pct} = ${calc.get('it_estimated_raw') or it_spend:,.2f}"
        )
    else:
        reported  = calc.get("it_budget_reported") or 0
        blended   = calc.get("it_blended_pre_cap") or it_spend
        it_detail = (
            f"Blend used (70% reported + 30% estimated): "
            f"(0.70 × ${reported:,.2f}) + (0.30 × (${revenue:,.2f} × {base_it_pct})) = ${blended:,.2f}"
        )
        if calc.get("it_spend_capped"):
            cap_val = calc.get("it_cap_value") or it_spend
            it_detail += f" → capped at 120% of reported IT budget (max ${cap_val:,.2f}) → ${it_spend:,.2f}"
        else:
            it_detail += f" → ${it_spend:,.2f}"

    # Step 3 detail
    ci_tags = []
    if calc.get("has_cloud_provider"):  ci_tags.append("+cloud")
    if calc.get("has_kubernetes"):      ci_tags.append("+k8s")
    if calc.get("has_data_platform"):   ci_tags.append("+data")
    if (calc.get("tech_count_normalized") or 0) > 15: ci_tags.append("+saas_tools")
    if calc.get("has_cloud_native_desc"): ci_tags.append("+cloud_native_desc")

    # Step 4 detail
    gf_tags = []
    recent_funding = calc.get("recent_funding") or 0
    if recent_funding and revenue and recent_funding > 0.5 * revenue: gf_tags.append("+funding")
    recency = calc.get("funding_recency_bucket") or ""
    if recency == "<12m":    gf_tags.append("+recency<12m")
    elif recency == "12-24m": gf_tags.append("+recency12-24m")
    if calc.get("industry_classified") == "saas": gf_tags.append("+saas")

    # Step 5 detail
    cloud5_detail = (
        f"${it_spend:,.0f} × {base_cloud_pct} × {cloud_intensity} × {growth_factor} = ${raw_cloud:,.2f}"
    )
    if calc.get("cloud_was_capped"):
        max_pct = calc.get("max_cloud_of_it") or 0.6
        cloud5_detail += f" → capped at {max_pct:.0%} IT (${est_cloud:,.2f})"
    else:
        cloud5_detail += f" → ${est_cloud:,.2f}"

    # Step 7 detail
    cg_detail = f"base {industry_label}"
    if calc.get("funding_date"):
        cg_detail += " + funding recency"

    # ── Step-by-step breakdown ───────────────────────────────────────────────
    breakdown_steps = [
        {
            "step":   1,
            "name":   "Base IT %",
            "value":  base_it_pct,
            "detail": f"{industry_label}, rev {rev_label}",
        },
        {
            "step":   2,
            "name":   "IT Spend",
            "value":  f"${it_spend:,.0f}",
            "detail": it_detail,
        },
        {
            "step":   3,
            "name":   "Cloud Intensity",
            "value":  cloud_intensity,
            "detail": " ".join(ci_tags) if ci_tags else "—",
        },
        {
            "step":   4,
            "name":   "Growth Factor",
            "value":  growth_factor,
            "detail": " ".join(gf_tags) if gf_tags else "—",
        },
        {
            "step":   5,
            "name":   "Cloud % of IT",
            "value":  f"{base_cloud_pct:.0%}",
            "detail": cloud5_detail,
        },
        {
            "step":   6,
            "name":   "GPU Fraction",
            "value":  f"{gpu_fraction:.0%}",
            "detail": f"{'AI/ML detected' if calc.get('has_ai_ml') else 'No AI/ML'} → ${est_gpu:,.2f}",
        },
        {
            "step":   7,
            "name":   "Cloud Growth",
            "value":  f"{cloud_growth:.1%} YoY",
            "detail": cg_detail,
        },
    ]

    return {
        "industry":        industry,
        "gpu_ai":          gpu_ai,
        "breakdown_steps": breakdown_steps,
        "est_cloud":       est_cloud,
        "est_gpu":         est_gpu,
        "est_growth":      est_growth,
    }


def generate_company_score(cur: psycopg2.extensions.cursor, c_uuid: str) -> str:
    """Fetch the latest propensity tier score for a company."""
    cur.execute("""
                SELECT tier
                FROM company_scores
                WHERE company_uuid = %s 
                ORDER BY created_at DESC
                LIMIT 1
            """, (c_uuid,))
    c_score = cur.fetchall()
    try:
        c_val = c_score[0]['tier']
    except:
        print('Value missing')
        return '-'
    return c_val

def generate_top_3_signals(cur: psycopg2.extensions.cursor, c_uuid: str) -> dict:
    """Fetch the top 3 detected signals and their confidence levels for a company."""
    cur.execute("""
        SELECT name, confidence_level
        FROM (
            SELECT DISTINCT ON (csd.signal_id) rs.name, csd.confidence_level
            FROM company_signal_detections csd
            JOIN ref_signals rs ON rs.signal_id = csd.signal_id
            WHERE csd.is_detected = TRUE
              AND csd.company_uuid = %s
            ORDER BY csd.signal_id,
                CASE csd.confidence_level
                    WHEN 'High'   THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low'    THEN 3
                    ELSE 4
                END
        ) deduped
        ORDER BY
            CASE confidence_level
                WHEN 'High'   THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low'    THEN 3
                ELSE 4
            END
        LIMIT 3
    """, (c_uuid,))

    rows = cur.fetchall()
    return {
        'signals':    [row["name"] for row in rows],
        'confidence': [row["confidence_level"] for row in rows],
    }

def process_companies() -> list[dict]:
    """Orchestrate per-company data fetching and return a list of enriched report records."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        report_info = [] 
        # Fetch company data
        company_info = generate_company_query(cur)
        for _ in company_info:
            c_uuid = 'a35fa5e5-8c38-429c-9fb1-4634524b6172'#company['company_uuid']

            # Execute enrichment logic
            print(f'c_uuid:{c_uuid}')
            raw_enrich_info = generate_raw_enrichment_query(cur, c_uuid, SOURCE)

            raw_cloud_estimates = generate_cloud_estimates_query(cur, c_uuid)

            c_signals = generate_top_3_signals(cur, c_uuid)

            c_breakdown = generate_cloud_breakdown_query(cur, c_uuid)

            # ── Fetch company name/domain for the actual c_uuid ───────────
            cur.execute(
                "SELECT company_name, domain FROM companies WHERE company_uuid = %s",
                (c_uuid,)
            )
            company_row = cur.fetchone() or {}

            # ── Format helpers ────────────────────────────────────────────
            def fmt_dollar(val: float | None) -> str:
                """Format a numeric value as a dollar string with no decimal places."""
                if not val: return '-'
                return f"${float(val):,.0f}"

            def fmt_dollar_2dp(val: float | None) -> str:
                """Format a numeric value as a dollar string with two decimal places."""
                if not val: return '-'
                return f"${float(val):,.2f}"

            # ── Derived values ────────────────────────────────────────────
            est_cloud  = c_breakdown.get("est_cloud", 0)
            est_gpu    = c_breakdown.get("est_gpu", 0)
            est_growth = c_breakdown.get("est_growth", 0)

            tech_count      = raw_cloud_estimates.get("tech_stack_count") or 0
            tech_normalized = raw_cloud_estimates.get("tech_count_normalized") or 0
            emp_growth_raw  = raw_cloud_estimates.get("employee_growth")
            emp_growth_fmt  = f"{emp_growth_raw}%" if emp_growth_raw is not None else "0%"

            db_info = {
                "company_info": {
                    "domain":                       company_row.get("domain"),
                    "description":                  raw_enrich_info.get("description", ""),
                    "company_name":                 company_row.get("company_name"),
                    "hq_location":                  raw_enrich_info.get("hq_location", "N/A"),
                    "founded_year":                 raw_enrich_info.get("founded_year") or "N/A",
                    "employee_count":               f"{int(raw_enrich_info.get('employee_count')):,}" if raw_enrich_info.get("employee_count") else "N/A",
                    "estimated_gpu_spend":          fmt_dollar(est_gpu),
                    "estimated_annual_cloud_spend": fmt_dollar(est_cloud),
                    "estimated_cloud_spend_growth": f"{est_growth:.1%}",
                },
                "company_inputs": {
                    "revenue":              fmt_dollar(raw_enrich_info.get("revenue", 0)),
                    "tech_stack":           f"{tech_count} BuiltWith techs → {tech_normalized} normalized",
                    "funding_date":         str(raw_cloud_estimates.get("funding_date")) if raw_cloud_estimates.get("funding_date") else "-",
                    "recent_funding":       fmt_dollar(raw_cloud_estimates.get("funding_amount")),
                    "employee_growth":      emp_growth_fmt,
                    "canonical_tokens":     raw_cloud_estimates.get("tech_stack_tokens", []),
                    "industry_raw_tags":    c_breakdown.get("industry", {}).get("raw") if isinstance(c_breakdown.get("industry", {}).get("raw"), list) else [],
                    "it_spend_zoominfo":    fmt_dollar(raw_cloud_estimates.get("it_spend_reported")),
                    "industry_classified":  (c_breakdown.get("industry", {}).get("classified") or "").title(),
                },
                "breakdown_steps": c_breakdown.get("breakdown_steps", []),
                "estimation_results": {
                    "est_gpu_spend":    fmt_dollar_2dp(est_gpu) + " /yr",
                    "est_cloud_spend":  fmt_dollar_2dp(est_cloud) + " /yr",
                    "est_cloud_growth": f"{est_growth:.1%} YoY",
                },
            }

            # Append to results list
            report_info.append({
                'company_uuid': c_uuid,
                'signals':      c_signals.get('signals'),
                'confidence':   c_signals.get('confidence'),
                'db_info':      db_info,
            })

            #print(report_info)
            break

        conn.commit()
        return report_info

    except Exception as e:
        conn.rollback()
        print(f"Error processing companies: {e}")
        raise
    finally:
        cur.close()
        conn.close()


# Usage example:
if __name__ == "__main__":
    enriched_data = process_companies()
    print(f"Processed {len(enriched_data)} companies")
    print(json.dumps(enriched_data, indent=2, ensure_ascii=False))