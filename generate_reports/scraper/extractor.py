import re

from generate_reports.config          import COMPANY_URL
from generate_reports.scraper.browser import click_view_breakdown
from generate_reports.parser.parsers  import (
    parse_company_info,
    parse_company_inputs,
    parse_estimation_results,
)


# ─────────────────────────────────────────────
#  EXTRACT BREAKDOWN TABLE
#  Reads directly from HTML <td> cells to avoid
#  inner_text formatting inconsistencies.
# ─────────────────────────────────────────────

def extract_breakdown_from_table(page):
    """
    Read the step-by-step breakdown directly
    from the HTML table cells.
    Splits value out of detail when value = 'i'
    (the info button rendered as text).
    """
    step_names = [
        "Base IT %", "IT Spend", "Cloud Intensity",
        "Growth Factor", "Cloud % of IT", "GPU Fraction", "Cloud Growth",
    ]
    steps = []

    for row in page.query_selector_all("table tr"):
        cols = row.query_selector_all("td")
        if len(cols) < 4:
            continue

        step_num   = cols[0].inner_text().strip()
        step_name  = cols[1].inner_text().strip()
        value_raw  = cols[2].inner_text().strip()
        detail_raw = cols[3].inner_text().strip()

        if not any(name in step_name for name in step_names):
            continue

        # Remove "i" info button text from step name
        step_name = step_name.replace("i", "").strip()

        # Real value is inside detail — split on tab or 2+ spaces
        if value_raw == "i":
            parts  = detail_raw.split("\t", 1) if "\t" in detail_raw \
                     else re.split(r"\s{2,}", detail_raw, maxsplit=1)
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
#  SCRAPE SINGLE COMPANY
#  Accepts an already-logged-in page object.
#  No browser launch. No login. No sleep.
# ─────────────────────────────────────────────

def scrape_company(page, company_uuid, debug=False) -> dict:
    """
    Scrape a single company page.
    Reuses the open browser page — no re-login.
    """
    from generate_reports.utils.helpers import debug_print_lines

    target_url = COMPANY_URL + company_uuid

    try:
        page.goto(target_url, wait_until="networkidle", timeout=45000)
        initial_text = page.inner_text("body")

        if debug:
            debug_print_lines(initial_text, "INITIAL PAGE TEXT")

        # company_inputs and estimation_results are visible
        # on the page BEFORE clicking View Breakdown
        company_info       = parse_company_info(initial_text)

        # Click View Breakdown to expand the step table
        clicked = click_view_breakdown(page)

        if clicked:
            expanded_text = page.inner_text("body")

            if debug:
                debug_print_lines(expanded_text, "TEXT AFTER VIEW BREAKDOWN")

            company_inputs     = parse_company_inputs(expanded_text)
            estimation_results = parse_estimation_results(expanded_text)
            breakdown_steps = extract_breakdown_from_table(page)
        else:
            print(f"  ⚠ View Breakdown not clicked — breakdown steps will be empty.")
            breakdown_steps = []

        return {
            "company_info"      : company_info,
            "company_inputs"    : company_inputs,
            "estimation_results": estimation_results,
            "breakdown_steps"   : breakdown_steps,
        }

    except Exception as e:
        print(f"  ✗ Scrape failed for {company_uuid}: {e}")
        return {}
