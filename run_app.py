#!/usr/bin/env python3
"""
run_app.py
===========
Entry point for the VC Triage App.
Run with: python3 run_app.py
Then open: http://localhost:5000
"""

from app.routes import app

if __name__ == "__main__":
    print("=" * 50)
    print("  Health Check — Triage App")
    print("  Open in browser: http://localhost:5001")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5001)
