import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import AzureOpenAI
from jinja2 import Environment, FileSystemLoader, select_autoescape


# ── Database ──────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres_password@postgres:5432/postgres",
)

# ── App URLs ──────────────────────────────────
BASE_URL = os.environ.get("VIEWER_BASE_URL", "")
LOGIN_URL = f"{BASE_URL}/login"
COMPANY_URL = f"{BASE_URL}/company/"
PASSCODE = os.environ.get("VIEWER_PASSCODE")

# Azure OpenAI Model Configuration
AZURE_OPENAI_LLM_DEPLOYMENT=os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT")
AZURE_OPENAI_LLM_MODEL=os.getenv("AZURE_OPENAI_LLM_MODE")
AZURE_OPENAI_LLM_API_VERSION=os.getenv("AZURE_OPENAI_LLM_API_VERSION")

CLIENT = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=AZURE_OPENAI_LLM_API_VERSION,
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

SOURCE = "zi_company_enrich"