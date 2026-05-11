import os
import sys
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
COOLIFY_URL = os.getenv("COOLIFY_URL")
PROJECT_ROOT_WSL = os.getenv("PROJECT_ROOT_WSL")

results = []

def check(label, ok, detail=""):
    status = "[OK]  " if ok else "[FAIL]"
    print(f"{status} {label}" + (f" — {detail}" if detail else ""))
    results.append(ok)

# 1. OpenRouter API
try:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        check("OpenRouter API", r.status == 200, f"HTTP {r.status}")
except urllib.error.HTTPError as e:
    check("OpenRouter API", False, f"HTTP {e.code}")
except Exception as e:
    check("OpenRouter API", False, str(e))

# 2. Coolify
try:
    with urllib.request.urlopen(COOLIFY_URL, timeout=5) as r:
        check("Coolify", True, f"HTTP {r.status}")
except urllib.error.HTTPError as e:
    check("Coolify", e.code < 500, f"HTTP {e.code}")
except Exception as e:
    check("Coolify", False, str(e))

# 3. WSL project root
wsl_ok = bool(PROJECT_ROOT_WSL) and os.path.exists(PROJECT_ROOT_WSL)
check("WSL Project Root", wsl_ok, PROJECT_ROOT_WSL or "not set")

print(f"\n{'All systems operational.' if all(results) else 'Squad degraded — see failures above.'}")
sys.exit(0 if all(results) else 1)
