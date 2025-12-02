import sys
from pathlib import Path

# Ensure apps/api is on path for imports like `app.schemas`.
ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "apps" / "api"
if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))
