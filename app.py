# app.py

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed

from main import run_quant_model
from engines.market_scanner import scan_market
from engines.market_screener import pre_screen
from config.market_universe import SP100, NASDAQ100, SECTORS, BROAD_MARKET
from engines.performance_engine import compute_performance_metrics
from engines.options_opportunity_engine import rank_option_opportunities
from engines.options_contract_engine import select_leaps_contract
from engines.options_payoff_engine import calculate_call_payoff
from engines.news_engine import get_market_news
from engines.social_sentiment_engine import run_market_sentiment_engine
from engines.market_news_sentiment_engine import get_market_news_sentiment
from engines.sentiment_stock_picker import identify_top_stocks


# ──────────────────────────────────────────────────────────────────────────────
# Page config — must be the very first Streamlit call
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Research Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# ──────────────────────────────────────────────────────────────────────────────
# Global CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Tabs ─────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
.stTabs [data-baseweb="tab"] {
    padding: 10px 22px;
    font-size: 14px;
    font-weight: 500;
    border-radius: 6px 6px 0 0;
    white-space: nowrap;
}

/* ── Metric cards ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] { font-size: 12px; opacity: 0.70; }
[data-testid="stMetricValue"] { font-size: 20px; font-weight: 700; }

/* ── Buttons ──────────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    border-radius: 8px;
    font-weight: 600;
    padding: 10px 26px;
    min-height: 44px;
}
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.15s;
    min-height: 44px;
}
.stButton > button:hover { transform: translateY(-1px); }

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #0e1117; }
[data-testid="stSidebar"] * { color: #e8eaf0 !important; }
[data-testid="stSidebar"] .stSelectbox label { color: #c8ccd8 !important; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown td,
[data-testid="stSidebar"] .stMarkdown th { color: #e8eaf0 !important; }
[data-testid="stSidebar"] caption,
[data-testid="stSidebar"] .stCaption { color: #a0a8b8 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }

/* ── Dataframe ────────────────────────────────────────────────────────────── */
.stDataFrame { font-size: 13px; overflow-x: auto; }

/* ── Alerts / dividers / expanders ───────────────────────────────────────── */
.stAlert { border-radius: 8px; }
hr { border-color: rgba(255,255,255,0.08) !important; }
.streamlit-expanderHeader { font-weight: 600; }

/* ── Touch-friendly select / input ───────────────────────────────────────── */
input, select, textarea { font-size: 16px !important; }

/* ══════════════════════════════════════════════════════════════════════════ */
/* TABLET  (≤ 900 px) — wrap columns 2-per-row                              */
/* ══════════════════════════════════════════════════════════════════════════ */
@media screen and (max-width: 900px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 4px 0 !important;
    }
    [data-testid="column"] {
        min-width: 47% !important;
        flex: 1 1 47% !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 14px !important;
        font-size: 13px !important;
    }
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* PHONE  (≤ 640 px) — full-width single column stack                       */
/* ══════════════════════════════════════════════════════════════════════════ */
@media screen and (max-width: 640px) {
    /* Single-column layout */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0 !important;
    }
    [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* Main container padding */
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 0.5rem !important;
    }

    /* Tabs — horizontal scroll strip */
    .stTabs [data-baseweb="tab"] {
        padding: 7px 10px !important;
        font-size: 11px !important;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] { font-size: 16px !important; }
    [data-testid="stMetricLabel"] { font-size: 10px !important; }

    /* Logo banner — stack vertically */
    .logo-banner {
        flex-direction: column !important;
        padding: 16px 18px !important;
        gap: 12px !important;
        align-items: flex-start !important;
    }
    .logo-banner .logo-title { font-size: 18px !important; }
    .logo-banner .logo-sub   { font-size: 11px !important; }

    /* Intent banner */
    .intent-banner {
        font-size: 16px !important;
        padding: 12px 16px !important;
    }

    /* Buttons — full width */
    .stButton > button { width: 100% !important; }

    /* Dataframe — horizontal scroll */
    .stDataFrame > div { overflow-x: auto !important; }

    /* Download button full width */
    [data-testid="stDownloadButton"] > button { width: 100% !important; }

    /* Expander header padding */
    .streamlit-expanderHeader { padding: 10px 12px !important; }

    /* Sidebar toggle bigger tap target */
    [data-testid="collapsedControl"] { padding: 12px !important; }
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AMD", "NFLX", "JPM",
]

INTENT_COLORS = {
    "STRONG BUY": ("#1a7a2e", "white"),
    "BUY":        ("#2e7d32", "white"),
    "HOLD":       ("#f9a825", "black"),
    "REDUCE":     ("#e65100", "white"),
    "SELL":       ("#b71c1c", "white"),
}

INTENT_ICONS = {
    "STRONG BUY": "🟢", "BUY": "🟩",
    "HOLD": "🟡", "REDUCE": "🟠", "SELL": "🔴",
}

PROFILE_OPTIONS = ["Conservative", "Balanced", "Aggressive", "Speculator"]

# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _resolve_tickers(universe_choice, selected_sectors, custom_input):
    """Convert universe selector state into a flat list of tickers."""
    if universe_choice == "S&P 100":
        return list(SP100)
    elif universe_choice == "NASDAQ 100":
        return list(NASDAQ100)
    elif universe_choice == "Broad Market (S&P100 + NASDAQ100)":
        return list(BROAD_MARKET)
    elif universe_choice == "Sector":
        raw = []
        for s in (selected_sectors or []):
            raw += SECTORS.get(s, [])
        return list(dict.fromkeys(raw))
    else:
        return [t.strip().upper() for t in (custom_input or "").split(",") if t.strip()]


def _universe_controls(prefix, default_top_n=30, show_top_n=True):
    """
    Render universe selector widgets. prefix must be unique per tab.
    Returns (universe_choice, selected_sectors, custom_input, top_n, min_mcap, min_vol)
    """
    UNIVERSE_OPTIONS = [
        "S&P 100", "NASDAQ 100", "Broad Market (S&P100 + NASDAQ100)",
        "Sector", "Custom",
    ]
    cols = st.columns([2, 1]) if show_top_n else [st.container()]
    with cols[0]:
        choice = st.selectbox("Universe", UNIVERSE_OPTIONS, key=f"{prefix}_universe")
    if show_top_n:
        with cols[1]:
            top_n = st.number_input(
                "Top N (by market cap)", min_value=5, max_value=150,
                value=default_top_n, step=5, key=f"{prefix}_top_n",
            )
    else:
        top_n = default_top_n

    sectors, custom = None, None
    if choice == "Sector":
        sectors = st.multiselect(
            "Select Sectors", list(SECTORS.keys()),
            default=["Technology"], key=f"{prefix}_sectors",
        )
    elif choice == "Custom":
        custom = st.text_area(
            "Tickers (comma-separated)", ",".join(DEFAULT_UNIVERSE),
            key=f"{prefix}_custom",
        )

    with st.expander("Pre-screen Filters", expanded=False):
        fc1, fc2 = st.columns(2)
        with fc1:
            min_mcap = st.number_input(
                "Min Market Cap ($B)", min_value=0.1, max_value=500.0,
                value=10.0, step=1.0, key=f"{prefix}_mcap",
            )
        with fc2:
            min_vol = st.number_input(
                "Min Avg Daily Volume", min_value=100_000, max_value=50_000_000,
                value=1_000_000, step=100_000, key=f"{prefix}_vol",
            )

    return choice, sectors, custom, int(top_n), min_mcap, int(min_vol)


def _run_prescreen(raw_tickers, top_n, min_mcap, min_vol, sectors):
    screened, failed = pre_screen(
        raw_tickers,
        min_market_cap_b=min_mcap,
        min_avg_volume=min_vol,
        sectors=sectors or [],
    )
    run_tickers = [r["Ticker"] for r in screened[:top_n]]
    summary = (
        f"{len(screened)} of {len(raw_tickers)} passed the screen — "
        f"running full model on top {len(run_tickers)}."
    )
    return run_tickers, summary, failed


# ── Styling helpers ───────────────────────────────────────────────────────────

def colour_intent(val):
    bg, fg = INTENT_COLORS.get(val, ("", ""))
    return f"background-color: {bg}; color: {fg}" if bg else ""


def colour_value(val):
    try:
        v = float(val)
        return "color: #2e7d32" if v > 15 else "color: #f9a825" if v > 0 else "color: #b71c1c"
    except (TypeError, ValueError):
        return ""


def colour_return(val):
    try:
        return "color: #2e7d32" if float(val) > 0 else "color: #b71c1c"
    except (TypeError, ValueError):
        return ""


def colour_rsi(val):
    try:
        v = float(val)
        if v > 70:
            return "color: #b71c1c"
        elif v < 30:
            return "color: #2e7d32"
        return ""
    except (TypeError, ValueError):
        return ""


def colour_sent_label(val):
    if val == "Bullish":
        return "color: #2e7d32"
    if val == "Bearish":
        return "color: #b71c1c"
    return "color: #f9a825"


def _intent_banner(ticker, intent):
    bg, fg = INTENT_COLORS.get(intent, ("#444", "white"))
    icon = INTENT_ICONS.get(intent, "")
    st.markdown(
        f'<div class="intent-banner" style="background:{bg};color:{fg};padding:16px 24px;border-radius:10px;'
        f'font-size:20px;font-weight:700;margin:12px 0;text-align:center;">'
        f'{icon} {ticker.upper()} — {intent}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _plotly_defaults():
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="rgba(255,255,255,0.85)",
        margin=dict(l=10, r=60, t=40, b=10),
    )


