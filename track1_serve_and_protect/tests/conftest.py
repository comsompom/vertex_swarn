"""Pytest configuration and shared fixtures."""
import sys
import os

# Ensure package root is on path when running tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
