"""
Intellog Auto-Deploy Watcher
Polls GitHub for new commits and auto-deploys when changes detected.
Run this alongside your backend for true CI/CD.

Usage: python autodeploy.py
"""
import os
import subprocess
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DEPLOY] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("autodeploy")

# Configuration
CHECK_INTERVAL = 60  # seconds between checks
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BRANCH = "main"


def run_cmd(cmd, cwd=None):
    """Run shell command and return output."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or PROJECT_DIR,
    )
    return result.stdout.strip(), result.returncode


def get_local_commit():
    out, _ = run_cmd(f"git rev-parse {BRANCH}")
    return out


def get_remote_commit():
    run_cmd("git fetch origin", PROJECT_DIR)
    out, _ = run_cmd(f"git rev-parse origin/{BRANCH}")
    return out


def deploy():
    """Pull latest and restart backend."""
    logger.info("=" * 50)
    logger.info("NEW COMMIT DETECTED — Deploying...")

    # Pull latest
    out, code = run_cmd("git pull origin main")
    logger.info("Git pull: %s", out)
    if code != 0:
        logger.error("Git pull failed!")
        return False

    # Update dependencies
    out, _ = run_cmd("pip install -r requirements.txt -q")
    logger.info("Dependencies updated")

    # Restart backend
    # Kill existing uvicorn
    run_cmd('taskkill /F /IM uvicorn.exe 2>nul')
    # Find and kill process on port 8000
    out, _ = run_cmd('for /f "tokens=5" %a in (\'netstat -aon ^| findstr :8000 ^| findstr LISTENING\') do taskkill /F /PID %a 2>nul')
    time.sleep(2)

    # Start new backend
    subprocess.Popen(
        "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000",
        shell=True, cwd=PROJECT_DIR,
        stdout=open(os.path.join(PROJECT_DIR, "logs", "backend.log"), "a"),
        stderr=subprocess.STDOUT,
    )
    time.sleep(3)

    # Verify
    try:
        import requests
        resp = requests.get("http://localhost:8000/api/health", timeout=5)
        if resp.status_code == 200:
            logger.info("✅ Backend healthy. Deploy complete!")
            return True
    except Exception:
        pass

    logger.warning("⚠️ Backend health check failed after deploy")
    return False


def watch():
    """Main watch loop."""
    logger.info("Intellog Auto-Deploy Watcher started")
    logger.info("Watching branch: %s", BRANCH)
    logger.info("Check interval: %ds", CHECK_INTERVAL)
    logger.info("Project: %s", PROJECT_DIR)
    logger.info("-" * 50)

    while True:
        try:
            local = get_local_commit()
            remote = get_remote_commit()

            if local != remote:
                logger.info("Local:  %s", local[:8])
                logger.info("Remote: %s", remote[:8])
                deploy()
            else:
                logger.info("Up to date (%s)", local[:8])
        except KeyboardInterrupt:
            logger.info("Watcher stopped")
            break
        except Exception as e:
            logger.error("Error: %s", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs(os.path.join(PROJECT_DIR, "logs"), exist_ok=True)
    watch()
