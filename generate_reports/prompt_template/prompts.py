import json

from typing import Dict, Any, Optional

from generate_reports.prompt_template.create_report_prompt import USER_PROMPT_TEMPLATE, SYSTEM_PROMPT
from generate_reports.llm.client import _call_llm
from generate_reports.utils.helpers import build_llm_response


def infer_company_insights(payload: Optional[str]) -> Optional[str]:
    """
    Infer persona/role type from job title using a small LLM call.
    Returns None if job_title is missing or generation fails.
    """
    if not payload:
        return None
    
    prompt = USER_PROMPT_TEMPLATE.format(company_data=json.dumps(payload, indent=2))
    llm_response = {}
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = _call_llm(messages, max_tokens=2500)
        if response and isinstance(response, dict):
            llm_response = build_llm_response(response)
        return llm_response
    except Exception as exc:
        print("Persona inference failed for title %r: %s")
        return llm_response