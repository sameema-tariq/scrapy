
# ─────────────────────────────────────────────
#  DEBUG HELPER
# ─────────────────────────────────────────────

def debug_print_lines(text, label="RAW TEXT"):
    """Print every non-empty line with its line number."""
    print(f"\n========== {label} ==========")
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped:
            print(f"  LINE {i:>4} | {stripped}")
    print("=" * 50)


# ─────────────────────────────────────────────
#  PRINT RESULT
# ─────────────────────────────────────────────

def print_result(report_info):
    """Pretty-print the full report for all companies."""
    for entry in report_info:
        data = entry.get("scrape_info", {})
        if not data:
            print(f"\n  ✗ No data for company {entry['id']}")
            continue

        print(f"\n{'=' * 55}")
        print(f"  COMPANY : {entry['id']}")
        print(f"{'=' * 55}")

        print("\n--- COMPANY INFO ---")
        for k, v in data.get("company_info", {}).items():
            print(f"  {k:<35}: {v}")

        print("\n--- COMPANY INPUTS ---")
        for k, v in data.get("company_inputs", {}).items():
            print(f"  {k:<35}: {v}")

        print("\n--- ESTIMATION RESULTS ---")
        for k, v in data.get("estimation_results", {}).items():
            print(f"  {k:<35}: {v}")

        print("\n--- BREAKDOWN STEPS ---")
        for s in data.get("breakdown_steps", []):
            print(f"  Step {s['step']}: {s['name']}")
            print(f"    Value  : {s['value']}")
            print(f"    Detail : {s['detail']}")

        print("\n--- SIGNALS ---")
        for sig, conf in zip(entry.get("signals", []), entry.get("confidence", [])):
            print(f"  [{conf}] {sig}")


def build_payload(info: dict) -> str:
    """Serialize the relevant fields into a clean block for the prompt."""
    scrape_info = info[0]['scrape_info']
    payload = {
        "company_name":         scrape_info["company_info"]["company_name"],
        "domain":               scrape_info["company_info"]["domain"],
        "description":          scrape_info["company_info"]["description"],
        "employee_count":       scrape_info["company_info"]["employee_count"],
        "est_cloud_spend":      scrape_info["company_info"]["estimated_annual_cloud_spend"],
        "est_cloud_growth":     scrape_info["company_info"]["estimated_cloud_spend_growth"],
        "est_gpu_spend":        scrape_info["company_info"]["estimated_gpu_spend"],
        "industry_classified":  scrape_info["company_inputs"]["industry_classified"],
        "industry_raw_tags":    scrape_info["company_inputs"]["industry_raw_tags"],
        "revenue":              scrape_info["company_inputs"]["revenue"],
        "it_spend_zoominfo":    scrape_info["company_inputs"]["it_spend_zoominfo"],
        "recent_funding":       scrape_info["company_inputs"]["recent_funding"],
        "funding_date":         scrape_info["company_inputs"]["funding_date"],
        "employee_growth":      scrape_info["company_inputs"]["employee_growth"],
        "tech_stack":           scrape_info["company_inputs"]["tech_stack"],
        "canonical_tokens":     scrape_info["company_inputs"]["canonical_tokens"],
        "est_cloud_spend":     scrape_info["estimation_results"]["est_cloud_spend"],
        "est_cloud_growth":     scrape_info["estimation_results"]["est_cloud_growth"],
        "est_gpu_spend":     scrape_info["estimation_results"]["est_gpu_spend"],
        "signals":              info[0]["signals"],
        "confidence":           info[0]["confidence"],
        "breakdown_steps":      scrape_info["breakdown_steps"],
    }
    return payload

def build_llm_response(response):
    city = 'N/A' if response.get("hq_city", None) == '' else response.get("hq_city", None)
    country = 'N/A' if response.get("hq_country", None) == '' else response.get("hq_country", None)
    founded_year = 'N/A' if response.get("hq_country", None) == '' else response.get("hq_country", None)
    return {
                'city': city,
                'country': country,
                'industry_label': response.get("industry_label", None),
                'founded_year': founded_year,
                'optimization': {
                    'savings_range': response.get("optimization", {}).get("savings_range", None),
                    'savings_rationale': response.get("optimization", {}).get("savings_rationale", None),
                    'projected_spend_increase': response.get("optimization", {}).get("projected_spend_increase", None),
                    'growth_risk': response.get("optimization", {}).get("growth_risk", None),
                },
                'company_profile': {
                    'base_it_pct_rationale': response.get("company_profile", {}).get("base_it_pct_rationale", None),
                    'growth_factor_rationale': response.get("company_profile", {}).get("growth_factor_rationale", None),
                },
                'cloud_tools_summary': response.get("cloud_tools_summary", None),
                'action_plan': {
                    'audit_pitch': response.get("action_plan", {}).get("audit_pitch", None),
                    'optimization_pitch': response.get("action_plan", {}).get("optimization_pitch", None),
                    'governance_pitch': response.get("action_plan", {}).get("governance_pitch", None),
                },
                'breakdown_summary': response.get("breakdown_summary", '')
            }

