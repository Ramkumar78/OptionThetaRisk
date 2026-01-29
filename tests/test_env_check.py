import sys
import os

def test_environment():
    print(f"Python executable: {sys.executable}")
    print(f"Path: {sys.path}")
    import flask
    print(f"Flask file: {flask.__file__}")
