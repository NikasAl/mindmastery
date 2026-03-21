#!/usr/bin/env python3
"""Entry point for MindMastery CLI."""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cli import main

if __name__ == "__main__":
    main()
