"""Start the Vidora API and web app together with `python run.py`."""

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


def preflight() -> list[str]:
    problems = []
    if shutil.which("uv") is None:
        problems.append("uv was not found on PATH. Install it from https://docs.astral.sh/uv/.")
    if shutil.which("npm") is None:
        problems.append("npm was not found on PATH. Install Node.js 20.9 or newer.")
    if not (FRONTEND / "node_modules").is_dir():
        problems.append("Frontend dependencies are missing. Run: npm --prefix frontend install")
    return problems


def main() -> int:
    problems = preflight()
    if problems:
        for problem in problems:
            print(f"Cannot start Vidora: {problem}", file=sys.stderr)
        return 1

    services = [
        ("API", ["uv", "run", "uvicorn", "--factory", "api.main:create_app", "--host", "127.0.0.1", "--port", "8000"], ROOT),
        ("Web app", [shutil.which("npm") or "npm", "run", "dev", "--", "--hostname", "127.0.0.1"], FRONTEND),
    ]
    processes: list[tuple[str, subprocess.Popen]] = []
    try:
        for name, command, cwd in services:
            processes.append((name, subprocess.Popen(command, cwd=cwd)))
        print("Vidora starting: web app http://127.0.0.1:3000, API http://127.0.0.1:8000/health")
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"{name} stopped unexpectedly (exit code {code}). Stopping Vidora.", file=sys.stderr)
                    return code or 1
            time.sleep(0.25)
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        print(f"Cannot start Vidora: {exc}", file=sys.stderr)
        return 1
    finally:
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
