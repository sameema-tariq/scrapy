import json
from playwright.sync_api import sync_playwright

from generate_reports.db.connections   import get_conn, release_conn
from generate_reports.db.queries      import (
    generate_company_query,
    generate_top_3_signals,
    fetch_signals_for_all_companies
)
from generate_reports.scraper.browser    import login
from generate_reports.scraper.extractor  import scrape_company
from generate_reports.utils.helpers      import build_payload
from generate_reports.prompt_template.prompts import infer_company_insights
from generate_reports.db.curd import insert_values


# ─────────────────────────────────────────────
#  PROCESS ALL COMPANIES
# ─────────────────────────────────────────────

def process_companies(debug=False):
    conn = get_conn()
    try:
        cur = conn.cursor()

        # ── Step 1: fetch all company UUIDs ──────────
        companies = generate_company_query(cur)
        c_uuids   = [row["company_uuid"] for row in companies]
        print(f"Found {len(c_uuids)} companies.\n")

        # ── Step 2: batch fetch all signals (1 query) ─
        signals_map = fetch_signals_for_all_companies(cur, c_uuids)

        # ── Step 3: one browser, one login, all pages ─
        report_info = {}
        c = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            login(page)                          # login once only

            for c_uuid in c_uuids:
                print(f"Scraping: {c_uuid} ...")
                try:
                    scrape_data = scrape_company(page, c_uuid, debug=debug)
                    c_signals   = signals_map.get(
                        c_uuid, {"signals": [], "confidence": []}
                    )
                    report_info = {
                        "id"         : c_uuid,
                        "signals"    : c_signals["signals"],
                        "confidence" : c_signals["confidence"],
                        "scrape_info": scrape_data,
                    }
                    print(f"  ✓ Done: {c_uuid}")

                except Exception as e:
                    # Isolate failure — log it and continue with next
                    print(f"  ✗ Error on {c_uuid}: {e}")
                    report_info = {
                        "id"         : c_uuid,
                        "signals"    : [],
                        "confidence" : [],
                        "scrape_info": {},
                    }

                print('*'*20)
                print(report_info)
                print('*'*20)
                for k,v in report_info:
                    print(k,v)
                #response = infer_company_insights(report_info)
                #report_info["llm_data"] = response


                #insert_values(report_info)
                
            browser.close()

        conn.commit()
        return report_info

    except Exception as e:
        conn.rollback()
        print(f"Fatal error: {e}")
        raise

    finally:
        cur.close()
        release_conn(conn)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    data = process_companies(debug=False)
    print(json.dumps(data, indent=2, ensure_ascii=False))


