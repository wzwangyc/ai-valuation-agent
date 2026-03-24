import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Test collection should not depend on a developer's private .env file.
# Provide minimal deterministic placeholders so imports succeed in a clean environment.
os.environ.setdefault("FRED_API_KEY", "test-fred-key")
os.environ.setdefault("FINNHUB_API_KEY", "test-finnhub-key")
