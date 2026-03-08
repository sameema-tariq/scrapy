
SYSTEM_PROMPT = """You are a cloud cost intelligence analyst. 
Given structured company data, you extract and generate concise, accurate fields.
Always respond with valid JSON only — no markdown, no preamble, no explanation."""

USER_PROMPT_TEMPLATE = """Analyze this company record and return ONLY a JSON object with the fields below.

=== COMPANY DATA ===
{company_data}

=== OUTPUT SCHEMA ===
Return exactly this JSON structure (all fields required):

{{
  "hq_city": "<city extracted from description>",
  "hq_country": "<country extracted from description>",
  "founded_year": "<country extracted from description>"
  "industry_label": "<1–2 word label e.g. 'Fintech · Digital Payments'>",

  "optimization": {{
    "savings_range": "<15–20% of est_cloud_spend as range>",
    "savings_rationale": "<1–2 sentences tailored to canonical_tokens stack (reserved instances, serverless tuning, GPU scheduling, etc.)>",
    "projected_spend_increase": "<est_cloud_spend × est_cloud_growth formatted",
    "growth_risk": "<1 sentence using est_cloud_growth % and projected next-year spend figure>"
  }},

  "company_profile": {{
    "base_it_pct_rationale": "<explain why this base IT % was chosen for this industry + revenue tier",
    "growth_factor_rationale": "<explain how industry classification contributed to growth_factor and est_cloud_growth>"
  }},

  "cloud_tools_summary": "<1-line stack profile e.g. 'Cloud-native multi-provider stack'>",

  "action_plan": {{
    "audit_pitch": "<2–3 sentences referencing company name, cloud providers from canonical_tokens, and est_cloud_spend figure>",
    "optimization_pitch": "<2–3 sentences referencing savings range (15–20% of est_cloud_spend) and specific levers from canonical_tokens stack>",
    "governance_pitch": "<2–3 sentences referencing recent_funding context, est_cloud_growth trajectory, and Canopy's platform value>"
  }}

  "breakdown_summary":  "<Throughly read the breakdown steps and then write 1–2 sentence related industry based summary of the estimation breakdown process. Do NOT include any numbers, formulas, or detailed calculations — keep it high-level and business-friendly.>",

}}

=== CALCULATION RULES ===
- savings_range: compute 15% and 20% of est_cloud_spend (numeric), format both as $XK or $X.XK
- projected_spend_increase: multiply est_cloud_spend by est_cloud_growth rate, prefix with +, format as $XK
- Use only data present in the company record — do not hallucinate figures
"""