def update_html_page(company):
    # ── Parse JSONB columns ───────────────────────────────────────────────────
    signals    = company.get("signals", [])
    confidence = company.get("confidence", [])
    scrape     = company.get("scrape_info", {})
    llm        = company.get("llm_data", {})

    # ── Scrape sub-objects ────────────────────────────────────────────────────
    company_info   = scrape.get("company_info", {})
    company_inputs = scrape.get("company_inputs", {})
    estimation     = scrape.get("estimation_results", {})
    breakdown      = scrape.get("breakdown_steps", [])

    # ── LLM sub-objects ───────────────────────────────────────────────────────
    optimization    = llm.get("optimization", {})
    company_profile = llm.get("company_profile", {})
    action_plan     = llm.get("action_plan", {})

    # ── Parse tech stack counts e.g. "176 BuiltWith techs → 456 normalized" ──
    tech_stack_raw        = company_inputs.get("tech_stack", "")
    tech_stack_builtwith  = tech_stack_raw.split(" ")[0] if tech_stack_raw else ""
    tech_stack_normalized = tech_stack_raw.split("→")[-1].strip().split(" ")[0] if "→" in tech_stack_raw else ""

    # ── Signals with confidence zipped ───────────────────────────────────────
    signals_with_confidence = list(zip(signals, confidence))

    # ── GPU fraction from breakdown step 6 ───────────────────────────────────
    gpu_fraction = next(
        (s.get("value") for s in breakdown if "gpu" in s.get("name", "").lower()),
        ""
    )

    report_data = {
        # ── Header ────────────────────────────────────────────────────────────
        "report_date":              company.get("created_at", ""),

        # ── Hero / companies ──────────────────────────────────────────────────
        "company_name":             company_info.get("company_name", ""),
        "domain":                   company_info.get("domain", ""),
        "hq_city":                  llm.get("city", ""),
        "hq_country":               llm.get("country", ""),
        "founded_year":             llm.get("founded_year", ""),
        "industry_label":           llm.get("industry_label", ""),
        "employee_count":           company_info.get("employee_count", ""),
        "description":              company_info.get("description", ""),

        # ── Estimation results ────────────────────────────────────────────────
        "est_cloud_spend":          estimation.get("est_cloud_spend", ""),
        "est_gpu_spend":            estimation.get("est_gpu_spend", ""),
        "est_cloud_growth":         estimation.get("est_cloud_growth", ""),
        "gpu_fraction_pct":         gpu_fraction,

        # ── Breakdown steps (loop in template) ───────────────────────────────
        "breakdown_steps":          breakdown,

        # ── Optimization (LLM) ────────────────────────────────────────────────
        "savings_range":            optimization.get("savings_range", ""),
        "savings_rationale":        optimization.get("savings_rationale", ""),
        "projected_spend_increase": optimization.get("projected_spend_increase", ""),
        "growth_risk":              optimization.get("growth_risk", ""),

        # ── Company profile ───────────────────────────────────────────────────
        "revenue":                  company_inputs.get("revenue", ""),
        "it_spend_zoominfo":        company_inputs.get("it_spend_zoominfo", ""),
        "recent_funding":           company_inputs.get("recent_funding", ""),
        "funding_round_label":      company_profile.get("funding_round_label", ""),
        "funding_date":             company_inputs.get("funding_date", ""),
        "industry":                 company_inputs.get("industry_classified", ""),
        "industry_raw_tags":        company_inputs.get("canonical_tokens", []),  # fallback
        "base_it_pct_rationale":    company_profile.get("base_it_pct_rationale", ""),
        "growth_factor_rationale":  company_profile.get("growth_factor_rationale", ""),

        # ── Signals (loop in template) ────────────────────────────────────────
        "signals_with_confidence":  signals_with_confidence,
        "high_confidence_count":    sum(1 for c in confidence if c == "High"),

        # ── Cloud tools ───────────────────────────────────────────────────────
        "canonical_tokens":         company_inputs.get("canonical_tokens", []),
        "tech_stack_builtwith":     tech_stack_builtwith,
        "tech_stack_normalized":    tech_stack_normalized,
        "cloud_tools_summary":      llm.get("cloud_tools_summary", ""),

        # ── Action plan (LLM) ─────────────────────────────────────────────────
        "audit_pitch":              action_plan.get("audit_pitch", ""),
        "optimization_pitch":       action_plan.get("optimization_pitch", ""),
        "governance_pitch":         action_plan.get("governance_pitch", ""),

        # ── Break down Step-by-Step Summmary ─────────────────────────────────────────────────
        'breakdown_summary': llm.get("breakdown_summary", '')
    }

    return report_data
