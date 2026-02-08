#!/usr/bin/env python3
import subprocess
import sys

if __name__ == "__main__":
    try:
        # Run the module
        subprocess.run([sys.executable, "-m", "andromancer"] + sys.argv[1:])
    except KeyboardInterrupt:
        pass
