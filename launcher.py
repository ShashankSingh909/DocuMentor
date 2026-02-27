#!/usr/bin/env python3
"""
System Launcher for DocuMentor

Launches FastAPI backend and the Next.js TypeScript frontend with proper
health checking and process management.
"""

import subprocess
import sys
import time
import socket
from pathlib import Path

import requests

project_root = Path(__file__).parent
frontend_dir = project_root / "frontend"


class ModernSystemLauncher:
    def __init__(self):
        self.fastapi_process = None
        self.nextjs_process = None
        self.api_port = 8100
        self.ui_port = 3000

    def check_port_available(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    def wait_for_api(self, timeout=30):
        print(f"Waiting for FastAPI on port {self.api_port}...")
        for i in range(timeout):
            try:
                response = requests.get(f"http://127.0.0.1:{self.api_port}/", timeout=2)
                if response.status_code == 200:
                    print("FastAPI is ready")
                    return True
            except (requests.RequestException, ConnectionError):
                pass
            time.sleep(1)
            print(f"   Attempt {i + 1}/{timeout}")
        print("ERROR: FastAPI failed to start within timeout")
        return False

    def launch_fastapi(self):
        print("Starting FastAPI backend...")
        if not self.check_port_available(self.api_port):
            print(f"ERROR: Port {self.api_port} is already in use")
            return False
        try:
            self.fastapi_process = subprocess.Popen(
                [sys.executable, "api_server.py", "--port", str(self.api_port), "--host", "127.0.0.1"],
                cwd=str(project_root),
            )
            return self.wait_for_api()
        except Exception as e:
            print(f"ERROR: Failed to start FastAPI: {e}")
            return False

    def launch_nextjs(self):
        print("Starting Next.js frontend...")
        if not self.check_port_available(self.ui_port):
            print(f"ERROR: Port {self.ui_port} is already in use")
            return False

        if not frontend_dir.exists():
            print(f"ERROR: frontend/ directory not found at {frontend_dir}")
            return False

        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("Installing frontend dependencies (first run)...")
            result = subprocess.run(["npm", "install"], cwd=str(frontend_dir), shell=True)
            if result.returncode != 0:
                print("ERROR: npm install failed")
                return False

        try:
            self.nextjs_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(frontend_dir),
                shell=True,
            )
            print("Next.js is starting...")
            return True
        except Exception as e:
            print(f"ERROR: Failed to start Next.js: {e}")
            return False

    def show_system_info(self):
        print("=" * 70)
        print("DOCUMENTOR - AI-POWERED DOCUMENTATION ASSISTANT")
        print("=" * 70)
        print("Stack:")
        print("   - Frontend : Next.js + shadcn/ui + Tailwind CSS")
        print("   - Backend  : FastAPI + ChromaDB + Sentence Transformers")
        print("   - LLM      : Ollama (gemma2:2b) / OpenAI / Gemini")
        print()
        print("Access Points:")
        print(f"   Web UI      : http://127.0.0.1:{self.ui_port}")
        print(f"   Dashboard   : http://127.0.0.1:{self.ui_port}/dashboard")
        print(f"   Q&A         : http://127.0.0.1:{self.ui_port}/qa")
        print(f"   API Docs    : http://127.0.0.1:{self.api_port}/docs")
        print("=" * 70)

    def cleanup(self):
        print("\nCleaning up processes...")
        for name, proc in [("FastAPI", self.fastapi_process), ("Next.js", self.nextjs_process)]:
            if proc:
                print(f"   Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("Cleanup complete")

    def launch_system(self):
        try:
            self.show_system_info()

            if not self.launch_fastapi():
                print("ERROR: Failed to start FastAPI. Aborting.")
                return False

            time.sleep(2)

            if not self.launch_nextjs():
                print("ERROR: Failed to start Next.js.")
                self.cleanup()
                return False

            print("\nSYSTEM LAUNCHED SUCCESSFULLY!")
            print(f"Open: http://127.0.0.1:{self.ui_port}")
            print("\nPress Ctrl+C to stop both services")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutdown requested...")
                self.cleanup()
                return True

        except Exception as e:
            print(f"ERROR: {e}")
            self.cleanup()
            return False


def check_dependencies():
    print("Checking dependencies...")
    missing = []
    for module in ["fastapi", "uvicorn", "requests"]:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        print(f"ERROR: Missing Python packages: {', '.join(missing)}")
        print("Install with: pip install fastapi uvicorn requests")
        return False
    print("All dependencies available")
    return True


def main():
    print("DocuMentor System Launcher")
    print("=" * 50)
    if not check_dependencies():
        return False
    launcher = ModernSystemLauncher()
    return launcher.launch_system()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
