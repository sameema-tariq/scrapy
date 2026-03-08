import re


# ─────────────────────────────────────────────
#  BASE HELPERS
# ─────────────────────────────────────────────

def find_value(text, label):
    """
    Returns the value on the line immediately
    AFTER the given label.
    e.g. label='Company Name' → next line value
    """
    pattern = rf"{re.escape(label)}\s*\n\s*(.+?)(?=\n|$)"
    match   = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "Not found"


def find_inline_value(text, label):
    """
    Returns the value on the SAME line as the label.
    e.g. label='Est. Cloud Spend' → '$581,760.00 /yr'
    """
    pattern = re.escape(label) + r"\s*(.+?)(?=\n|$)"
    match   = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "Not found"


# ─────────────────────────────────────────────
#  COMPANY INFO
# ─────────────────────────────────────────────

def parse_company_info(text):
    """Parse the main company header section."""
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


# ─────────────────────────────────────────────
#  COMPANY INPUTS
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  ESTIMATION RESULTS
# ─────────────────────────────────────────────

def parse_estimation_results(text):
    """Parse the Estimation Results section."""
    return {
        "est_cloud_spend" : find_inline_value(text, "Est. Cloud Spend"),
        "est_cloud_growth": find_inline_value(text, "Est. Cloud Growth"),
        "est_gpu_spend"   : find_inline_value(text, "Est. GPU Spend"),
    }