'''
import json
from playwright.sync_api import sync_playwright

from generate_reports.db.connections   import get_conn, release_conn
from generate_reports.db.queries      import (
    generate_company_query,
    generate_top_3_signals,
    fetch_signals_for_all_companies
)
from generate_reports.scraper.browser    import login
from generate_reports.scraper.extractor  import scrape_company
from generate_reports.utils.helpers      import build_payload
from generate_reports.prompt_template.prompts import infer_company_insights
from generate_reports.db.curd import insert_values


# ─────────────────────────────────────────────
#  PROCESS ALL COMPANIES
# ─────────────────────────────────────────────

def process_companies(debug=False):
    conn = get_conn()
    try:
        cur = conn.cursor()

        # ── Step 1: fetch all company UUIDs ──────────
        companies = generate_company_query(cur)
        c_uuids   = [row["company_uuid"] for row in companies]
        print(f"Found {len(c_uuids)} companies.\n")

        # ── Step 2: batch fetch all signals (1 query) ─
        signals_map = fetch_signals_for_all_companies(cur, c_uuids)

        # ── Step 3: one browser, one login, all pages ─
        report_info = {}
        c = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            login(page)                          # login once only

            for c_uuid in c_uuids:
                print(f"Scraping: {c_uuid} ...")
                try:
                    scrape_data = scrape_company(page, c_uuid, debug=debug)
                    c_signals   = signals_map.get(
                        c_uuid, {"signals": [], "confidence": []}
                    )
                    report_info = {
                        "id"         : c_uuid,
                        "signals"    : c_signals["signals"],
                        "confidence" : c_signals["confidence"],
                        "scrape_info": scrape_data,
                    }
                    print(f"  ✓ Done: {c_uuid}")

                except Exception as e:
                    # Isolate failure — log it and continue with next
                    print(f"  ✗ Error on {c_uuid}: {e}")
                    report_info = {
                        "id"         : c_uuid,
                        "signals"    : [],
                        "confidence" : [],
                        "scrape_info": {},
                    }

                print('*'*20)
                print(report_info)
                print('*'*20)
                for k,v in report_info:
                    print(k,v)
                #response = infer_company_insights(report_info)
                #report_info["llm_data"] = response


                #insert_values(report_info)
                
            browser.close()

        conn.commit()
        return report_info

    except Exception as e:
        conn.rollback()
        print(f"Fatal error: {e}")
        raise

    finally:
        cur.close()
        release_conn(conn)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    data = process_companies(debug=False)
    #info = insert_values(raw)
    #print(raw[0].keys())
    print(json.dumps(data, indent=2, ensure_ascii=False))






from playwright.sync_api import sync_playwright
import time
import re
import os

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

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

URL        = "http://127.0.0.1:8080/login"
TARGET_URL_1 = "http://127.0.0.1:8080/company/"
PASSCODE   = "Ftr2602!"


# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────

def login(page):
    print("Logging in...")
    page.goto(URL, wait_until="networkidle", timeout=45000)

    for sel in ['input[type="password"]', 'input[type="text"]']:
        try:
            page.wait_for_selector(sel, timeout=5000)
            page.fill(sel, PASSCODE)
            break
        except:
            continue

    for btn in ['button:has-text("Log in")', 'button[type="submit"]', 'button']:
        try:
            page.click(btn, timeout=5000)
            break
        except:
            continue

    time.sleep(2)
    print("Logged in.\n")


# ─────────────────────────────────────────────
#  CLICK VIEW BREAKDOWN
# ─────────────────────────────────────────────

def click_view_breakdown(page):
    print("Clicking View Breakdown...")
    for sel in [
        'button:has-text("View Breakdown")',
        'a:has-text("View Breakdown")',
        '*:has-text("View Breakdown")',
    ]:
        try:
            page.click(sel, timeout=5000)
            print(f"  → Clicked: {sel}")
            time.sleep(2)
            return True
        except:
            continue
    print("  → Could not find View Breakdown button.")
    return False


# ─────────────────────────────────────────────
#  PARSERS
# ─────────────────────────────────────────────

def find_value(text, label):
    pattern = rf"{re.escape(label)}\s*\n\s*(.+?)(?=\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "Not found"


def find_inline_value(text, label):
    pattern = rf"{re.escape(label)}\s*(.+?)(?=\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "Not found"


def parse_company_info(text):
    return {
        "company_name"                : find_value(text, "Company Name"),
        "domain"                      : find_value(text, "Domain"),
        "revenue"                     : find_value(text, "Revenue"),
        "employee_count"              : find_value(text, "Employee Count"),
        "description"                 : find_value(text, "Description"),
        "estimated_annual_cloud_spend": find_value(text, "Estimated Annual Cloud Spend"),
        "estimated_gpu_spend"         : find_value(text, "Estimated GPU Spend"),
        "estimated_cloud_spend_growth": find_value(text, "Estimated Cloud Spend Growth (YoY)"),
    }


def parse_company_inputs(text):
    industry_match      = re.search(r"Industry\s*(.+?)(?=Revenue|\n)", text, re.IGNORECASE)
    industry_raw        = industry_match.group(1).strip() if industry_match else "Not found"
    industry_classified = re.match(r"^(\w+)", industry_raw)
    industry_classified = industry_classified.group(1) if industry_classified else industry_raw
    raw_tags_match      = re.search(r"raw:\s*(\[.*?\])", industry_raw)
    raw_tags            = raw_tags_match.group(1) if raw_tags_match else "Not found"

    tech_match       = re.search(r"Tech Stack\s*(.+?)(?=\n|Canonical)", text, re.IGNORECASE)
    tech_stack       = tech_match.group(1).strip() if tech_match else "Not found"
    tokens_match     = re.search(r"Canonical Tokens\s*(.+?)(?=\n|$)", text, re.IGNORECASE)
    canonical_tokens = tokens_match.group(1).strip() if tokens_match else "Not found"

    # Add $ to revenue if not already present
    revenue_raw = find_inline_value(text, "Revenue")
    revenue     = f"${revenue_raw}" if revenue_raw and not revenue_raw.startswith("$") else revenue_raw

    return {
        "industry_classified" : industry_classified,
        "industry_raw_tags"   : raw_tags,
        "revenue"             : revenue,
        "employee_count"      : find_inline_value(text, "Employee Count"),
        "it_spend_zoominfo"   : find_inline_value(text, "IT Spend (ZoomInfo)"),
        "recent_funding"      : find_inline_value(text, "Recent Funding"),
        "funding_date"        : find_inline_value(text, "Funding Date"),
        "employee_growth"     : find_inline_value(text, "Employee Growth"),
        "tech_stack"          : tech_stack,
        "canonical_tokens"    : canonical_tokens.split() if canonical_tokens != "Not found" else [],
    }


def parse_estimation_results(text):
    return {
        "est_cloud_spend" : find_inline_value(text, "Est. Cloud Spend"),
        "est_cloud_growth": find_inline_value(text, "Est. Cloud Growth"),
        "est_gpu_spend"   : find_inline_value(text, "Est. GPU Spend"),
    }


def extract_breakdown_from_table(page):
    """
    Read breakdown directly from the HTML table rows — bypasses
    inner_text formatting issues entirely.
    """
    step_names = [
        "Base IT %", "IT Spend", "Cloud Intensity",
        "Growth Factor", "Cloud % of IT", "GPU Fraction", "Cloud Growth",
    ]

    steps = []

    # Find all table rows
    rows = page.query_selector_all("table tr")
    print(f"  → Found {len(rows)} table rows")

    for row in rows:
        cols = row.query_selector_all("td")
        if len(cols) < 4:
            continue

        step_num  = cols[0].inner_text().strip()
        step_name = cols[1].inner_text().strip()
        value_raw = cols[2].inner_text().strip()
        detail_raw = cols[3].inner_text().strip()

        # Only process rows that match known step names
        if not any(name in step_name for name in step_names):
            continue

        # Remove "i" from step_name if present (info button text)
        step_name = step_name.replace("i", "").strip()

        # value_raw is "i" (the info button) — real value is in detail
        # detail format: "0.108\tSaas, rev <50M"  or  "0.108   Saas, rev <50M"
        if value_raw == "i":
            if "\t" in detail_raw:
                parts  = detail_raw.split("\t", 1)
            else:
                parts  = re.split(r"\s{2,}", detail_raw, maxsplit=1)

            value  = parts[0].strip() if len(parts) >= 1 else ""
            detail = parts[1].strip() if len(parts) == 2 else ""
        else:
            value  = value_raw
            detail = detail_raw

        steps.append({
            "step"  : step_num,
            "name"  : step_name,
            "value" : value,
            "detail": detail,
        })

    return steps


# ─────────────────────────────────────────────
#  DEBUG HELPER
# ─────────────────────────────────────────────

def debug_print_lines(text, label="RAW TEXT"):
    print(f"\n========== {label} ==========")
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped:
            print(f"  LINE {i:>4} | {stripped}")
    print("=" * 50)


# ─────────────────────────────────────────────
#  MAIN SCRAPER
# ─────────────────────────────────────────────

def scrape_company(TARGET_URL, debug=False) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        login(page)

        page.goto(TARGET_URL, wait_until="networkidle", timeout=45000)
        time.sleep(2)
        initial_text = page.inner_text("body")

        if debug:
            debug_print_lines(initial_text, "INITIAL PAGE TEXT")

        # Click View Breakdown to expand the table
        click_view_breakdown(page)

        expanded_text = page.inner_text("body")

        if debug:
            debug_print_lines(expanded_text, "TEXT AFTER VIEW BREAKDOWN")

        # Extract breakdown directly from HTML table (not from text)
        breakdown_steps = extract_breakdown_from_table(page)

        browser.close()

    result = {
        "company_info"      : parse_company_info(initial_text),
        "company_inputs"    : parse_company_inputs(expanded_text),
        "estimation_results": parse_estimation_results(expanded_text),
        "breakdown_steps"   : breakdown_steps,
    }

    return result


# ─────────────────────────────────────────────
#  GENERATE SIGNALS
# ─────────────────────────────────────────────

def generate_company_query(cur):
    cur.execute("""
                SELECT company_uuid
                FROM companies
            """)
    company = cur.fetchall()
    if not company:
        raise ValueError(f"No company found")
    
    return company

def generate_top_3_signals(cur, c_uuid):
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

    signal_rows = cur.fetchall()
    signal_ids = [row["signal_id"] for row in signal_rows]
    signal_confidences = [row["confidence_level"] for row in signal_rows]
    cur.execute("""
        SELECT name
        FROM ref_signals
        WHERE signal_id = ANY(%s)
    """, (signal_ids,))

    signal_names = [row["name"] for row in cur.fetchall()]
    return {
        'signals' : signal_names,
        'confidence': signal_confidences 
    }


def process_companies():
    conn = get_conn()
    try:
        cur = conn.cursor()
        report_info = [] 
        # Fetch company data
        company_info = generate_company_query(cur)
        for company in company_info:
            
            c_uuid = company['company_uuid']

            TARGET_URL = TARGET_URL_1 + c_uuid

            c_signals = generate_top_3_signals(cur, c_uuid)

            data = scrape_company(TARGET_URL, debug=False)

            # Append to results list
            report_info.append({
                'id': c_uuid,                     # primary identifier
                'signals' : c_signals.get('signals'),
                'confidence': c_signals.get('confidence'),
                'scrape_info': data
            })

            print(report_info)
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
# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    data = process_companies()

    import json
    print("\nAs a structured dict:")
    print(json.dumps(data, indent=4, ensure_ascii=False))

'''