import os
from pathlib import Path
from dotenv import load_dotenv

# Detect Project Root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load .env if present
load_dotenv(PROJECT_ROOT / ".env")

# AI & API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat").strip()

# Specialized Models per Agent Role (Legacy single model overrides)
MODEL_REPO_ANALYZER = os.getenv("MODEL_REPO_ANALYZER", "qwen/qwen-2.5-coder-32b-instruct").strip()
MODEL_LINKEDIN_PARSER = os.getenv("MODEL_LINKEDIN_PARSER", "deepseek/deepseek-chat").strip()
MODEL_CV_WRITER = os.getenv("MODEL_CV_WRITER", "deepseek/deepseek-chat").strip()
MODEL_EVALUATOR = os.getenv("MODEL_EVALUATOR", "typesafe/jev-router").strip()


def _parse_model_chain(env_var: str, legacy_single: str, default_chain: list[str]) -> list[str]:
    raw = os.getenv(env_var, "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    if legacy_single and legacy_single != default_chain[0]:
        chain = [legacy_single]
        for m in default_chain:
            if m not in chain:
                chain.append(m)
        return chain
    return default_chain


# Task-Specific Model Chains (Primary + Fallbacks for OpenRouter)
MODELS_JOB_ANALYZER = _parse_model_chain(
    "MODELS_JOB_ANALYZER",
    os.getenv("MODEL_JOB_ANALYZER", MODEL_CV_WRITER),
    ["deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.3-70b-instruct"],
)
MODELS_CV_WRITER = _parse_model_chain(
    "MODELS_CV_WRITER",
    MODEL_CV_WRITER,
    ["deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.3-70b-instruct"],
)
MODELS_EVALUATOR = _parse_model_chain(
    "MODELS_EVALUATOR",
    MODEL_EVALUATOR,
    ["typesafe/jev-router", "deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct"],
)
MODELS_REPO_ANALYZER = _parse_model_chain(
    "MODELS_REPO_ANALYZER",
    MODEL_REPO_ANALYZER,
    ["qwen/qwen-2.5-coder-32b-instruct", "deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct"],
)
MODELS_LINKEDIN_PARSER = _parse_model_chain(
    "MODELS_LINKEDIN_PARSER",
    MODEL_LINKEDIN_PARSER,
    ["deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.3-70b-instruct"],
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

# Database & Authentication Configuration (Cloud / Render Ready)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "mateo").strip() or "mateo"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "").strip()

# Paths
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "profile.db"
EXAMPLES_DIR = DATA_DIR / "examples"
OUTPUTS_DIR = DATA_DIR / "outputs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
