# =========================================================
# M5 - Pytest Configuration
# =========================================================

import os
os.environ.setdefault("M5_ALLOW_EXPERIMENTAL_FALLBACK", "true")

from pathlib import Path
import sys


# services/rul-validation directory
SERVICE_ROOT = Path(__file__).resolve().parents[1]

# Add services/rul-validation to Python path
service_root_str = str(SERVICE_ROOT)

if service_root_str not in sys.path:
    sys.path.insert(0, service_root_str)