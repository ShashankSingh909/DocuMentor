#!/usr/bin/env python3
"""
DocuMentor - Main Entry Point

The Streamlit UI has been replaced with a Next.js TypeScript frontend.

To start the system:
  python launcher.py           # Start both FastAPI + Next.js
  python api_server.py         # Start FastAPI only (port 8100)
  cd frontend && npm run dev   # Start Next.js only (port 3000)

Access:
  Web UI   -> http://localhost:3000
  API Docs -> http://localhost:8100/docs
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent
frontend_dir = project_root / "frontend"


def main():
    print("DocuMentor - AI Documentation Assistant")
    print("=" * 50)
    print()
    print("The UI is now a Next.js TypeScript app in frontend/")
    print()
    print("To start everything:    python launcher.py")
    print("To start API only:      python api_server.py")
    print("To start frontend only: cd frontend && npm run dev")
    print()
    print("Access:")
    print("  Web UI   -> http://localhost:3000")
    print("  API Docs -> http://localhost:8100/docs")
    print()

    # Offer to launch frontend directly
    if len(sys.argv) > 1 and sys.argv[1] == "--frontend":
        print("Starting Next.js frontend...")
        subprocess.run(["npm", "run", "dev"], cwd=str(frontend_dir), shell=True)
    else:
        print("Tip: run 'python launcher.py' to start both servers.")


if __name__ == "__main__":
    main()
