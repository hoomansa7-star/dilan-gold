# -*- coding: utf-8 -*-
"""
Vercel Serverless Function entrypoint for Dilan Gold ERP.
"""
import sys
import os

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server.main import app
