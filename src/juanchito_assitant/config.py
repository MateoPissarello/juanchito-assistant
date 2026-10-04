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

# Specialized Models per Agent Role
MODEL_REPO_ANALYZER = os.getenv("MODEL_REPO_ANALYZER", "qwen/qwen-2.5-coder-32b-instruct").strip()
MODEL_LINKEDIN_PARSER = os.getenv("MODEL_LINKEDIN_PARSER", "deepseek/deepseek-chat").strip()
MODEL_CV_WRITER = os.getenv("MODEL_CV_WRITER", "deepseek/deepseek-chat").strip()
MODEL_EVALUATOR = os.getenv("MODEL_EVALUATOR", "typesafe/jev-router").strip()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

# Paths
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "profile.db"
EXAMPLES_DIR = DATA_DIR / "examples"
OUTPUTS_DIR = DATA_DIR / "outputs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
