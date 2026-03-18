"""
Pytest configuration.

This file is automatically loaded by pytest before running tests.
It ensures the backend directory is in the Python path.
"""
import sys
from pathlib import Path

# Add backend directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))