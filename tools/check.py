"""check.py: the repo's one-command check (tests + lint). The pre-commit hook runs this; exit code gates the commit."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.exit(subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "tests"], cwd=ROOT).returncode)
