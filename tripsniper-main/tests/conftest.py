import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STUB_DIR = ROOT / "test_stubs"
if STUB_DIR.exists() and str(STUB_DIR) not in sys.path:
    sys.path.insert(0, str(STUB_DIR))
