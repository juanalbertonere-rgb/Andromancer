#!/usr/bin/env python3
import asyncio
import logging
import sys
from andromancer.cli import AndroMancerCLI
from andromancer import config as cfg

# Setup structured logging
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(cfg.LOG_FILE),
        logging.StreamHandler()
    ]
)

async def main():
    try:
        import httpx
    except ImportError:
        print("⚠️  httpx not found. Please install it with: pip install httpx")
        return

    import subprocess
    try:
        result = subprocess.run(["adb", "version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            print("⚠️  ADB not found. Please install android-tools.")
            return
    except Exception:
        print("⚠️  ADB not accessible. Make sure android-tools is installed.")
        return

    cli = AndroMancerCLI()
    initial_goal = sys.argv[1] if len(sys.argv) > 1 else None
    await cli.run(initial_goal)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
