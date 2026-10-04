import os
from pathlib import Path
from dotenv import load_dotenv

# Detect Project Root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load .env if present
load_dotenv(PROJECT_ROOT / ".env")

# AI & API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
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
