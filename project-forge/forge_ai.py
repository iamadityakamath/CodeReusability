#!/usr/bin/env python3
"""Compatibility wrapper for backend forge_ai implementation.

This keeps existing CLI/task usage unchanged while the implementation
lives in ReusableAI/backend/forge_ai.py.
"""

from ReusableAI.backend.forge_ai import *  # noqa: F403
from ReusableAI.backend.forge_ai import main


if __name__ == "__main__":
    raise SystemExit(main())