@st.cache_data(ttl=600)
def load_reddit_sentiment():
    return run_market_sentiment_engine()


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0 8px 0;">
  <svg width="36" height="36" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="36" cy="36" r="34" stroke="url(#sr)" stroke-width="1.5" fill="none" opacity="0.6"/>
    <circle cx="36" cy="36" r="30" fill="url(#sd)" opacity="0.9"/>
    <rect x="16" y="38" width="7" height="14" rx="1.5" fill="#10b981" opacity="0.9"/>
    <rect x="28" y="26" width="7" height="22" rx="1.5" fill="#10b981"/>
    <rect x="40" y="32" width="7" height="16" rx="1.5" fill="#34d399" opacity="0.85"/>
    <polyline points="16,46 28,36 40,38 56,20" stroke="url(#sl)" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <defs>
      <linearGradient id="sr" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#10b981"/><stop offset="100%" stop-color="#38bdf8"/>
      </linearGradient>
      <radialGradient id="sd" cx="36" cy="36" r="30" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#0d2137"/><stop offset="100%" stop-color="#060c18"/>
      </radialGradient>
      <linearGradient id="sl" x1="16" y1="46" x2="56" y2="20" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#10b981"/><stop offset="100%" stop-color="#38bdf8"/>
      </linearGradient>
    </defs>
  </svg>
  <div>
    <div style="font-size:13px;font-weight:700;color:#e2f5ff;line-height:1.2;">IIRP</div>
    <div style="font-size:10px;color:#7dd3fc;line-height:1.2;">Quant Research</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("## ⚙️ Platform Controls")
    st.divider()

    global_profile = st.selectbox(
        "Default Risk Profile",
        PROFILE_OPTIONS,
        key="global_profile",
        help="Applied to all tabs by default. Each tab can override independently.",
    )

    st.divider()
    st.markdown("### Quick Navigation")
    st.markdown("""
| Tab | Purpose |
|-----|---------|
| 📊 Stock Analysis | Full deep-dive on one ticker |
| 🌐 Market Scan | Cross-asset quant dashboard |
| 📈 Performance | Historical return metrics |
| 🎯 Options | Strategy scanner & LEAPS |
| 📰 Market News | Company news & impact |
| 💬 Sentiment | News + Reddit sentiment |
""")

    st.divider()
    st.markdown("### About")
    st.caption(
        "Intelligent Investment Research Platform  \n"
        "Multi-factor quant model · VADER NLP · Monte Carlo simulation  \n"
        "Multi-source options data (Polygon → yfinance → cache)"
    )

# ──────────────────────────────────────────────────────────────────────────────
# Page header — logo banner
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="logo-banner" style="
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1f3c 50%, #0a1628 100%);
    border: 1px solid rgba(56,189,248,0.18);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 28px;
    box-shadow: 0 4px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
    position: relative;
    overflow: hidden;
">

<!-- Glow orbs -->
<div style="
    position:absolute; top:-40px; left:60px;
    width:220px; height:220px;
    background: radial-gradient(circle, rgba(16,185,129,0.12) 0%, transparent 70%);
    pointer-events:none;
"></div>
<div style="
    position:absolute; top:-20px; right:100px;
    width:180px; height:180px;
    background: radial-gradient(circle, rgba(56,189,248,0.10) 0%, transparent 70%);
    pointer-events:none;
"></div>

<!-- Logo mark SVG -->
<svg width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
  <!-- Outer ring -->
  <circle cx="36" cy="36" r="34" stroke="url(#ring_grad)" stroke-width="1.5" fill="none" opacity="0.6"/>
  <!-- Background disc -->
  <circle cx="36" cy="36" r="30" fill="url(#disc_grad)" opacity="0.9"/>
  <!-- Candlestick bars -->
  <rect x="16" y="38" width="7" height="14" rx="1.5" fill="#10b981" opacity="0.9"/>
  <line x1="19.5" y1="35" x2="19.5" y2="38" stroke="#10b981" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="19.5" y1="52" x2="19.5" y2="55" stroke="#10b981" stroke-width="1.5" stroke-linecap="round"/>
  <rect x="28" y="26" width="7" height="22" rx="1.5" fill="#10b981" opacity="1"/>
  <line x1="31.5" y1="21" x2="31.5" y2="26" stroke="#10b981" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="31.5" y1="48" x2="31.5" y2="53" stroke="#10b981" stroke-width="1.5" stroke-linecap="round"/>
  <rect x="40" y="32" width="7" height="16" rx="1.5" fill="#34d399" opacity="0.85"/>
  <line x1="43.5" y1="28" x2="43.5" y2="32" stroke="#34d399" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="43.5" y1="48" x2="43.5" y2="52" stroke="#34d399" stroke-width="1.5" stroke-linecap="round"/>
  <!-- Trend line -->
  <polyline points="16,46 28,36 40,38 56,20" stroke="url(#line_grad)" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>
  <!-- Arrow head -->
  <polyline points="51,17 56,20 53,25" stroke="url(#line_grad)" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>
  <defs>
    <linearGradient id="ring_grad" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#38bdf8"/>
    </linearGradient>
    <radialGradient id="disc_grad" cx="36" cy="36" r="30" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0d2137"/>
      <stop offset="100%" stop-color="#060c18"/>
    </radialGradient>
    <linearGradient id="line_grad" x1="16" y1="46" x2="56" y2="20" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#38bdf8"/>
    </linearGradient>
  </defs>
</svg>

<!-- Text block -->
<div style="flex:1;">
  <div class="logo-title" style="
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.3px;
      line-height: 1.1;
      background: linear-gradient(90deg, #e2f5ff 0%, #a7f3d0 60%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
  ">Intelligent Investment Research Platform</div>
  <div class="logo-sub" style="
      margin-top: 7px;
      font-size: 13px;
      color: rgba(180,210,240,0.75);
      letter-spacing: 0.3px;
      line-height: 1.5;
  ">
    Multi-factor quant model &nbsp;·&nbsp; Options intelligence &nbsp;·&nbsp;
    Market sentiment &nbsp;·&nbsp; VADER NLP &nbsp;·&nbsp; Monte Carlo simulation
  </div>

  <!-- Pill badges -->
  <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
    <span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.35);color:#6ee7b7;
                 padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">
      ● LIVE DATA
    </span>
    <span style="background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.3);color:#7dd3fc;
                 padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">
      6-FACTOR MODEL
    </span>
    <span style="background:rgba(167,243,208,0.10);border:1px solid rgba(167,243,208,0.25);color:#a7f3d0;
                 padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">
      POLYGON · YFINANCE · CACHE
    </span>
    <span style="background:rgba(251,191,36,0.10);border:1px solid rgba(251,191,36,0.25);color:#fcd34d;
                 padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">
      BETA
    </span>
  </div>
</div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Main tabs
# ──────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Stock Analysis",
    "🌐 Market Scan",
    "📈 Performance",
    "🎯 Options Strategy",
    "📰 Market News",
    "💬 Sentiment Engine",
])


