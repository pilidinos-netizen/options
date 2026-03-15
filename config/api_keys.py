import os
import streamlit as st

def _get(key, default=""):
    # 1. Streamlit Cloud secrets (production)
    try:
        return st.secrets[key]
    except Exception:
        pass
    # 2. Environment variable (local .env or CI)
    return os.environ.get(key, default)

POLYGON_API_KEY   = _get("POLYGON_API_KEY")
ALPHA_VANTAGE_KEY = _get("ALPHA_VANTAGE_KEY", "")
