import sys
from pathlib import Path

# Ensure `app` package resolves when running pytest from `service_compress/`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