# =============================================================================
# TAB 1 — SINGLE STOCK ANALYSIS
# =============================================================================
with tab1:

    st.subheader("Single Stock Deep-Dive Analysis")
    st.caption(
        "Full 12-stage quant pipeline: fundamentals → factor scoring → intent → "
        "regime detection → risk management → Monte Carlo"
    )

    with st.expander("🎓 New Here? What This Tab Does & Why It Matters", expanded=False):
        st.markdown("""
        ### What is this tab for?
        Think of this tab as hiring a **professional stock analyst** for any company you're
        curious about — except it runs in seconds and is completely data-driven.

        You type in a stock ticker (like `AAPL` for Apple or `TSLA` for Tesla), choose how
        much risk you're comfortable with, and the platform runs a **12-step analysis** that
        professional quant funds use. Here's what happens under the hood — in plain English:

        ---

        #### Step 1 — Fetching the Company's Financial Report Card
        The platform pulls the company's real financial data: How fast is revenue growing?
        Are they profitable? Do they carry too much debt? This is like reading a company's
        annual report, but the computer does it instantly.

        #### Step 2 — Scoring 6 Key Factors
        Every company gets scored on 6 dimensions (like a school report card):
        - 📈 **Growth** — Is the business expanding? Revenue growing year-over-year?
        - 💰 **Profitability** — Do they actually make money after all expenses?
        - ⚙️ **Efficiency** — How well do they convert assets into profit?
        - 🏦 **Leverage** — How much debt do they carry? Too much debt = higher risk.
        - 💎 **ROE (Return on Equity)** — How much profit do they generate per dollar invested?
        - 🏷️ **Valuation** — Is the stock price reasonable compared to earnings (P/E ratio)?

        #### Step 3 — Detecting the Market Regime
        Is the broader market trending up (Bullish), going sideways (Neutral), or falling
        (Bearish)? This context shapes the recommendation.

        #### Step 4 — Classifying Intent
        Based on all scores and your risk tolerance, the model outputs a clear signal:
        **STRONG BUY / BUY / HOLD / REDUCE / SELL**.

        #### Step 5 — Risk Management
        The platform calculates how volatile (jumpy) the stock is and adjusts the
        suggested position size accordingly. High volatility = smaller position = less risk.

        #### Step 6 — Monte Carlo Simulation
        Runs 1,000 different simulated futures for the stock price over 1 year using
        historical patterns. The result is the **average projected price** — not a guarantee,
        but a probability-weighted estimate.

        ---

        ### How to use it
        1. Type a stock ticker in the box (e.g. `NVDA`, `MSFT`, `JPM`)
        2. Select your **Risk Profile** — Conservative if you want safety, Speculator if you
           want aggressive signals
        3. Click **Run Full Analysis**
        4. Read the intent banner (green = buy signal, red = sell signal)
        5. Scroll down to see the factor breakdown and full reasoning

        > 💡 **Tip:** Start with a company you already know — like `AAPL` (Apple) or
        > `AMZN` (Amazon) — so you can compare the model's output to what you already
        > know about the company.
        """)

    with st.expander("📘 Glossary — What All These Terms Mean"):
        st.markdown("""
        ### Intent
        The system's overall recommendation signal:
        - **STRONG BUY** → Very high conviction — all factor and volatility thresholds met for the selected profile
        - **BUY** → Positive outlook — strong factor score within acceptable volatility bounds
        - **HOLD** → Neutral — insufficient edge to act aggressively in either direction
        - **REDUCE** → Weakening outlook — consider trimming existing position
        - **SELL** → Negative outlook — model recommends exiting

        ### Confidence (0–100)
        Strength of the signal. Derived from the composite score relative to the profile's
        STRONG BUY threshold. 100% means the score hits or exceeds the upper bound.

        ### Volatility
        Annualised standard deviation of daily log returns over the past year.
        High volatility = larger price swings. Low volatility = more stable movement.
        Conservative profiles are penalised more aggressively for high volatility.

        ### Composite Score
        Weighted sum of 6 normalised factor scores:
        - Growth (25%) · Profitability (20%) · Efficiency (20%)
        - Leverage (15%) · ROE (10%) · Valuation (10%)

        Max ≈ 3.45 · Min ≈ −1.60. STRONG BUY threshold: 3.0 (Balanced profile).

        ### Regime
        Market condition inferred from momentum and volatility signals:
        - **Bullish** → Uptrend likely
        - **Neutral** → Sideways / range-bound
        - **Bearish** → Downtrend risk

        ### Position Size (%)
        Suggested portfolio allocation. Starts from the base risk profile allocation and
        is automatically reduced (×0.75 or ×0.50) when volatility exceeds profile thresholds.

        ### Monte Carlo Projection
        Mean of 1,000 Geometric Brownian Motion paths estimating the price in one year.
        Uses historical drift and volatility. Does NOT guarantee returns.
        """)

    st.divider()

    in_c1, in_c2 = st.columns([2, 1])
    with in_c1:
        ticker = st.text_input("Stock Ticker Symbol", placeholder="e.g. NVDA, AAPL, MSFT, TSLA")
    with in_c2:
        profile = st.selectbox(
            "Risk Profile",
            PROFILE_OPTIONS,
            index=PROFILE_OPTIONS.index(global_profile),
            key="t1_profile",
        )

    if st.button("Run Full Analysis", type="primary", key="t1_run"):
        if not ticker.strip():
            st.warning("Please enter a ticker symbol.")
        else:
            with st.spinner(f"Running full 12-stage quant model on {ticker.upper()}..."):
                result = run_quant_model(ticker.upper(), profile)

            intent = result.get("Intent", "HOLD")

            # ── Intent banner ──────────────────────────────────────────────
            _intent_banner(ticker, intent)

            # ── Core metrics ───────────────────────────────────────────────
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Intent",            intent)
            m2.metric("Confidence",        f"{result.get('Confidence', 0)}%")
            m3.metric("Composite Score",   f"{result.get('Factor Scores', {}).get('total', 0):.2f}")
            m4.metric("Regime",            result.get("Regime", "N/A"))
            m5.metric("Ann. Volatility",   f"{result.get('Volatility', 0) * 100:.1f}%")
            m6.metric("Position Size",     f"{result.get('Position Size (%)', 0)}%")

            mc_val = result.get("Monte Carlo Projection (1Y)", 0)
            st.metric("Monte Carlo 1Y Projection", f"${mc_val:,.2f}")

            st.divider()

            # ── Risk flag + options strategy ───────────────────────────────
            rf_c, strat_c = st.columns(2)
            with rf_c:
                rf = result.get("Risk Flag", "")
                if rf:
                    st.warning(f"⚠️ **Risk Flag:** {rf}")
                else:
                    st.success("✅ No risk flags raised")
            with strat_c:
                st.info(
                    f"**Recommended Options Strategy**  \n"
                    f"`{result.get('Options Strategy', 'N/A')}`"
                )

            st.divider()

            # ── Factor score breakdown ─────────────────────────────────────
            st.markdown("### Factor Score Breakdown")
            scores = result.get("Factor Scores", {})
            factor_order = [
                ("Growth (25%)",        "growth"),
                ("Profitability (20%)", "profitability"),
                ("Efficiency (20%)",    "efficiency"),
                ("Leverage (15%)",      "leverage"),
                ("ROE (10%)",           "roe"),
                ("Valuation (10%)",     "valuation"),
            ]

            f_cols = st.columns(6)
            for col, (label, key) in zip(f_cols, factor_order):
                col.metric(label, f"{scores.get(key, 0):+.2f}")

            factor_labels = [f[0] for f in factor_order]
            factor_vals   = [scores.get(f[1], 0) for f in factor_order]
            bar_colors    = ["#2e7d32" if v >= 0 else "#b71c1c" for v in factor_vals]

            fig_factors = go.Figure(go.Bar(
                x=factor_vals,
                y=factor_labels,
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:+.2f}" for v in factor_vals],
                textposition="outside",
            ))
            fig_factors.update_layout(
                height=270,
                xaxis=dict(title="Score", zeroline=True, zerolinecolor="rgba(255,255,255,0.3)"),
                **_plotly_defaults(),
            )
            st.plotly_chart(fig_factors, use_container_width=True)

            st.divider()

            # ── Qualitative & quantitative reasoning ───────────────────────
            reasoning = result.get("Reasoning", "")
            if reasoning:
                st.markdown("### Qualitative & Quantitative Reasoning")
                st.text(reasoning)

            # ── Timing plan ────────────────────────────────────────────────
            timing = result.get("Timing Plan", "")
            if timing:
                st.divider()
                st.markdown("### Timing Plan")
                st.info(timing)


# =============================================================================
# TAB 2 — MARKET SCAN
# =============================================================================
with tab2:

    st.subheader("Market Scan — Quant Cross-Asset Dashboard")
    st.caption(
        "Parallel scan across your selected universe with full factor scoring, "
        "momentum, RSI, fundamentals, and risk analysis"
    )

    with st.expander("🎓 New Here? What This Tab Does & Why It Matters", expanded=False):
        st.markdown("""
        ### What is this tab for?
        Instead of analysing one stock at a time, this tab scans **an entire group of stocks
        simultaneously** — like having 100 analysts working in parallel — and ranks them all
        so you can instantly spot the best opportunities.

        This is how professional portfolio managers and quant hedge funds decide **where to
        focus their attention** across the market each day.

        ---

        ### What can you scan?
        Choose from pre-built universes or build your own:
        - **S&P 100** — America's 100 largest companies (Apple, Microsoft, ExxonMobil, etc.)
        - **NASDAQ 100** — Top 100 tech-heavy stocks (NVIDIA, Google, Meta, Tesla, etc.)
        - **Broad Market** — Combined S&P 100 + NASDAQ 100 (~170 unique stocks)
        - **Sector** — Focus on one industry (e.g. only Energy or only Technology)
        - **Custom** — Type in your own list of tickers

        ### What does "Pre-screen" mean?
        Before running the expensive full analysis on every stock, the platform quickly
        filters out stocks that are too small or trade too little. This saves time and
        focuses the analysis on stocks you can actually trade.

        ---

        ### What do the results tell you?

        #### 📋 Signal & Risk tab
        The main dashboard — shows every stock's **buy/sell signal, confidence score,
        volatility, and recommended options strategy** at a glance.

        #### 💰 Fundamentals tab
        The financial report card for every stock: revenue growth, profit margins, P/E ratio
        (is the stock expensive?), and return on equity. Lets you spot companies with strong
        business fundamentals vs. hype-driven stocks.

        #### 📈 Momentum tab
        Shows recent **price performance** (1-month, 3-month, 6-month returns) and RSI.
        RSI (Relative Strength Index) tells you if a stock is *overbought* (>70, might fall)
        or *oversold* (<30, might recover). Great for timing.

        #### 🔬 Factor Heatmap tab
        A colour-coded grid showing how each stock scores on all 6 factors.
        **Dark green = strong, dark red = weak.** Lets you see patterns across the whole
        market instantly — e.g. if the Energy sector is uniformly green on Profitability.

        #### 🏭 Sector Breakdown tab
        Groups the results by industry sector and shows the **average quant score per sector**.
        Useful for spotting which industries the model is most bullish on right now.

        ---

        ### How to use it
        1. Select **Risk Profile** and **Universe** (start with S&P 100 or NASDAQ 100)
        2. Set **Top N** to 30 — a good balance of breadth vs. speed
        3. Click **Run Market Scan** and wait for the parallel scan to complete
        4. Look at the pie chart first — if most stocks are green (BUY/STRONG BUY), the
           market is in good shape. If most are red, be cautious.
        5. Click into the inner tabs to drill into fundamentals, momentum, or factor details

        > 💡 **Tip:** Use the **CSV download button** to export results into Excel for
        > further analysis or to keep a record of the market snapshot over time.
        """)

    snap_profile = st.selectbox(
        "Risk Profile",
        PROFILE_OPTIONS,
        index=PROFILE_OPTIONS.index(global_profile),
        key="snap_profile",
    )
    universe_choice, selected_sectors, custom_input, top_n, min_mcap, min_vol = \
        _universe_controls("t2")

    if st.button("Run Market Scan", type="primary", key="run_snapshot"):
        raw_tickers = _resolve_tickers(universe_choice, selected_sectors, custom_input)
        if not raw_tickers:
            st.warning("No tickers to scan.")
            st.stop()

        with st.spinner(f"Pre-screening {len(raw_tickers)} tickers..."):
            run_tickers, summary, failed = _run_prescreen(
                raw_tickers, top_n, min_mcap, min_vol, selected_sectors
            )

        st.success(summary)
        if failed:
            with st.expander(f"{len(failed)} tickers failed pre-screen"):
                st.write(", ".join(sorted(failed)))
        if not run_tickers:
            st.warning("No tickers passed the screen. Loosen your filters.")
            st.stop()

        progress_bar = st.progress(0)
        status_text  = st.empty()

        def update_progress(done, total):
            progress_bar.progress(int(done / total * 100))
            status_text.text(f"Scanning {done}/{total} tickers...")

        with st.spinner("Running full quant model in parallel..."):
            results = scan_market(
                run_tickers, run_quant_model, snap_profile,
                max_workers=8, progress_cb=update_progress,
            )

        progress_bar.empty()
        status_text.empty()

        if not results:
            st.warning("No results returned.")
            st.stop()

        st.session_state["scan_results"] = pd.DataFrame(results)

    df_all = st.session_state.get("scan_results")

    if df_all is not None and not df_all.empty:

        # ── Signal count bar ───────────────────────────────────────────────
        signal_counts = df_all["Intent"].value_counts()
        order = ["STRONG BUY", "BUY", "HOLD", "REDUCE", "SELL"]
        col_sb, col_b, col_h, col_r, col_s = st.columns(5)
        for col, label, icon in zip(
            [col_sb, col_b, col_h, col_r, col_s], order,
            ["🟢", "🟩", "🟡", "🟠", "🔴"],
        ):
            col.metric(f"{icon} {label}", signal_counts.get(label, 0))

        csv_bytes = df_all.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download Full Scan as CSV", csv_bytes,
            "market_scan.csv", "text/csv",
        )

        st.divider()

        # ── Charts row ─────────────────────────────────────────────────────
        ch_c1, ch_c2 = st.columns(2)
        with ch_c1:
            sig_df = signal_counts.reindex(order).dropna()
            fig_pie = go.Figure(go.Pie(
                labels=sig_df.index,
                values=sig_df.values,
                hole=0.4,
                marker_colors=["#1a7a2e", "#2e7d32", "#f9a825", "#e65100", "#b71c1c"][:len(sig_df)],
                textinfo="label+percent",
            ))
            fig_pie.update_layout(
                title="Signal Distribution",
                height=320,
                showlegend=False,
                **_plotly_defaults(),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with ch_c2:
            score_df = df_all[["Ticker", "Composite Score"]].sort_values("Composite Score")
            bar_colors = [
                "#1a7a2e" if s >= 3.0 else "#2e7d32" if s >= 1.8
                else "#f9a825" if s >= 0.8 else "#e65100" if s >= 0.0
                else "#b71c1c"
                for s in score_df["Composite Score"]
            ]
            fig_bar = go.Figure(go.Bar(
                x=score_df["Composite Score"],
                y=score_df["Ticker"],
                orientation="h",
                marker_color=bar_colors,
                text=score_df["Composite Score"].round(2),
                textposition="outside",
            ))
            fig_bar.add_vline(x=3.0, line_dash="dash", line_color="#1a7a2e",
                              annotation_text="Strong Buy", annotation_position="top right")
            fig_bar.add_vline(x=1.8, line_dash="dash", line_color="#f9a825",
                              annotation_text="Buy", annotation_position="top right")
            fig_bar.update_layout(
                title="Composite Score by Ticker",
                height=max(320, len(score_df) * 22),
                xaxis_title="Composite Score",
                **_plotly_defaults(),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # ── Data panels in inner tabs ──────────────────────────────────────
        dtab1, dtab2, dtab3, dtab4, dtab5 = st.tabs([
            "📋 Signal & Risk",
            "💰 Fundamentals",
            "📈 Momentum",
            "🔬 Factor Heatmap",
            "🏭 Sector Breakdown",
        ])

        with dtab1:
            SIGNAL_COLS = [
                "Ticker", "Name", "Sector", "Intent", "Confidence",
                "Composite Score", "Regime", "Ann. Vol (%)",
                "Risk Flag", "Position Size (%)", "Options Strategy",
            ]
            st.dataframe(
                df_all[SIGNAL_COLS].style
                .applymap(colour_intent, subset=["Intent"])
                .format({"Composite Score": "{:.2f}", "Confidence": "{:.0f}"}),
                use_container_width=True, height=520,
            )

        with dtab2:
            FUND_COLS = [
                "Ticker", "Rev Growth (%)", "Gross Margin (%)", "Op Margin (%)",
                "Fwd P/E", "ROE (%)", "Market Cap",
            ]
            st.dataframe(
                df_all[FUND_COLS].style
                .applymap(colour_value, subset=["Rev Growth (%)", "Op Margin (%)", "ROE (%)"]),
                use_container_width=True, height=520,
            )

        with dtab3:
            MOM_COLS = [
                "Ticker", "1M Ret (%)", "3M Ret (%)", "6M Ret (%)",
                "52W Range (%)", "RSI-14",
            ]
            st.dataframe(
                df_all[MOM_COLS].style
                .applymap(colour_return, subset=["1M Ret (%)", "3M Ret (%)", "6M Ret (%)"])
                .applymap(colour_rsi, subset=["RSI-14"]),
                use_container_width=True, height=520,
            )

        with dtab4:
            FACTOR_COLS = [
                "Ticker", "F:Growth", "F:Profitability", "F:Efficiency",
                "F:Leverage", "F:ROE", "F:Valuation", "Composite Score",
            ]
            st.dataframe(
                df_all[FACTOR_COLS].set_index("Ticker").style
                .background_gradient(cmap="RdYlGn", vmin=-3, vmax=5)
                .format("{:.2f}"),
                use_container_width=True, height=520,
            )

        with dtab5:
            sector_df = (
                df_all.groupby("Sector")["Composite Score"]
                .agg(["count", "mean"])
                .rename(columns={"count": "Tickers", "mean": "Avg Score"})
                .sort_values("Avg Score", ascending=False)
                .reset_index()
            )
            sector_df["Avg Score"] = sector_df["Avg Score"].round(2)

            sec_c1, sec_c2 = st.columns([1, 1])
            with sec_c1:
                st.dataframe(sector_df, use_container_width=True)
            with sec_c2:
                fig_sec = px.bar(
                    sector_df.sort_values("Avg Score"),
                    x="Avg Score", y="Sector", orientation="h",
                    color="Avg Score",
                    color_continuous_scale=["#b71c1c", "#f9a825", "#2e7d32"],
                    text="Avg Score",
                )
                fig_sec.update_layout(
                    height=max(260, len(sector_df) * 40),
                    coloraxis_showscale=False,
                    **_plotly_defaults(),
                )
                st.plotly_chart(fig_sec, use_container_width=True)


# =============================================================================
# TAB 3 — PERFORMANCE DASHBOARD
# =============================================================================
with tab3:

    st.subheader("Historical Performance Metrics")
    st.caption(
        "Annualised return, volatility, Sharpe ratio, and max drawdown computed from 1-year price history"
    )

    with st.expander("🎓 New Here? What This Tab Does & Why It Matters", expanded=False):
        st.markdown("""
        ### What is this tab for?
        This tab answers the question: **"How has this stock actually performed?"**

        While Tab 1 tells you what to *expect* in the future, this tab shows you what
        *already happened* — using real historical price data. It's like checking a fund
        manager's track record before trusting their future recommendations.

        ---

        ### The 5 metrics explained in plain English

        #### 📊 Total Return (%)
        The simple answer: if you had bought this stock 1 year ago and held it, how much
        money would you have made (or lost)? e.g. +45% means a $10,000 investment is now
        worth $14,500.

        #### 📅 Annual Return (%)
        The return expressed as a yearly percentage, adjusted for compounding.
        This makes it easy to compare stocks held for different time periods.

        #### 🌊 Annual Volatility (%)
        How "bumpy" was the ride? A stock with 60% volatility swings wildly — great if it
        goes up, terrifying if it drops. A stock with 15% volatility is much smoother.
        Lower volatility = better sleep at night.

        #### ⚖️ Sharpe Ratio
        This is the **most important metric** on this page. It measures how much return
        you got *per unit of risk taken*. Think of it as "bang for your buck":
        - **> 2.0** → Excellent — high return for the risk
        - **1.0 – 2.0** → Good
        - **0 – 1.0** → Mediocre — you're taking risk but not being well compensated
        - **< 0** → Poor — you'd have been better off in cash

        The **top 3 Sharpe ratio stocks are highlighted in green** in the comparison table.

        #### 📉 Max Drawdown (%)
        The worst-case loss from peak to trough during the period. A -40% drawdown means
        the stock fell 40% from its high point before recovering. This tells you the worst
        pain you would have experienced as a holder.

        ---

        ### Single Stock vs. Compare Universe

        **📌 Single Stock** — Deep-dive on one company's historical performance. Great for
        due diligence before investing.

        **🔄 Compare Universe** — Scan an entire group of stocks and rank them by Sharpe
        Ratio. The bar chart makes it immediately obvious which stocks gave the best
        risk-adjusted returns. Use this to build a shortlist of historically strong performers.

        ---

        > 💡 **Tip:** A stock can have a great Sharpe Ratio historically but a weak quant
        > score in Tab 1 — that means its best days may be behind it. Ideally you want
        > both: strong past performance AND a positive forward-looking signal.
        """)

    perf_t1, perf_t2 = st.tabs(["📌 Single Stock", "🔄 Compare Universe"])

    # ── Single Stock ──────────────────────────────────────────────────────────
    with perf_t1:
        perf_ticker = st.text_input(
            "Ticker for Performance Review", "NVDA", key="perf_single_ticker"
        )
        if st.button("Analyze Performance", type="primary", key="perf_single_btn"):
            with st.spinner(f"Computing performance metrics for {perf_ticker.upper()}..."):
                metrics = compute_performance_metrics(perf_ticker.upper())

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Return",  f"{metrics['Total Return (%)']:+.1f}%")
            m2.metric("Annual Return", f"{metrics['Annual Return (%)']:+.1f}%")
            m3.metric("Annual Vol",    f"{metrics['Annual Volatility (%)']:.1f}%")
            m4.metric("Sharpe Ratio",  f"{metrics['Sharpe Ratio']:.2f}")
            m5.metric("Max Drawdown",  f"{metrics['Max Drawdown (%)']:.1f}%")

    # ── Compare Universe ──────────────────────────────────────────────────────
    with perf_t2:
        universe_choice, selected_sectors, custom_input, top_n, min_mcap, min_vol = \
            _universe_controls("t3", default_top_n=20)

        sort_by = st.selectbox(
            "Sort results by",
            ["Sharpe Ratio", "Annual Return (%)", "Total Return (%)", "Max Drawdown (%)"],
            key="perf_sort_by",
        )

        if st.button("Compare Performance", type="primary", key="perf_compare"):
            raw_tickers = _resolve_tickers(universe_choice, selected_sectors, custom_input)
            if not raw_tickers:
                st.warning("No tickers to scan.")
                st.stop()

            with st.spinner(f"Pre-screening {len(raw_tickers)} tickers..."):
                run_tickers, summary, failed = _run_prescreen(
                    raw_tickers, top_n, min_mcap, min_vol, selected_sectors
                )
            st.success(summary)
            if failed:
                with st.expander(f"{len(failed)} failed to fetch"):
                    st.write(", ".join(failed))
            if not run_tickers:
                st.warning("No tickers passed. Loosen your filters.")
                st.stop()

            perf_bar    = st.progress(0)
            perf_status = st.empty()

            def _fetch_perf(t):
                try:
                    m = compute_performance_metrics(t)
                    m["Ticker"] = t
                    return m
                except Exception:
                    return None

            rows = []
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(_fetch_perf, t): t for t in run_tickers}
                done = 0
                for future in as_completed(futures):
                    r = future.result()
                    if r:
                        rows.append(r)
                    done += 1
                    perf_bar.progress(int(done / len(run_tickers) * 100))
                    perf_status.text(f"Fetching {done}/{len(run_tickers)}...")

            perf_bar.empty()
            perf_status.empty()

            if not rows:
                st.warning("No performance data returned.")
                st.stop()

            ascending = sort_by == "Max Drawdown (%)"
            st.session_state["perf_results"] = (
                pd.DataFrame(rows).set_index("Ticker")
                .sort_values(sort_by, ascending=ascending)
            )

        df_perf = st.session_state.get("perf_results")
        if df_perf is not None and not df_perf.empty:

            top3_idx = set(df_perf["Sharpe Ratio"].nlargest(3).index)

            def colour_perf(val):
                try:
                    return "color: #2e7d32" if float(val) > 0 else "color: #b71c1c"
                except (TypeError, ValueError):
                    return ""

            st.markdown("### Performance Comparison  *(top 3 Sharpe highlighted)*")
            st.dataframe(
                df_perf.style
                .applymap(colour_perf, subset=["Total Return (%)", "Annual Return (%)", "Max Drawdown (%)"])
                .format("{:.2f}")
                .apply(
                    lambda row: [
                        "background-color: rgba(46,125,50,0.18)" if row.name in top3_idx else ""
                        for _ in row
                    ],
                    axis=1,
                ),
                use_container_width=True,
            )

            sharpe_sorted = df_perf["Sharpe Ratio"].sort_values()
            bar_c = ["#2e7d32" if v > 1 else "#f9a825" if v > 0 else "#b71c1c"
                     for v in sharpe_sorted]

            fig_sharpe = go.Figure(go.Bar(
                x=sharpe_sorted.values,
                y=sharpe_sorted.index,
                orientation="h",
                marker_color=bar_c,
                text=sharpe_sorted.round(2),
                textposition="outside",
            ))
            fig_sharpe.add_vline(x=1.0, line_dash="dash", line_color="white",
                                 annotation_text="Sharpe = 1", annotation_position="top right")
            fig_sharpe.update_layout(
                title="Sharpe Ratio Comparison",
                height=max(320, len(sharpe_sorted) * 22),
                xaxis_title="Sharpe Ratio",
                **_plotly_defaults(),
            )
            st.plotly_chart(fig_sharpe, use_container_width=True)


# =============================================================================
# TAB 4 — OPTIONS STRATEGY CENTER
# =============================================================================
with tab4:

    st.subheader("Options Strategy Center")
    st.caption(
        "Market-wide opportunity scanner · LEAPS contract generator · Interactive payoff diagrams"
    )

    with st.expander("🎓 New Here? What Options Are & Why This Tab Matters", expanded=False):
        st.markdown("""
        ### What is an option? (Plain English)
        An **option** is a contract that gives you the *right* (but not the obligation) to
        buy or sell a stock at a **set price** on or before a **set date**.

        **Example:** Apple is trading at $200. You buy a **Call Option** with a strike of
        $210 expiring in 3 months for a premium (cost) of $5 per share. If Apple rises to
        $230, your option is now worth $20 — a **4× return** on just $5 invested.
        If Apple stays below $210, you lose your $5 premium. That's your *maximum loss*.

        Options let you **control more stock with less money** — but they also expire
        worthless if wrong, so strategy and timing matter enormously.

        ---

        ### Why use options instead of just buying stock?
        | | Buying Stock | Buying an Option |
        |--|--|--|
        | **Capital required** | Full share price | Small premium (5-15% of stock price) |
        | **Max loss** | Full investment | Just the premium paid |
        | **Max gain** | Unlimited | Unlimited (calls) |
        | **Time pressure** | Hold forever | Must be right before expiry |

        ---

        ### What does this tab do?

        #### 🏆 Top Marketplace Opportunities
        Scans a universe of stocks and finds the **10 best options setups** right now —
        ranked by a score combining: model confidence, how cheap/expensive the option
        premium is (implied volatility), liquidity (how easily you can trade it), and
        alignment with the current market regime.

        Think of it like a **job board for options trades** — surfacing the setups with
        the best risk/reward based on all available data.

        #### 📃 LEAPS Generator
        **LEAPS** (Long-term Equity Anticipation Securities) are options with expiry dates
        **10+ months in the future**. They behave more like owning stock but cost far less.
        Many professional investors use LEAPS as a stock substitute.

        The generator finds the optimal LEAPS call contract for any stock and shows:
        - **Strike price** — the price at which you can buy the stock
        - **Premium** — what you pay today for the contract
        - **Break-even** — what price the stock must reach for you to profit
        - **Greeks** — Delta (how much the option moves per $1 stock move), Theta
          (daily time decay cost), Vega (sensitivity to volatility changes)
        - **Interactive P&L chart** — shows your profit/loss at every possible stock price
          at expiration. Hover over it to see exact numbers.

        ---

        ### Risk Profiles & Options Strategy
        The platform recommends different strategies based on your risk tolerance:
        - **Conservative** → Sell Cash-Secured Puts (income-generating, limited downside)
        - **Balanced** → Bull Call Spreads (defined risk, moderate upside)
        - **Aggressive** → Buy LEAPS Calls (larger upside, time decay risk)
        - **Speculator** → Buy OTM Calls (lottery-ticket style, high risk/high reward)

        > ⚠️ **Warning for beginners:** Options are powerful but complex. Start by reading
        > the P&L chart for a LEAPS contract to understand how profit and loss work before
        > trading real money.
        """)

    with st.expander("📘 How Options Opportunities Are Scored"):
        st.markdown("""
        Options opportunities are ranked using a multi-factor scoring system:

        | Factor | What It Measures |
        |--------|-----------------|
        | **Model confidence** | Strength of the quant signal (0–100%) |
        | **Implied volatility** | How much premium is priced in — higher IV = richer option premium |
        | **Stock volatility** | Price movement potential relative to option cost |
        | **Liquidity** | Open interest + bid-ask spread — ease of entry and exit |
        | **Strategy alignment** | Recommended strategy fit for current market regime |

        **Higher Opportunity Score = Better overall setup.**

        LEAPS contracts target expirations ≥ 10 months out for longer-duration
        directional exposure with defined risk.

        Options data sourced via **Polygon.io → yfinance → local cache fallback**.
        """)

    profile_opt = st.selectbox(
        "Risk Profile",
        PROFILE_OPTIONS,
        index=PROFILE_OPTIONS.index(global_profile),
        key="options_profile",
    )

    opt_t1, opt_t2 = st.tabs(["🏆 Top Marketplace Opportunities", "📃 LEAPS Generator"])

    # ── Mode 1: Top Marketplace Opportunities ────────────────────────────────
    with opt_t1:
        universe_choice_opt, selected_sectors_opt, custom_input_opt, top_n_opt, min_mcap_opt, min_vol_opt = \
            _universe_controls("t4", default_top_n=40)

        if st.button("Scan Marketplace for Top Opportunities", type="primary", key="scan_options"):
            raw_tickers = _resolve_tickers(
                universe_choice_opt, selected_sectors_opt, custom_input_opt
            )
            if not raw_tickers:
                st.warning("No tickers to scan.")
                st.stop()

            with st.spinner(f"Pre-screening {len(raw_tickers)} tickers..."):
                run_tickers, summary, failed = _run_prescreen(
                    raw_tickers, top_n_opt, min_mcap_opt, min_vol_opt, selected_sectors_opt
                )
            st.success(summary)
            if failed:
                with st.expander(f"{len(failed)} failed to fetch"):
                    st.write(", ".join(failed))
            if not run_tickers:
                st.warning("No tickers passed. Loosen your filters.")
                st.stop()

            with st.spinner("Ranking option opportunities..."):
                opt_results = rank_option_opportunities(run_tickers, run_quant_model, profile_opt)
            st.session_state["opt_results"] = opt_results

        opt_results = st.session_state.get("opt_results")
        if opt_results:
            st.markdown("### Top Option Opportunities")
            df_opt = pd.DataFrame(opt_results)

            def _col_intent_opt(v):
                bg, fg = INTENT_COLORS.get(v, ("", ""))
                return f"background-color: {bg}; color: {fg}" if bg else ""

            st.dataframe(
                df_opt.style.applymap(_col_intent_opt, subset=["Intent"])
                if "Intent" in df_opt.columns else df_opt,
                use_container_width=True,
            )
        elif opt_results is not None:
            st.warning("No valid option opportunities found.")

    # ── Mode 2: LEAPS Generator ───────────────────────────────────────────────
    with opt_t2:
        opt_ticker = st.text_input("Ticker for LEAPS", "NVDA", key="leaps_ticker")

        if st.button("Generate LEAPS Contract", type="primary", key="gen_leaps"):
            with st.spinner(f"Finding optimal LEAPS contract for {opt_ticker.upper()}..."):
                contract = select_leaps_contract(opt_ticker.upper())
            st.session_state["leaps_contract"] = (contract, opt_ticker.upper())

        leaps_data = st.session_state.get("leaps_contract")
        if leaps_data:
            contract, leaps_tkr = leaps_data
            strike    = contract.get("Strike", 0)
            premium   = contract.get("Premium", 0)
            break_even = round(strike + premium, 2)

            st.markdown(f"### LEAPS Contract — {leaps_tkr}")

            lc1, lc2, lc3, lc4, lc5 = st.columns(5)
            lc1.metric("Strike Price",   f"${strike:,.2f}")
            lc2.metric("Premium (Cost)", f"${premium:,.2f}")
            lc3.metric("Break-Even",     f"${break_even:,.2f}")
            lc4.metric("Expiry",         contract.get("Expiry", "N/A"))
            lc5.metric("Type",           contract.get("Type", "Call"))

            greeks_keys = ["Delta", "Gamma", "Theta", "Vega"]
            extra_keys  = ["IV", "Open Interest", "Bid", "Ask"]
            all_extra   = {k: contract.get(k) for k in greeks_keys + extra_keys
                           if contract.get(k) is not None}
            if all_extra:
                ex_cols = st.columns(len(all_extra))
                for col, (k, v) in zip(ex_cols, all_extra.items()):
                    try:
                        fmt = f"{float(v):.4f}" if k in greeks_keys else str(v)
                        col.metric(k, fmt)
                    except (TypeError, ValueError):
                        col.metric(k, str(v))

            st.divider()

            # ── P&L chart ──────────────────────────────────────────────────
            price_range = np.linspace(strike * 0.5, strike * 1.8, 150)
            payoff      = calculate_call_payoff(strike, premium, price_range)

            fig_pnl = go.Figure()
            fig_pnl.add_trace(go.Scatter(
                x=price_range, y=payoff,
                mode="lines",
                line=dict(color="#2196F3", width=2.5),
                fill="tozeroy",
                fillcolor="rgba(33,150,243,0.08)",
                name="P&L",
                hovertemplate="Stock price: $%{x:,.2f}<br>P&L: $%{y:,.2f}<extra></extra>",
            ))
            fig_pnl.add_hline(y=0, line_color="rgba(255,255,255,0.35)")
            fig_pnl.add_vline(
                x=break_even, line_color="#f9a825", line_dash="dash",
                annotation_text=f"Break-even ${break_even:,.0f}",
                annotation_position="top right",
            )
            fig_pnl.add_vline(
                x=strike, line_color="rgba(255,255,255,0.3)", line_dash="dot",
                annotation_text=f"Strike ${strike:,.0f}",
                annotation_position="top left",
            )
            fig_pnl.update_layout(
                title=f"LEAPS P&L at Expiration — {leaps_tkr}",
                xaxis_title="Stock Price at Expiration ($)",
                yaxis_title="Profit / Loss ($)",
                height=400,
                margin=dict(l=10, r=10, t=50, b=40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
            )
            st.plotly_chart(fig_pnl, use_container_width=True)

            with st.expander("Full Contract Data (raw JSON)"):
                st.json(contract)


# =============================================================================
# TAB 5 — MARKET NEWS
# =============================================================================
with tab5:

    st.subheader("Market News & Impact Analysis")
    st.caption("Company-specific news, VADER sentiment scoring, and ecosystem mapping")

    with st.expander("🎓 New Here? What This Tab Does & Why It Matters", expanded=False):
        st.markdown("""
        ### What is this tab for?
        News moves stock prices. This tab automatically **reads, analyses, and scores** the
        latest news about any company you search for — so you don't have to manually sift
        through hundreds of articles.

        It uses **VADER** (Valence Aware Dictionary and sEntiment Reasoner), an AI model
        originally developed at Georgia Tech, to assign a sentiment score to every article.
        This is the same class of technology used by hedge funds for news-driven trading.

        ---

        ### What does it show?

        #### 🟢🔴 Sentiment Banner
        The first thing you see after fetching news is the overall **verdict** on recent
        news: Bullish (positive for the stock), Bearish (negative), or Neutral.
        The score ranges from -1.0 (extremely negative) to +1.0 (extremely positive).

        #### 🏢 Company Ecosystem
        Shows the company's **industry, competitors, and key suppliers**. This is useful
        because:
        - If a supplier has bad news (e.g. a chip shortage), it affects the company too
        - If a competitor reports bad earnings, it might be good for this company
        - Ecosystem awareness helps you understand second-order effects

        #### 📋 Summary
        A plain-English summary of the most important themes in recent news — so you
        can get the key points without reading every article.

        #### 📢 Financial Announcements
        Highlights specific events detected in the news: earnings reports, dividend
        announcements, product launches, mergers, regulatory filings, etc. These are
        the events that typically cause the biggest short-term price moves.

        #### 📰 Articles
        The individual news articles, each in a collapsible card. Click any article to
        see the source, publication date, and link to the full story. Announcements
        detected in each article are flagged automatically.

        ---

        ### How to use it
        1. Type a ticker (e.g. `NVDA`, `TSLA`, `AMZN`)
        2. Click **Fetch News**
        3. Check the **sentiment banner** first — is the news tone positive or negative?
        4. Read the **Financial Announcements** section — any earnings, guidance, or
           M&A news could be a catalyst for a price move
        5. Cross-reference with Tab 1: if news is Bullish AND the quant model says
           STRONG BUY, that's a stronger combined signal

        > 💡 **Tip:** Run this tab the night before or morning of any planned trade.
        > News sentiment often leads price movement by hours or days.
        """)

    nc1, nc2 = st.columns([3, 1])
    with nc1:
        news_ticker = st.text_input(
            "Stock Ticker", "NVDA", key="news_input",
            placeholder="Enter ticker, e.g. AAPL"
        )
    with nc2:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_news_btn = st.button("Fetch News", type="primary", key="fetch_news_button")

    if fetch_news_btn and news_ticker.strip():
        with st.spinner(f"Fetching news and ecosystem data for {news_ticker.upper()}..."):
            news_data = get_market_news(news_ticker.upper())
        st.session_state["news_data"] = news_data

    news_data = st.session_state.get("news_data")

    if news_data:
        if "Error" in news_data:
            st.warning(news_data["Error"])
        else:
            sent_score = news_data.get("Sentiment Score", 0)
            sent_label = news_data.get("Sentiment Label", "Neutral")

            # ── Sentiment banner ───────────────────────────────────────────
            if sent_label == "Bullish":
                st.success(f"News Sentiment: **BULLISH** — score: `{sent_score:+.3f}`")
            elif sent_label == "Bearish":
                st.error(f"News Sentiment: **BEARISH** — score: `{sent_score:+.3f}`")
            else:
                st.warning(f"News Sentiment: **NEUTRAL** — score: `{sent_score:+.3f}`")

            st.divider()

            # ── Company Ecosystem ──────────────────────────────────────────
            eco = news_data.get("Ecosystem", {})
            eco_c1, eco_c2 = st.columns(2)
            with eco_c1:
                st.metric("Company",  eco.get("company",  "N/A"))
                st.metric("Industry", eco.get("industry", "N/A"))
            with eco_c2:
                competitors = eco.get("competitors", [])
                suppliers   = eco.get("suppliers",   [])
                st.info(f"**Competitors**  \n{', '.join(competitors) if competitors else 'N/A'}")
                st.info(f"**Suppliers**  \n{', '.join(suppliers) if suppliers else 'N/A'}")

            st.divider()

            # ── Summary + Impact Analysis ──────────────────────────────────
            sum_c1, sum_c2 = st.columns([3, 2])
            with sum_c1:
                st.markdown("### Summary")
                st.write(news_data.get("Summary", ""))
            with sum_c2:
                st.markdown("### Financial Announcements")
                impact = news_data.get("Impact Analysis", {})
                if impact:
                    for k, v in impact.items():
                        st.markdown(f"**{k}:** {v}")
                else:
                    st.caption("No specific financial announcements detected.")

            st.divider()

            # ── Articles ───────────────────────────────────────────────────
            articles = news_data.get("Articles", [])
            st.markdown(f"### Articles  *({len(articles)} found)*")
            for article in articles:
                art_sent = article.get("Sentiment", sent_label)
                icon = "🟢" if art_sent == "Bullish" else "🔴" if art_sent == "Bearish" else "🟡"
                with st.expander(f"{icon} {article['Title']}", expanded=False):
                    ac1, ac2, ac3 = st.columns(3)
                    ac1.markdown(f"**Source:** {article['Source']}")
                    ac2.markdown(f"**Published:** {article['Published']}")
                    if article.get("Announcements"):
                        ac3.markdown(f"**Detected:** {', '.join(article['Announcements'])}")
                    st.markdown(f"[Read Full Article →]({article['Link']})")


# =============================================================================
# TAB 6 — SENTIMENT ENGINE
# =============================================================================
with tab6:

    st.subheader("Market Sentiment Dashboard")
    st.caption("Financial news sources + Reddit retail sentiment — powered by VADER NLP")

    with st.expander("🎓 New Here? What This Tab Does & Why It Matters", expanded=False):
        st.markdown("""
        ### What is this tab for?
        Markets are driven by two forces: **data** (fundamentals, covered in Tabs 1-4)
        and **emotion** (fear, greed, hype, panic — covered here).

        This tab measures the **emotional temperature of the market** from two very
        different sources: professional financial media and retail investor communities.
        Together they give you a 360° view of current market sentiment.

        ---

        ### 📡 Financial News Sentiment — What It Does

        Simultaneously reads **12 major financial news sources** in parallel:
        CNBC · MarketWatch · Yahoo Finance · Reuters · Bloomberg · CNN Business ·
        Google Finance · Barron's · Seeking Alpha · Morningstar · Investopedia · FT

        For each article, VADER AI assigns a sentiment score from -1.0 to +1.0.
        These scores are then aggregated to give you:

        **Overall Market Tone** — Is the professional financial press bullish or bearish
        about the market right now? This often leads market moves by 24-48 hours.

        **Per-Source Breakdown** — Do all sources agree? Or is Bloomberg bearish while
        CNBC is bullish? Disagreement between sources signals uncertainty.

        **Macro Theme Analysis** — Which big topics dominate the news?
        (Fed/Rates, Inflation, AI/Technology, Geopolitics, etc.)
        This tells you *why* the market is moving, not just *that* it's moving.

        **Top Headlines** — The most bullish and bearish individual articles — the
        specific stories driving the narrative today.

        **Full Article Feed** — Browse all articles with filters by source and sentiment.
        Every headline links directly to the original article.

        ---

        ### 🎯 Sentiment-Driven Stock Picks — The Killer Feature
        After fetching news sentiment, scroll down to **"Identify Top Stocks & Options
        from Sentiment"**. This feature:

        1. Identifies which macro themes are most bullish in today's news
           (e.g. "AI / Technology sentiment is very positive")
        2. Maps those themes to the stocks most likely to benefit
           (e.g. NVDA, MSFT, AMD, GOOGL for AI)
        3. Runs the full quant model on each candidate in parallel
        4. Combines the quant score + a sentiment alignment bonus to rank picks
        5. Returns the top N stocks with full analysis cards

        **This is where fundamental analysis meets news intelligence** — a combination
        used by the most sophisticated quantitative funds.

        ---

        ### 🐦 Reddit Retail Sentiment — What It Does
        Scans discussions across **r/stocks, r/investing, r/wallstreetbets, r/finance,
        r/economy** to measure what *retail investors* (everyday people) are talking about.

        This matters because retail sentiment can be a **contrarian indicator** — when
        Reddit is euphoric about a stock (e.g. GME in 2021), it's often near its peak.
        Conversely, when retail is panicking and selling, institutions are often buying.

        Shows: market sentiment score, ticker-level sentiment, most discussed stocks,
        trending themes, and sample posts from the community.

        ---

        ### How to use the two signals together
        | Scenario | What It Might Mean |
        |----------|-------------------|
        | News Bullish + Reddit Bullish | Strong momentum — broad agreement |
        | News Bullish + Reddit Bearish | Professionals optimistic, retail fearful — possible contrarian buy |
        | News Bearish + Reddit Bullish | Retail chasing, pros cautious — possible peak/caution signal |
        | News Bearish + Reddit Bearish | Broad fear — possible bottom forming or continued decline |

        > 💡 **Tip:** Run this tab first thing in the morning before making any trading
        > decisions. The overall market tone here should inform how aggressively you
        > act on signals from Tabs 1–4.
        """)

    sent_t1, sent_t2 = st.tabs(["📡 Financial News Sentiment", "🐦 Reddit Retail Sentiment"])

    # ================================================================
    # SECTION A — Financial News Sentiment
    # ================================================================
    with sent_t1:
        st.markdown(
            "**Sources:** CNBC · MarketWatch · Yahoo Finance · Reuters · Bloomberg · CNN Business · "
            "Google Finance · Barron's · Seeking Alpha · Morningstar · Investopedia · FT"
        )

        fn_c1, fn_c2, fn_c3 = st.columns([1, 1, 2])
        with fn_c1:
            days_back   = st.slider("News lookback (days)", 1, 14, 3, key="news_days")
        with fn_c2:
            max_per_src = st.slider("Max articles per source", 5, 30, 15, key="news_per_src")
        with fn_c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Fetch Financial News Sentiment", type="primary", key="fetch_fin_sent"):
                with st.spinner("Fetching from all news sources in parallel..."):
                    nd = get_market_news_sentiment(
                        days_back=days_back,
                        max_per_source=max_per_src,
                    )
                st.session_state["fin_sent_data"] = nd

        nd = st.session_state.get("fin_sent_data")

        if nd:
            ov_score = nd["overall_score"]
            ov_label = nd["overall_label"]
            ov_bias  = nd["overall_bias"]

            # ── Large sentiment banner ─────────────────────────────────────
            src_count = len(nd["sources_reached"])
            art_count = nd["articles_analysed"]
            if ov_label == "Bullish":
                st.success(
                    f"### 📈 Market Tone: BULLISH\n"
                    f"Score: **{ov_score:+.3f}** · {src_count} sources reached · {art_count} articles analysed"
                )
            elif ov_label == "Bearish":
                st.error(
                    f"### 📉 Market Tone: BEARISH\n"
                    f"Score: **{ov_score:+.3f}** · {src_count} sources reached · {art_count} articles analysed"
                )
            else:
                st.warning(
                    f"### ➡️ Market Tone: NEUTRAL\n"
                    f"Score: **{ov_score:+.3f}** · {src_count} sources reached · {art_count} articles analysed"
                )

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Overall Score",       f"{ov_score:+.3f}")
            sc2.metric("Sentiment Label",     ov_label)
            sc3.metric("Market Bias (words)", ov_bias)
            sc4.metric("Articles Analysed",   art_count)

            if nd.get("sources_failed"):
                st.caption(f"Sources unreachable: {', '.join(nd['sources_failed'])}")

            st.divider()

            # ── Detailed breakdowns in nested tabs ─────────────────────────
            ns_t1, ns_t2, ns_t3, ns_t4 = st.tabs([
                "🗞️ Per-Source Breakdown",
                "🏷️ Macro Themes",
                "📰 Top Headlines",
                "📚 Full Article Feed",
            ])

            with ns_t1:
                src_rows = [
                    {
                        "Source":    src,
                        "Articles":  v["article_count"],
                        "Avg Score": v["score"],
                        "Sentiment": v["label"],
                    }
                    for src, v in nd["per_source"].items()
                ]
                df_src = pd.DataFrame(src_rows).sort_values("Avg Score", ascending=False)
                src_c1, src_c2 = st.columns([1, 1])
                with src_c1:
                    st.dataframe(
                        df_src.style
                        .applymap(colour_sent_label, subset=["Sentiment"])
                        .format({"Avg Score": "{:+.3f}"}),
                        use_container_width=True,
                    )
                with src_c2:
                    bar_c = [
                        "#2e7d32" if s >= 0.05 else "#b71c1c" if s <= -0.05 else "#f9a825"
                        for s in df_src["Avg Score"]
                    ]
                    fig_src = go.Figure(go.Bar(
                        x=df_src["Avg Score"],
                        y=df_src["Source"],
                        orientation="h",
                        marker_color=bar_c,
                        text=df_src["Avg Score"].round(3),
                        textposition="outside",
                    ))
                    fig_src.add_vline(x=0.05, line_dash="dash", line_color="#2e7d32",
                                     annotation_text="Bullish")
                    fig_src.add_vline(x=-0.05, line_dash="dash", line_color="#b71c1c",
                                     annotation_text="Bearish")
                    fig_src.update_layout(
                        height=max(320, len(df_src) * 38),
                        xaxis_title="VADER Score",
                        **_plotly_defaults(),
                    )
                    st.plotly_chart(fig_src, use_container_width=True)

            with ns_t2:
                if nd["theme_breakdown"]:
                    df_themes = pd.DataFrame(nd["theme_breakdown"])
                    th_c1, th_c2 = st.columns([1, 1])
                    with th_c1:
                        st.dataframe(
                            df_themes.style
                            .applymap(colour_sent_label, subset=["label"])
                            .format({"avg_sentiment": "{:+.3f}"}),
                            use_container_width=True,
                        )
                    with th_c2:
                        top_themes = df_themes.head(8)
                        th_bar_c = [
                            "#2e7d32" if s >= 0.05 else "#b71c1c" if s <= -0.05 else "#f9a825"
                            for s in top_themes["avg_sentiment"]
                        ]
                        fig_th = go.Figure(go.Bar(
                            x=top_themes["avg_sentiment"],
                            y=top_themes["theme"],
                            orientation="h",
                            marker_color=th_bar_c,
                            text=top_themes["avg_sentiment"].round(3),
                            textposition="outside",
                        ))
                        fig_th.add_vline(x=0, line_color="rgba(255,255,255,0.3)")
                        fig_th.update_layout(
                            title="Theme Sentiment (top 8 by mentions)",
                            height=max(290, len(top_themes) * 38),
                            xaxis_title="Avg VADER Score",
                            **_plotly_defaults(),
                        )
                        st.plotly_chart(fig_th, use_container_width=True)
                else:
                    st.info("No macro themes detected in current articles.")

            with ns_t3:
                h_c1, h_c2 = st.columns(2)
                with h_c1:
                    st.markdown("### Most Bullish Headlines")
                    for h in nd["top_bullish_headlines"]:
                        st.markdown(
                            f"🟢 **[{h['title']}]({h['link']})**  \n"
                            f"`{h['source']}` — Score: `{h['score']:+.3f}`"
                        )
                        st.markdown("---")
                with h_c2:
                    st.markdown("### Most Bearish Headlines")
                    for h in nd["top_bearish_headlines"]:
                        st.markdown(
                            f"🔴 **[{h['title']}]({h['link']})**  \n"
                            f"`{h['source']}` — Score: `{h['score']:+.3f}`"
                        )
                        st.markdown("---")

            with ns_t4:
                art_src_filter = st.multiselect(
                    "Filter by source",
                    options=nd["sources_reached"],
                    default=nd["sources_reached"],
                    key="art_src_filter",
                )
                art_sent_filter = st.multiselect(
                    "Filter by sentiment",
                    ["Bullish", "Neutral", "Bearish"],
                    default=["Bullish", "Neutral", "Bearish"],
                    key="art_sent_filter",
                )
                for art in nd["all_articles"]:
                    if art["source"] not in art_src_filter:
                        continue
                    if art["sentiment_label"] not in art_sent_filter:
                        continue
                    icon = (
                        "🟢" if art["sentiment_label"] == "Bullish"
                        else "🔴" if art["sentiment_label"] == "Bearish"
                        else "🟡"
                    )
                    theme_str = ", ".join(art["themes"]) if art["themes"] else "General"
                    st.markdown(
                        f"{icon} **[{art['title']}]({art['link']})**  \n"
                        f"`{art['source']}` | {art['published']} | "
                        f"Score: `{art['sentiment_score']:+.3f}` | Themes: *{theme_str}*"
                    )
                    st.markdown("---")

            # ================================================================
            # SENTIMENT-DRIVEN STOCK & OPTIONS PICKS
            # ================================================================
            st.divider()
            st.markdown("## Sentiment-Driven Top Stock & Options Picks")
            st.caption(
                "Maps bullish news themes to candidate tickers, then validates each with the full "
                "quant model. Combined score = quant composite + sentiment alignment bonus."
            )

            pk_c1, pk_c2 = st.columns([1, 1])
            with pk_c1:
                pick_profile = st.selectbox(
                    "Risk Profile for Analysis",
                    PROFILE_OPTIONS,
                    index=PROFILE_OPTIONS.index(global_profile),
                    key="pick_profile",
                )
            with pk_c2:
                pick_top_n = st.number_input(
                    "Number of picks", min_value=3, max_value=10, value=5, key="pick_top_n"
                )

            if st.button(
                "Identify Top Stocks & Options from Sentiment",
                type="primary",
                key="run_picker",
            ):
                with st.spinner("Mapping themes → tickers → running quant model in parallel..."):
                    picker_result = identify_top_stocks(
                        nd,
                        run_quant_model,
                        risk_profile=pick_profile,
                        top_n=int(pick_top_n),
                    )
                st.session_state["picker_result"] = picker_result

            picker_result = st.session_state.get("picker_result")

            if picker_result:
                picks          = picker_result.get("picks", [])
                bullish_themes = picker_result.get("bullish_themes", [])
                p_label        = picker_result.get("overall_label", "")
                p_score        = picker_result.get("overall_score", 0)
                candidates_run = picker_result.get("candidates_run", 0)

                if picker_result.get("message"):
                    st.warning(picker_result["message"])
                elif not picks:
                    st.info(
                        "No qualifying picks found. Try a different risk profile "
                        "or refresh the sentiment data."
                    )
                else:
                    st.markdown("### Bullish Themes Driving These Picks")
                    theme_cols = st.columns(min(len(bullish_themes[:4]), 4))
                    for i, (theme, weight, sent) in enumerate(bullish_themes[:4]):
                        theme_cols[i].metric(theme, f"{sent:+.3f}", f"Weight {weight:.3f}")

                    st.caption(
                        f"Overall news: **{p_label}** ({p_score:+.3f}) · "
                        f"Candidates evaluated: {candidates_run}"
                    )
                    st.divider()

                    for rank, pick in enumerate(picks, 1):
                        ticker   = pick["ticker"]
                        intent   = pick["intent"]
                        icon     = INTENT_ICONS.get(intent, "⬜")
                        conf     = pick["confidence"]
                        combined = pick["combined_score"]
                        quant    = pick["quant_score"]
                        bonus    = pick["sentiment_bonus"]
                        bg, fg   = INTENT_COLORS.get(intent, ("#444", "white"))

                        with st.expander(
                            f"#{rank}  {icon}  {ticker}  |  {intent}  |  "
                            f"Score: {combined:.2f}  (Quant: {quant:.2f} + Sentiment: {bonus:+.3f})",
                            expanded=(rank == 1),
                        ):
                            # Intent badge
                            st.markdown(
                                f'<span style="display:inline-block;background:{bg};color:{fg};'
                                f'padding:6px 18px;border-radius:20px;font-weight:700;">'
                                f'{icon} {ticker} — {intent}</span>',
                                unsafe_allow_html=True,
                            )
                            st.markdown("")

                            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                            mc1.metric("Confidence",    f"{conf}%")
                            mc2.metric("Regime",        pick["regime"])
                            mc3.metric("Ann. Vol",      f"{pick['volatility'] * 100:.1f}%")
                            mc4.metric("Position Size", f"{pick['position_size']}%")
                            mc5.metric("MC 1Y Proj.",   f"${pick['mc_projection']:,.2f}")

                            rf_flag = pick.get("risk_flag", "")
                            if rf_flag:
                                st.warning(f"⚠️ **Risk Flag:** {rf_flag}")

                            st.info(f"**Options Strategy:** `{pick['options_strategy']}`")

                            # Driving themes
                            st.markdown("**Driving Themes:**")
                            for ta in pick["theme_alignment"]:
                                badge = "🟢" if ta["sentiment"] > 0.05 else "🟡"
                                st.markdown(
                                    f"  {badge} **{ta['theme']}** — "
                                    f"sentiment `{ta['sentiment']:+.3f}`, "
                                    f"theme weight `{ta['weight']:.4f}`"
                                )

                            # Factor scores
                            fs = pick.get("factor_scores", {})
                            if fs:
                                st.markdown("**Factor Score Breakdown:**")
                                fs_cols = st.columns(6)
                                factor_map = [
                                    ("Growth",        "growth"),
                                    ("Profitability",  "profitability"),
                                    ("Efficiency",     "efficiency"),
                                    ("Leverage",       "leverage"),
                                    ("ROE",            "roe"),
                                    ("Valuation",      "valuation"),
                                ]
                                for col, (label, key) in zip(fs_cols, factor_map):
                                    col.metric(label, f"{fs.get(key, 0):+.2f}")

                            # Full reasoning
                            if pick.get("reasoning"):
                                with st.expander("Full Qualitative & Quantitative Reasoning"):
                                    st.text(pick["reasoning"])

                            if pick.get("timing"):
                                st.markdown(f"**Timing:** {pick['timing']}")

    # ================================================================
    # SECTION B — Reddit Retail Sentiment
    # ================================================================
    with sent_t2:
        st.markdown(
            "**Subreddits:** r/stocks · r/investing · r/wallstreetbets · r/finance · r/economy"
        )

        if st.button("Refresh Reddit Sentiment", key="refresh_reddit"):
            st.cache_data.clear()

        data = load_reddit_sentiment()

        reddit_score = data.get("Market Sentiment Score", 0)
        if reddit_score > 0.05:
            st.success(f"### 📈 Reddit Sentiment: BULLISH ({reddit_score:+.3f})")
        elif reddit_score < -0.05:
            st.error(f"### 📉 Reddit Sentiment: BEARISH ({reddit_score:+.3f})")
        else:
            st.warning(f"### ➡️ Reddit Sentiment: NEUTRAL ({reddit_score:+.3f})")

        st.divider()

        ticker_table = data.get("Ticker Sentiment Table", [])
        if ticker_table:
            st.markdown("### Ticker Sentiment Table")
            df_r = pd.DataFrame(ticker_table)
            df_r.columns = ["Ticker", "Mentions", "Sentiment Score", "Sentiment"]

            def _col_reddit_sent(val):
                if val == "bullish":
                    return "color: #2e7d32"
                if val == "bearish":
                    return "color: #b71c1c"
                return "color: gray"

            st.dataframe(
                df_r.style.applymap(_col_reddit_sent, subset=["Sentiment"]),
                use_container_width=True,
            )
        else:
            st.info("No ticker sentiment detected.")

        st.divider()

        r_col1, r_col2 = st.columns(2)

        with r_col1:
            st.markdown("### Most Discussed Tickers")
            top_tickers = data.get("Top Tickers", [])
            if top_tickers:
                df_tt = pd.DataFrame(top_tickers, columns=["Ticker", "Mentions"])
                fig_tt = px.bar(
                    df_tt, x="Mentions", y="Ticker", orientation="h",
                    color="Mentions", color_continuous_scale="Blues", text="Mentions",
                )
                fig_tt.update_layout(
                    height=max(260, len(df_tt) * 30),
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)",
                )
                st.plotly_chart(fig_tt, use_container_width=True)
            else:
                st.info("No ticker discussion detected.")

        with r_col2:
            st.markdown("### Trending Market Themes")
            top_keywords = data.get("Top Keywords", [])
            if top_keywords:
                df_kw = pd.DataFrame(top_keywords, columns=["Keyword", "Mentions"])
                fig_kw = px.bar(
                    df_kw, x="Mentions", y="Keyword", orientation="h",
                    color="Mentions", color_continuous_scale="Purples", text="Mentions",
                )
                fig_kw.update_layout(
                    height=max(260, len(df_kw) * 30),
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)",
                )
                st.plotly_chart(fig_kw, use_container_width=True)
            else:
                st.info("No market themes detected.")

        st.divider()

        st.markdown("### Sample Market Posts")
        for post in data.get("Sample Posts", []):
            with st.expander(f"📝 {post['title']}", expanded=False):
                p1, p2, p3 = st.columns(3)
                p1.markdown(
                    f"**Tickers:** {', '.join(post['tickers']) if post['tickers'] else 'None'}"
                )
                p2.markdown(
                    f"**Keywords:** {', '.join(post['keywords']) if post['keywords'] else 'None'}"
                )
                p3.markdown(f"**Sentiment:** {post['label']} (`{post['sentiment']}`)")
