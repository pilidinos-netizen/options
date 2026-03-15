# Intelligent Investment Research Platform — Architecture & Developer Reference

> Version: 2.0 | Last updated: 2026-03-15
> Stack: Python 3.13 · Streamlit · Plotly · yfinance · Polygon.io · VADER · feedparser · ThreadPoolExecutor

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Data Flow Diagram](#3-data-flow-diagram)
4. [Layer-by-Layer Reference](#4-layer-by-layer-reference)
   - [UI Layer](#41-ui-layer--apppy)
   - [Controller Layer](#42-controller-layer--mainpy)
   - [Engine Layer](#43-engine-layer--engines)
   - [Data Layer](#44-data-layer--data)
   - [Models Layer](#45-models-layer--models)
   - [Storage Layer](#46-storage-layer--storage)
   - [Config Layer](#47-config-layer--config)
5. [Full Quant Pipeline (main.py walkthrough)](#5-full-quant-pipeline)
6. [Risk Profile Impact Matrix](#6-risk-profile-impact-matrix)
7. [Data Source Fallback Chains](#7-data-source-fallback-chains)
   - [Options Data Fallback](#71-options-data-fallback)
   - [Fundamentals Fallback](#72-fundamentals-fallback)
   - [Market Data Fallback](#73-market-data-fallback)
8. [Market Sentiment Architecture](#8-market-sentiment-architecture)
9. [UI Architecture](#9-ui-architecture)
   - [Global Layout](#91-global-layout)
   - [Tab Structure](#92-tab-structure)
   - [Session State](#93-session-state)
10. [Scoring & Threshold Reference](#10-scoring--threshold-reference)
11. [Concurrency Model](#11-concurrency-model)
12. [Deployment & Secrets Management](#12-deployment--secrets-management)
13. [File Reference Table](#13-file-reference-table)
14. [Key Dependencies](#14-key-dependencies)
15. [Adding New Features](#15-adding-new-features)
16. [Changelog](#16-changelog)

---

## 1. System Overview

This platform is a **modular quantitative research system** for options and equity analysis. It combines:

- **Fundamental factor scoring** across 6 weighted metrics
- **Risk-profile-aware signal classification** (5-level intent: STRONG BUY → SELL)
- **Options strategy selection** with 20 distinct strategy-profile combinations
- **Multi-source data resilience** — Polygon.io → yfinance → local cache fallback for options, fundamentals, and market price data
- **Broad market scanning** across S&P 100, NASDAQ 100, and sector universes
- **Financial news sentiment** aggregated from 12 professional sources
- **Reddit retail sentiment** across 5 subreddits
- **Sentiment-driven stock picking** mapping bullish news themes to quant-validated candidates
- **Monte Carlo price projection** via Geometric Brownian Motion
- **Interactive Plotly charts** throughout (hover, zoom, download)
- **Streamlit Cloud deployment** with secrets management

---

## 2. High-Level Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         STREAMLIT UI  (app.py)                               ║
║                                                                              ║
║  Sidebar: global_profile, navigation guide, platform description             ║
║  Header:  SVG logo banner with pill badges                                   ║
║                                                                              ║
║  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐ ┌────────────────────┐ ║
║  │ Tab 1       │ │ Tab 2        │ │ Tab 3          │ │ Tab 4              │ ║
║  │ 📊 Stock    │ │ 🌐 Market    │ │ 📈 Performance │ │ 🎯 Options         │ ║
║  │ Analysis    │ │ Scan         │ │                │ │ Strategy           │ ║
║  └──────┬──────┘ └──────┬───────┘ └───────┬────────┘ └────────┬───────────┘ ║
║         │               │                 │                    │             ║
║  ┌──────┴──────┐ ┌──────┴───────┐         │                    │             ║
║  │ Tab 5       │ │ Tab 6        │         │                    │             ║
║  │ 📰 Market   │ │ 💬 Sentiment │         │                    │             ║
║  │ News        │ │ Engine       │         │                    │             ║
║  └─────────────┘ └──────────────┘         │                    │             ║
╚══════════════════════════════════════════╪════════════════════╪════════════╝
                                           │                    │
                    ┌──────────────────────▼──────────────────────┐
                    │           CONTROLLER  (main.py)              │
                    │         run_quant_model(ticker, profile)     │
                    └────────────────────┬────────────────────────┘
                                         │
         ┌───────────────────────────────┼────────────────────────────┐
         │                               │                            │
╔════════▼═══════╗           ╔═══════════▼══════════╗    ╔═══════════▼═══════╗
║  ENGINE LAYER  ║           ║    DATA LAYER        ║    ║   MODELS LAYER    ║
║                ║           ║                      ║    ║                   ║
║ factor_engine  ║◄──────────║ fundamentals.py      ║    ║ monte_carlo.py    ║
║ intent_classif ║           ║   ├── yfinance       ║    ║ backtester.py     ║
║ regime_engine  ║◄──────────║   └── Polygon.io ───►║    ╚═══════════════════╝
║ options_select ║           ║ market_data.py       ║
║ position_sizer ║◄──────────║   ├── yfinance       ║    ╔═══════════════════╗
║ timing_engine  ║           ║   └── Polygon.io ───►║    ║  STORAGE LAYER    ║
║ volatility_eng ║           ║ options_chain.py     ║    ║                   ║
║ risk_engine    ║           ║   ├── Polygon.io     ║    ║ cache.py (pickle) ║
╚════════════════╝           ║   ├── yfinance       ║    ║ database.py (SQL) ║
                             ║   └── local cache ───╫────║                   ║
                             ╚══════════════════════╝    ╚═══════════════════╝
         │
╔════════▼═══════════════════════════════════════════════════════════════════╗
║                         SCAN / SENTIMENT ENGINES                           ║
║                                                                            ║
║  market_scanner.py          market_news_sentiment_engine.py               ║
║  market_screener.py         social_sentiment_engine.py                    ║
║  news_engine.py             sentiment_stock_picker.py                     ║
║  performance_engine.py      options_opportunity_engine.py                 ║
║  options_contract_engine.py options_payoff_engine.py                      ║
║  greeks_optimizer.py                                                       ║
╚════════════════════════════════════════════════════════════════════════════╝
         │
╔════════▼════════════════════════════════════════════════════════════════════╗
║                            CONFIG LAYER                                     ║
║                                                                             ║
║  settings.py         market_universe.py      api_keys.py                   ║
║  RISK_PROFILES       SP100, NASDAQ100         POLYGON_API_KEY              ║
║  FACTOR_WEIGHTS      SECTORS, BROAD_MARKET    (reads from st.secrets /     ║
║                                               env vars — never hardcoded)  ║
╚═════════════════════════════════════════════════════════════════════════════╝
```

---

## 3. Data Flow Diagram

```
  User Input
  (ticker + risk_profile)
         │
         ▼
┌────────────────────┐
│  get_fundamentals  │──► 1. yfinance .info (primary)
└────────┬───────────┘     2. Polygon /v3/reference/tickers (fallback — name, sector, marketCap)
         │                 3. Polygon /vX/reference/financials (fallback — revenue, margins, ratios)
         │                 Returns same keys regardless of source
         ▼
┌────────────────────┐
│  compute_scores    │──► Factor scores dict
└────────┬───────────┘     {growth, profitability, efficiency,
         │                  leverage, roe, valuation, total}
         │                  total ∈ [-1.60, +3.45]
         ▼
┌──────────────────────┐
│ calculate_volatility │──► annualised vol (float)
└────────┬─────────────┘     get_price_history → 1. yfinance, 2. Polygon /v2/aggs
         ▼
┌────────────────────────────────────┐
│  classify_intent                   │──► (intent: str, confidence: int)
│  (score, vol, risk_profile)        │    profile-specific thresholds
└────────┬───────────────────────────┘
         ▼
┌────────────────────┐
│  detect_regime     │──► "Expansion" | "Late Cycle" | "Neutral" | "Contraction"
└────────┬───────────┘
         ▼
┌────────────────────────────────────┐
│  select_options_strategy           │──► strategy string (20 distinct strategies)
│  (intent, risk_profile)            │
└────────┬───────────────────────────┘
         ▼
┌────────────────────────────────────┐
│  position_size(intent, profile)    │──► allocation (float, 0–0.45)
└────────┬───────────────────────────┘
         ▼
┌────────────────────────────────────┐
│  risk_management(vol, alloc, prof) │──► (adj_allocation, risk_flag)
└────────┬───────────────────────────┘     profile-specific vol thresholds
         ▼
┌────────────────────┐
│  get_price_history │──► current_price (yfinance → Polygon fallback)
└────────┬───────────┘
         ▼
┌────────────────────────────────────┐
│  simulate_price                    │──► MC projection (mean of 1000 GBM paths)
│  (S0, mu=0.10, sigma=vol, T=1)     │
└────────┬───────────────────────────┘
         ▼
┌────────────────────────────────────┐
│  build_reasoning                   │──► multi-line qualitative report string
│  (ticker, info, scores, intent,    │    (quantitative metrics + factor
│   volatility, confidence)          │     commentary + signal verdict)
└────────┬───────────────────────────┘
         ▼
     Result Dict
  ┌──────────────────────────────────────┐
  │ Ticker, Intent, Confidence, Regime   │
  │ Volatility, Options Strategy         │
  │ Position Size (%), Risk Flag         │
  │ Monte Carlo Projection (1Y)          │
  │ Timing Plan, Factor Scores           │
  │ Reasoning (full qualitative report)  │
  └──────────────────────────────────────┘
```

---

## 4. Layer-by-Layer Reference

### 4.1 UI Layer — `app.py`

The Streamlit frontend. Six tabs with shared global controls and a persistent sidebar.

#### Global Layout

```
Page
├── Sidebar
│   ├── SVG logo mark (36px) + "IIRP / Quant Research" text
│   ├── global_profile selectbox (shared default for all tabs)
│   ├── Quick Navigation table
│   └── About caption
├── Header Banner (SVG logo + gradient text + pill badges)
└── Main tabs (st.tabs)
```

#### Tab Overview

| Tab | Name | Primary Engine(s) Called | Inner Tabs |
|-----|------|--------------------------|------------|
| 1 | 📊 Stock Analysis | `run_quant_model` | None |
| 2 | 🌐 Market Scan | `scan_market`, `pre_screen` | Signal & Risk · Fundamentals · Momentum · Factor Heatmap · Sector Breakdown |
| 3 | 📈 Performance | `compute_performance_metrics` | Single Stock · Compare Universe |
| 4 | 🎯 Options Strategy | `rank_option_opportunities`, `select_leaps_contract` | Top Opportunities · LEAPS Generator |
| 5 | 📰 Market News | `get_market_news` | None |
| 6 | 💬 Sentiment Engine | `get_market_news_sentiment`, `identify_top_stocks`, `run_market_sentiment_engine` | Financial News Sentiment · Reddit Retail Sentiment |

#### Novice Guidance

Every tab contains a **"🎓 New Here? What This Tab Does & Why It Matters"** expander (collapsed by default) with plain-English explanations covering:
- What the tab is for and its real-world analogy
- Every metric and term explained without jargon
- Step-by-step usage instructions
- Practical tips for combining tabs

#### Shared Helpers (defined in `app.py`)

```
_resolve_tickers(universe_choice, selected_sectors, custom_input) -> list[str]
    Converts universe selector state to a flat ticker list.
    Supports: S&P 100, NASDAQ 100, Broad Market, Sector, Custom.

_universe_controls(prefix, default_top_n, show_top_n) -> (choice, sectors, custom, top_n, min_mcap, min_vol)
    Renders universe selector widgets (unique keys via prefix).
    Used in Tab 2, Tab 3 (compare mode), Tab 4.

_run_prescreen(raw_tickers, top_n, min_mcap, min_vol, sectors) -> (run_tickers, summary, failed)
    Thin wrapper around pre_screen(); returns sorted list ready for full model.

_intent_banner(ticker, intent)
    Renders full-width coloured HTML banner (green → STRONG BUY, red → SELL).

colour_intent / colour_value / colour_return / colour_rsi / colour_sent_label
    Pandas Styler applymap functions used consistently across all dataframe displays.

_plotly_defaults() -> dict
    Returns shared Plotly layout kwargs (transparent background, white font, margins).
```

#### Charts

All charts use **Plotly** (interactive hover, zoom, pan, PNG download). Matplotlib has been fully removed.

| Chart | Tab | Type |
|-------|-----|------|
| Signal Distribution donut | 2 | `go.Pie` |
| Composite Score by Ticker | 2 | `go.Bar` (horizontal) |
| Sector Avg Score | 2 | `px.bar` |
| Factor Score breakdown | 1 | `go.Bar` (horizontal) |
| Sharpe Ratio comparison | 3 | `go.Bar` (horizontal) |
| LEAPS P&L at expiration | 4 | `go.Scatter` (area fill) |
| Per-source sentiment | 6 | `go.Bar` (horizontal) |
| Macro theme sentiment | 6 | `go.Bar` (horizontal) |
| Most discussed tickers | 6 | `px.bar` |
| Trending keywords | 6 | `px.bar` |

---

### 4.2 Controller Layer — `main.py`

```python
run_quant_model(ticker: str, risk_profile: str) -> dict
```

Orchestrates the full 12-stage pipeline in sequential order. The only entry point used by all UI tabs.

**Stage sequence:**
```
1  get_fundamentals(ticker)                       → info dict (yfinance → Polygon fallback)
2  compute_scores(info)                           → scores dict
3  calculate_volatility(ticker)                   → float (uses get_price_history internally)
4  classify_intent(score, vol, profile)           → (intent, confidence)
5  detect_regime(score)                           → str
6  select_options_strategy(intent, profile)       → str
7  position_size(intent, profile)                 → float
8  risk_management(vol, allocation, profile)      → (float, str)
9  get_price_history(ticker)                      → DataFrame → current_price (yfinance → Polygon)
10 simulate_price(S0, mu, sigma, T, sims=1000)   → float
11 timing_plan()                                  → dict
12 build_reasoning(ticker, info, scores, ...)     → str
```

---

### 4.3 Engine Layer — `engines/`

#### `factor_engine.py`
**Purpose:** 6-factor fundamental scoring.

```
compute_scores(info: dict) -> dict
```

| Factor | Metric | Score Range | Exceptional Threshold |
|--------|--------|-------------|----------------------|
| Growth | `revenueGrowth` | −2 to +5 | >30% → +5 |
| Profitability | `grossMargins` | −1 to +4 | >60% → +4 |
| Efficiency | `operatingMargins` | −1 to +3 | >30% → +3 |
| Leverage | `debtToEquity` | −2 to +2 | D/E < 50 → +2 |
| ROE | `returnOnEquity` | −1 to +3 | ROE > 25% → +3 |
| Valuation | `forwardPE` | −3 to +2 | P/E < 15 → +2; >45 → −3 |

**Composite formula:**
```
total = growth×0.25 + profitability×0.20 + efficiency×0.20
      + leverage×0.15 + roe×0.10 + valuation×0.10
Max ≈ +3.45   |   Min ≈ −1.60
```

```
build_reasoning(ticker, info, scores, intent, volatility, confidence) -> str
```
Generates a structured multi-section text report with:
- Quantitative metrics table (all 6 raw values + factor scores)
- Per-factor qualitative commentary
- Volatility context
- Signal verdict paragraph

---

#### `intent_classifier.py`
**Purpose:** Maps composite score + volatility to a 5-level intent signal.

```
classify_intent(weighted_score, volatility, risk_profile) -> (intent, confidence)
```

| Profile | STRONG BUY score ≥ | vol < | BUY score ≥ | vol < |
|---------|--------------------|-------|-------------|-------|
| Conservative | 3.2 | 0.20 | 2.2 | 0.30 |
| Balanced | 3.0 | 0.30 | 1.8 | 0.50 |
| Aggressive | 2.5 | 0.45 | 1.5 | 0.65 |
| Speculator | 2.0 | 0.60 | 1.2 | 0.80 |

HOLD ≥ 0.8 | REDUCE ≥ 0.0 | SELL < 0.0 (all profiles)

---

#### `risk_engine.py`
**Purpose:** Adjusts position allocation based on volatility (profile-calibrated).

```
risk_management(volatility, allocation, risk_profile) -> (adjusted_allocation, risk_flag)
```

| Profile | Moderate flag (×0.75) | High flag (×0.50) |
|---------|-----------------------|-------------------|
| Conservative | vol > 25% | vol > 40% |
| Balanced | vol > 40% | vol > 60% |
| Aggressive | vol > 55% | vol > 75% |
| Speculator | vol > 70% | vol > 90% |

---

#### `options_selector.py`
**Purpose:** 20-strategy matrix (4 profiles × 5 intents).

| Intent | Conservative | Balanced | Aggressive | Speculator |
|--------|-------------|----------|------------|------------|
| STRONG BUY | Sell Cash-Secured Put (ATM, 30–45 DTE) | Bull Call Spread (ATM/OTM, 45–60 DTE) | Buy 12M ATM LEAPS Call | Buy OTM Call (5–10% OTM) + LEAPS kicker |
| BUY | Bull Put Spread (30–45 DTE) | Buy ATM Call or Bull Call Spread | Buy ATM Call (30–60 DTE) | Buy OTM Call (2–5% OTM, 21–45 DTE) |
| HOLD | Covered Call (OTM, 30 DTE) | Covered Call (slight OTM, 30–45 DTE) | Sell ATM Straddle or Covered Call | Short Strangle (collect premium) |
| REDUCE | Buy Protective Put (ATM) | Bear Put Spread | Buy OTM Put or Bear Call Spread | Buy OTM Put (5–10% OTM) |
| SELL | Sell Covered Call (deep ITM) / Exit | Buy Protective Put or close long | Buy ATM Put / Ratio Put Spread | Buy Deep OTM Put / Bear Put Spread |

---

#### `market_scanner.py`
**Purpose:** Parallel full-model scan across a ticker list.

```
scan_market(tickers, run_model, profile, max_workers=8, progress_cb=None) -> list[dict]
```

Each row contains: Ticker, Name, Sector, Intent, Confidence, Composite Score, Regime, Rev Growth, Gross/Op Margin, Fwd P/E, ROE, Market Cap, Ann. Vol, Risk Flag, Position Size, 1M/3M/6M Returns, 52W Range %, RSI-14, Options Strategy, F:Growth/Profitability/Efficiency/Leverage/ROE/Valuation.

**RSI-14 calculation:** Inline, from 3-month price history. Cutoffs: >70 overbought, <30 oversold.

---

#### `market_screener.py`
**Purpose:** Fast parallel pre-screener (one yfinance call per ticker).

```
pre_screen(tickers, min_market_cap_b=1.0, min_avg_volume=500_000,
           sectors=None, max_workers=12) -> (results, failed)
```

Applies three filters: market cap, average daily volume, sector. Returns sorted by market cap descending.

---

#### `market_news_sentiment_engine.py`
**Purpose:** Broad financial news sentiment across 12 sources.

```
get_market_news_sentiment(days_back=3, max_per_source=15, max_workers=10) -> dict
```

**Sources:**
```
CNBC · MarketWatch · Yahoo Finance · Reuters Business · Bloomberg
CNN Business · Google Finance · Barron's · Seeking Alpha
Morningstar · Investopedia · FT Markets
```

**Macro themes detected (10):**
```
Fed / Rates · Inflation · Earnings Season · Recession / Growth
Geopolitics · AI / Technology · Energy · Crypto / Digital Assets
Labor Market · Housing / Real Estate
```

**Output keys:**
```
overall_score         float   VADER compound average across all articles
overall_label         str     "Bullish" / "Neutral" / "Bearish"
overall_bias          str     Word-frequency signal (bullish/bearish keywords)
articles_analysed     int
sources_reached       list
sources_failed        list
per_source            dict    {source: {score, label, article_count, top_headlines}}
theme_breakdown       list    [{theme, mentions, avg_sentiment, label}]
top_bullish_headlines list    Top 5 most positive articles
top_bearish_headlines list    Top 5 most negative articles
all_articles          list    Full feed sorted newest first
```

---

#### `sentiment_stock_picker.py`
**Purpose:** Maps bullish news themes to stock candidates, validates with full quant model.

```
identify_top_stocks(sentiment_data, run_model, risk_profile="Balanced",
                    top_n=5, max_candidates=25, max_workers=8) -> dict
```

**Pipeline:**
```
1. Score themes:  weight = avg_sentiment × (1 + 0.05 × mentions)
2. Build pool:    collect tickers from top 6 bullish themes via THEME_TICKERS
3. Run model:     parallel quant model on top 25 candidates
4. Compute score: combined = quant_score + sentiment_bonus
   Bonus rules:
     Bullish market + BUY/STRONG BUY intent → +0.4 × overall_score
     Bullish market + HOLD intent           → +0.1 × overall_score
     Bearish market + BUY/STRONG BUY intent → −0.2 × |overall_score|  (penalty)
     Bearish market + REDUCE/SELL intent    → +0.2 × |overall_score|
5. Rank:          sort by intent tier, then combined_score descending
6. Return top N
```

**THEME_TICKERS mapping (excerpt):**

| Theme | Tickers |
|-------|---------|
| AI / Technology | NVDA, MSFT, GOOGL, META, AMD, AVGO, PLTR, CRWD, NET, PANW, ARM, MRVL, SMCI, TSM, AMAT |
| Fed / Rates | JPM, BAC, GS, MS, WFC, C, BLK, SCHW, V, MA, AXP |
| Inflation | XOM, CVX, COP, OXY, SLB, EOG, GLD, FCX, NEM, MPC, VLO |
| Energy | XOM, CVX, COP, OXY, SLB, EOG, MPC, VLO, PSX, HAL |
| Geopolitics | LMT, RTX, GD, NOC, BA, HII, TDG |
| Earnings Season | AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, V, MA, HD |
| Housing | DHI, LEN, TOL, PHM, NVR, LOW, HD |
| Crypto | COIN, MSTR, RIOT, MARA, CLSK |

---

#### `options_contract_engine.py`
**Purpose:** LEAPS contract selector (≥10 months to expiry).

```
select_leaps_contract(ticker, min_months=10) -> {Expiration, Strike, Premium, ...Greeks}
```

Uses `get_expirations()` + `get_options_by_expiry()` → finds ATM call at nearest qualifying expiry.

---

#### `options_opportunity_engine.py`
**Purpose:** Rank options opportunities across a universe.

```
rank_option_opportunities(tickers, run_model, profile) -> list[dict]  # top 10
```

**Opportunity Score formula:**
```
score = confidence × 0.5 + (volatility × 100) × 0.3 + (avg_volume / 1_000_000) × 0.2
```

---

#### `performance_engine.py`
**Purpose:** Historical performance statistics.

```
compute_performance_metrics(ticker) -> {Total Return (%), Annual Return (%),
                                        Annual Volatility (%), Sharpe Ratio, Max Drawdown (%)}
```

---

### 4.4 Data Layer — `data/`

#### `fundamentals.py` — Two-Source Fallback *(updated v2.0)*

```
get_fundamentals(ticker: str) -> dict
```

**Fallback chain:**
```
┌─────────────────────────┐  < 10 keys  ┌──────────────────────────────────────┐
│  yfinance               │────────────►│  Polygon.io (3 API calls)            │
│  yf.Ticker(t).info      │  or error   │                                      │
│                         │             │  1. /v3/reference/tickers/{ticker}   │
│  Returns 100+ fields    │             │     → name, sector, marketCap        │
│  in one call            │             │                                      │
└─────────────────────────┘             │  2. /vX/reference/financials         │
                                        │     → revenue growth, margins,       │
                                        │       ROE, debt/equity               │
                                        │                                      │
                                        │  3. Keys mapped to match yfinance    │
                                        │     field names exactly — zero       │
                                        │     downstream changes required      │
                                        └──────────────────────────────────────┘
```

**Fields returned (regardless of source):**

| Field | yfinance key | Polygon source |
|-------|-------------|----------------|
| Revenue growth | `revenueGrowth` | Calculated from 2 years of `/vX/reference/financials` |
| Gross margin | `grossMargins` | `gross_profit / revenues` |
| Operating margin | `operatingMargins` | `operating_income_loss / revenues` |
| Return on assets | `returnOnAssets` | `net_income_loss / assets` |
| Return on equity | `returnOnEquity` | `net_income_loss / equity` |
| Debt/equity | `debtToEquity` | `long_term_debt / equity × 100` |
| Company name | `shortName` | `name` from ticker details |
| Sector | `sector` | `sic_description` from ticker details |
| Market cap | `marketCap` | `market_cap` from ticker details |

Result dict includes `_source` key: `"yfinance"`, `"polygon"`, or `"none"`.

---

#### `market_data.py` — Two-Source Fallback *(updated v2.0)*

```
get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame
```

**Fallback chain:**
```
┌─────────────────────────┐   empty    ┌──────────────────────────────────────┐
│  yfinance               │───────────►│  Polygon.io                          │
│  yf.download(ticker,    │  or error  │  GET /v2/aggs/ticker/{ticker}/       │
│    period, auto_adjust) │            │    range/1/day/{start}/{end}         │
│                         │            │                                      │
│  Returns multi-level    │            │  Parameters:                         │
│  columns for single     │            │    adjusted=true, sort=asc           │
│  ticker — normalised    │            │    limit=50000                       │
│  to single-level        │            │                                      │
└─────────────────────────┘            │  Returns same DataFrame schema:      │
                                       │  Date index, Open/High/Low/          │
                                       │  Close/Volume columns                │
                                       └──────────────────────────────────────┘
```

**Period → days mapping:**
```
"1d"→1  "5d"→5  "1mo"→30  "3mo"→90  "6mo"→180  "1y"→365  "2y"→730  "5y"→1825
```

Raises `ValueError` only if **both** sources fail.

---

#### `options_chain.py` — Three-Source Fallback

```
get_options_chain(ticker)           → (calls_df, puts_df)  nearest expiry
get_options_by_expiry(ticker, exp)  → (calls_df, puts_df)  specific expiry
get_expirations(ticker)             → list[str]             sorted date strings
```

**Fallback chain:**
```
┌────────────────────┐    fail    ┌────────────────────┐    fail    ┌──────────────────┐
│  Polygon.io        │──────────►│  yfinance          │──────────►│  Local cache     │
│  /v3/snapshot/     │            │  stock.option_chain│            │  (pickle, 4h TTL)│
│  options/{ticker}  │            │                    │            │                  │
│  + Greeks, IV      │            │  + Greeks via yf   │            │  Stale but usable│
└────────────────────┘            └────────────────────┘            └──────────────────┘
         │                                 │
         └─── On success: save_options_cache() to keep cache warm ──────────────┘
```

**Normalised output columns:**

| Column | Type | Source |
|--------|------|--------|
| contractSymbol | str | Both |
| strike | float | Both |
| expiration | str (YYYY-MM-DD) | Both |
| contractType | str (call/put) | Polygon only |
| bid / ask / lastPrice | float | Both |
| volume / openInterest | int | Both |
| impliedVolatility | float | Both |
| delta / gamma / theta / vega | float | Polygon only |

---

### 4.5 Models Layer — `models/`

#### `monte_carlo.py`
```
simulate_price(S0, mu=0.10, sigma=0.30, T=1, sims=1000) -> float
```
GBM formula: `S_T = S0 × exp((mu − 0.5×sigma²)×T + sigma×√T×Z)` where Z ~ N(0,1)
Returns the **mean** of all simulation endpoints.

#### `backtester.py`
```
backtest(ticker) -> Series
```
MA50 crossing strategy: Long when Close > MA50, else flat. Returns cumulative return series.

---

### 4.6 Storage Layer — `storage/`

#### `cache.py`
```
save_options_cache(ticker, calls, puts, expiry=None)
load_options_cache(ticker, expiry=None, max_age_hours=4) -> (calls, puts) | (None, None)
```

Cache file structure:
```
storage/
  options_cache/
    {TICKER}_options_nearest.pkl   ← nearest expiry (expiry=None)
    {TICKER}_options_2025-06-20.pkl ← specific expiry
```

Each `.pkl` is a dict: `{"calls": DataFrame, "puts": DataFrame, "timestamp": float}`

#### `database.py`
```
init_db() -> sqlite3.Connection   # quant.db / signals.db
```
Schema: `signals(ticker TEXT, intent TEXT, confidence REAL)`

---

### 4.7 Config Layer — `config/`

#### `settings.py`
```python
RISK_PROFILES = {"Conservative": 0.05, "Balanced": 0.10, "Aggressive": 0.20, "Speculator": 0.30}
FACTOR_WEIGHTS = {"growth": 0.25, "profitability": 0.20, "efficiency": 0.20,
                  "leverage": 0.15, "roe": 0.10, "valuation": 0.10}  # sum = 1.0
```

#### `market_universe.py`
```python
SP100        # 100 large-cap tickers
NASDAQ100    # 100 NASDAQ tickers
SECTORS      # 7 sectors: Technology, Financials, Healthcare, Energy,
             #             Consumer, Industrials, Utilities & Telecom
BROAD_MARKET # sorted(set(SP100 + NASDAQ100))
```

#### `api_keys.py` *(updated v2.0 — secrets management)*
```python
def _get(key, default=""):
    # Priority 1: Streamlit Cloud secrets (st.secrets[key])
    # Priority 2: Environment variable (os.environ.get(key))
    # Priority 3: default value

POLYGON_API_KEY   = _get("POLYGON_API_KEY")
ALPHA_VANTAGE_KEY = _get("ALPHA_VANTAGE_KEY", "")
```

API keys are **never hardcoded**. See [Section 12](#12-deployment--secrets-management) for setup.

---

## 5. Full Quant Pipeline

```
run_quant_model("NVDA", "Aggressive")
│
├─► get_fundamentals("NVDA")
│     ├── yfinance.Ticker("NVDA").info  [primary]
│     │   Returns: {revenueGrowth: 0.22, grossMargins: 0.74,
│     │             operatingMargins: 0.55, debtToEquity: 42,
│     │             returnOnEquity: 0.91, forwardPE: 35, ...}
│     └── Polygon fallback if yfinance returns < 10 fields
│
├─► compute_scores(info)
│     ├── growth:        3  (revenue 15–30%)
│     ├── profitability: 4  (gross margin > 60%)
│     ├── efficiency:    3  (op margin > 30%)
│     ├── leverage:      2  (D/E < 50)
│     ├── roe:           3  (ROE > 25%)
│     ├── valuation:    -1  (P/E 30–45 = expensive)
│     └── total: 3×0.25 + 4×0.20 + 3×0.20 + 2×0.15 + 3×0.10 + (-1)×0.10
│               = 0.75 + 0.80 + 0.60 + 0.30 + 0.30 - 0.10 = 2.65
│
├─► calculate_volatility("NVDA")  →  0.42  (42% annualised)
│     └── get_price_history("NVDA", "1y") [yfinance → Polygon fallback]
│
├─► classify_intent(2.65, 0.42, "Aggressive")
│     Aggressive thresholds: STRONG BUY ≥ 2.5 AND vol < 0.45
│     → score 2.65 ≥ 2.5  ✓  |  vol 0.42 < 0.45  ✓
│     → ("STRONG BUY", 90)
│
├─► detect_regime(2.65)  →  "Expansion"  (score > 1)
│
├─► select_options_strategy("STRONG BUY", "Aggressive")
│     →  "Buy 12M ATM LEAPS Call"
│
├─► position_size("STRONG BUY", "Aggressive")
│     →  0.20 × 1.5 = 0.30  (30% allocation)
│
├─► risk_management(0.42, 0.30, "Aggressive")
│     Aggressive: moderate threshold = 0.55  →  vol 0.42 < 0.55  → no reduction
│     →  (0.30, "Normal Risk (42% vol within Aggressive tolerance)")
│
├─► get_price_history("NVDA", "1d")  →  current_price = $875.40
│     └── yfinance primary → Polygon fallback
│
├─► simulate_price(875.40, mu=0.10, sigma=0.42, T=1, sims=1000)
│     →  $952.83  (mean of 1000 GBM paths)
│
├─► timing_plan()
│     →  {entry: "8–12% pullback", add: "breakout confirmation", exit: "-20% or signal flip"}
│
└─► build_reasoning("NVDA", info, scores, "STRONG BUY", 0.42, 90)
      →  Full qualitative + quantitative report string
```

---

## 6. Risk Profile Impact Matrix

| Component | Conservative | Balanced | Aggressive | Speculator |
|-----------|-------------|----------|------------|------------|
| **Base allocation** | 5% | 10% | 20% | 30% |
| **STRONG BUY threshold** | score ≥ 3.2, vol < 20% | score ≥ 3.0, vol < 30% | score ≥ 2.5, vol < 45% | score ≥ 2.0, vol < 60% |
| **BUY threshold** | score ≥ 2.2, vol < 30% | score ≥ 1.8, vol < 50% | score ≥ 1.5, vol < 65% | score ≥ 1.2, vol < 80% |
| **Vol reduction (moderate)** | > 25% → ×0.75 | > 40% → ×0.75 | > 55% → ×0.75 | > 70% → ×0.75 |
| **Vol reduction (high)** | > 40% → ×0.50 | > 60% → ×0.50 | > 75% → ×0.50 | > 90% → ×0.50 |
| **STRONG BUY strategy** | Sell Cash-Secured Put | Bull Call Spread | Buy LEAPS Call | OTM Calls + LEAPS |
| **SELL strategy** | Deep ITM Covered Call | Protective Put | ATM Put / Ratio Spread | Deep OTM Bear Spread |

---

## 7. Data Source Fallback Chains

### 7.1 Options Data Fallback

```
get_options_chain(ticker)
         │
         ├─ POLYGON_API_KEY set?
         │    YES ──► GET /v3/snapshot/options/{ticker}
         │            ├─ Success → normalise → save_options_cache → return     [Polygon]
         │            └─ Fail → proceed to step 2
         │
         ├─ yfinance fallback
         │    ──► yf.Ticker(ticker).option_chain(exp)
         │        ├─ Success → save_options_cache → return                     [yfinance]
         │        └─ Fail → proceed to step 3
         │
         └─ Local cache fallback
              ──► load_options_cache(ticker, max_age_hours=4)
                  ├─ Fresh → return cached DataFrames                          [cache]
                  └─ Stale/missing → return (None, None)
```

### 7.2 Fundamentals Fallback

```
get_fundamentals(ticker)
         │
         ├─ yfinance primary
         │    ──► yf.Ticker(ticker).info
         │        ├─ ≥ 10 fields → return info dict                           [yfinance]
         │        └─ < 10 fields or error → proceed to Polygon
         │
         └─ Polygon.io fallback (3 independent calls)
              ├─ GET /v3/reference/tickers/{ticker}
              │    → name, sector, sic_description, market_cap
              ├─ GET /vX/reference/financials?ticker=X&timeframe=annual&limit=2
              │    → revenue_growth, gross_margin, op_margin, ROA, ROE, D/E
              └─ Merge results → map to yfinance field names → return          [Polygon]
```

### 7.3 Market Data Fallback

```
get_price_history(ticker, period)
         │
         ├─ yfinance primary
         │    ──► yf.download(ticker, period, auto_adjust=True)
         │        ├─ Non-empty DataFrame → normalise columns → return          [yfinance]
         │        └─ Empty or error → proceed to Polygon
         │
         └─ Polygon.io fallback
              ──► GET /v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}
                  params: adjusted=true, sort=asc, limit=50000
                  ├─ Non-empty → build DataFrame (Date index, OHLCV) → return  [Polygon]
                  └─ Empty → raise ValueError("No market data available...")
```

---

## 8. Market Sentiment Architecture

```
Tab 6 — Sentiment Dashboard
│
├─ 📡 Financial News Sentiment (Tab A)
│   │
│   ├── get_market_news_sentiment(days_back, max_per_source)
│   │    │
│   │    ├── ThreadPoolExecutor (10 workers)
│   │    │    ├── _fetch_source("CNBC", url, ...)
│   │    │    ├── _fetch_source("MarketWatch", url, ...)
│   │    │    ├── _fetch_source("Yahoo Finance", url, ...)
│   │    │    ├── _fetch_source("Reuters", url, ...)
│   │    │    ├── _fetch_source("Bloomberg", url, ...)
│   │    │    ├── _fetch_source("CNN Business", url, ...)
│   │    │    ├── _fetch_source("Google Finance", url, ...)
│   │    │    ├── _fetch_source("Barron's", url, ...)
│   │    │    ├── _fetch_source("Seeking Alpha", url, ...)
│   │    │    ├── _fetch_source("Morningstar", url, ...)
│   │    │    ├── _fetch_source("Investopedia", url, ...)
│   │    │    └── _fetch_source("FT Markets", url, ...)
│   │    │         └── Each: feedparser.parse → VADER score → theme detection
│   │    │
│   │    └── Aggregate: overall_score, per_source, theme_breakdown,
│   │                   top_bullish/bearish headlines, all_articles
│   │
│   ├── Stored in st.session_state["fin_sent_data"]
│   │
│   ├── Displayed across 4 inner sub-tabs:
│   │    ├── 🗞️ Per-Source Breakdown (table + Plotly bar)
│   │    ├── 🏷️ Macro Themes (table + Plotly bar)
│   │    ├── 📰 Top Headlines (bullish/bearish side-by-side)
│   │    └── 📚 Full Article Feed (filterable by source + sentiment)
│   │
│   └── identify_top_stocks(sentiment_data, run_model, profile)
│        │
│        ├── Score & rank bullish themes
│        ├── Map themes → THEME_TICKERS
│        ├── ThreadPoolExecutor (8 workers): run_quant_model per candidate
│        ├── Add sentiment_bonus to quant composite score
│        └── Return top N picks with full model output + theme context
│             └── Displayed as expandable pick cards with:
│                  intent badge · metrics row · risk flag · options strategy
│                  driving themes · factor score breakdown · reasoning · timing
│
└─ 🐦 Reddit Retail Sentiment (Tab B)
    │
    └── run_market_sentiment_engine()  [@st.cache_data ttl=600]
         ├── feedparser → r/stocks, r/investing, r/wallstreetbets, r/finance, r/economy
         ├── VADER sentiment per post
         ├── Ticker extraction (regex [A-Z]{2,5})
         └── Returns: market score, ticker table, top tickers/keywords, sample posts
              └── Displayed with Plotly bar charts + expandable post cards
```

---

## 9. UI Architecture

### 9.1 Global Layout

```
app.py top-level structure:
│
├── st.set_page_config(layout="wide", page_icon="📊")        ← must be first
├── st.markdown(CSS)                                          ← global styling
├── Constants: DEFAULT_UNIVERSE, INTENT_COLORS, INTENT_ICONS, PROFILE_OPTIONS
├── Helper functions: _resolve_tickers, _universe_controls, _run_prescreen,
│                     _intent_banner, colour_*, _plotly_defaults
├── @st.cache_data load_reddit_sentiment()
│
├── with st.sidebar:                                          ← persistent sidebar
│   ├── SVG logo mark
│   ├── global_profile selectbox
│   ├── Navigation table
│   └── About caption
│
├── st.markdown(header_banner_html)                           ← SVG logo + gradient text
│
└── tab1..tab6 = st.tabs([...])                              ← 6 main tabs
```

### 9.2 Tab Structure

```
Tab 1 — Stock Analysis
  ├── 🎓 Novice expander
  ├── 📘 Glossary expander
  ├── Ticker input + Risk Profile (pre-filled from global_profile)
  ├── [Run Full Analysis button]
  └── Results:
       ├── Intent banner (full-width coloured HTML)
       ├── 6-column metric row + MC projection metric
       ├── Risk Flag (st.warning) + Options Strategy (st.info)
       ├── Factor scores: 6 metrics + Plotly horizontal bar chart
       ├── Qualitative Reasoning (st.text)
       └── Timing Plan (st.info)

Tab 2 — Market Scan
  ├── 🎓 Novice expander
  ├── Risk Profile + Universe controls + Pre-screen filters
  ├── [Run Market Scan button]
  ├── 5-column signal count bar + CSV download button
  ├── 2-column charts (donut pie + horizontal bar)
  └── 5 inner sub-tabs:
       ├── 📋 Signal & Risk (styled dataframe)
       ├── 💰 Fundamentals (styled dataframe)
       ├── 📈 Momentum (styled dataframe)
       ├── 🔬 Factor Heatmap (gradient background dataframe)
       └── 🏭 Sector Breakdown (table + Plotly bar)

Tab 3 — Performance
  ├── 🎓 Novice expander
  └── 2 inner tabs:
       ├── 📌 Single Stock: ticker input → 5 metrics
       └── 🔄 Compare Universe:
            ├── Universe controls + Sort-by selectbox
            ├── [Compare Performance button]
            ├── Styled dataframe (top 3 Sharpe highlighted green)
            └── Plotly Sharpe bar chart

Tab 4 — Options Strategy
  ├── 🎓 Novice expander
  ├── 📘 Scoring guide expander
  ├── Risk Profile selectbox
  └── 2 inner tabs:
       ├── 🏆 Top Opportunities:
       │    ├── Universe controls
       │    ├── [Scan button]
       │    └── Styled dataframe
       └── 📃 LEAPS Generator:
            ├── Ticker input + [Generate button]
            ├── 5 metric cards (Strike, Premium, Break-Even, Expiry, Type)
            ├── Greeks row (if available)
            ├── Plotly P&L chart (area fill, hover, annotations)
            └── Raw JSON expander

Tab 5 — Market News
  ├── 🎓 Novice expander
  ├── Ticker input + [Fetch News button]
  └── Results:
       ├── Sentiment banner (coloured st.success/error/warning)
       ├── Ecosystem cards (Company, Industry, Competitors, Suppliers)
       ├── Summary + Financial Announcements (2 columns)
       └── Articles as expandable cards (icon + source + date + link)

Tab 6 — Sentiment Engine
  ├── 🎓 Novice expander
  └── 2 inner tabs:
       ├── 📡 Financial News Sentiment:
       │    ├── Days/articles sliders + [Fetch button]
       │    ├── Large sentiment banner (### heading in st.success/error/warning)
       │    ├── 4 overall metrics
       │    └── 4 nested sub-tabs:
       │         ├── 🗞️ Per-Source (table + Plotly bar)
       │         ├── 🏷️ Macro Themes (table + Plotly bar)
       │         ├── 📰 Top Headlines (2-column bullish/bearish)
       │         └── 📚 Full Article Feed (multiselect filters)
       │    └── Sentiment Picks section:
       │         ├── Risk Profile + N picks inputs
       │         ├── [Identify Top Stocks button]
       │         ├── Bullish theme metric cards
       │         └── Pick expander cards (intent badge, metrics, themes, factors, reasoning)
       └── 🐦 Reddit Retail Sentiment:
            ├── [Refresh button]
            ├── Sentiment banner
            ├── Ticker sentiment styled dataframe
            ├── 2-column Plotly bars (tickers + keywords)
            └── Sample posts as expandable cards
```

### 9.3 Session State

| Key | Set when | Used by | Persists |
|-----|----------|---------|----------|
| `scan_results` | Market Scan button | Tab 2 results display | Tab 2 |
| `perf_results` | Compare Performance button | Tab 3 results display | Tab 3 |
| `opt_results` | Scan Options button | Tab 4 results display | Tab 4 |
| `leaps_contract` | Generate LEAPS button | Tab 4 LEAPS display | Tab 4 |
| `news_data` | Fetch News button | Tab 5 results display | Tab 5 |
| `fin_sent_data` | Fetch Financial News Sentiment | Top-5 picker, Tab 6 results | Tab 6 |
| `picker_result` | Identify Top Stocks button | Pick cards display | Tab 6 |

All results persist in session state so they survive widget interactions without re-running expensive API calls.

---

## 10. Scoring & Threshold Reference

### Factor Score Bands

| Factor | Score | Condition |
|--------|-------|-----------|
| **Growth** | +5 | revenueGrowth > 30% |
| | +3 | revenueGrowth > 15% |
| | +1 | revenueGrowth > 0% |
| | −2 | revenueGrowth ≤ 0% |
| **Profitability** | +4 | grossMargins > 60% |
| | +2 | grossMargins > 50% |
| | −1 | grossMargins ≤ 50% |
| **Efficiency** | +3 | operatingMargins > 30% |
| | +1 | operatingMargins > 15% |
| | −1 | operatingMargins ≤ 15% |
| **Leverage** | +2 | D/E < 50 |
| | 0 | D/E < 100 |
| | −2 | D/E ≥ 100 |
| **ROE** | +3 | returnOnEquity > 25% |
| | +1 | returnOnEquity > 15% |
| | −1 | returnOnEquity ≤ 15% |
| **Valuation** | +2 | forwardPE < 15 (cheap) |
| | +1 | forwardPE < 22 (fair) |
| | 0 | forwardPE < 30 (stretched) |
| | −1 | forwardPE < 45 (expensive) |
| | −3 | forwardPE ≥ 45 or N/A |

### Composite Score Interpretation

| Composite Score | Regime | Signal (Balanced) |
|-----------------|--------|-------------------|
| ≥ 3.0 + vol < 0.30 | Expansion | **STRONG BUY** |
| ≥ 1.8 + vol < 0.50 | Expansion/Late Cycle | **BUY** |
| ≥ 0.8 | Late Cycle | **HOLD** |
| ≥ 0.0 | Neutral | **REDUCE** |
| < 0.0 | Contraction | **SELL** |

---

## 11. Concurrency Model

```
Component                     Workers    Pattern
─────────────────────────────────────────────────────────────────
market_screener.pre_screen    12         ThreadPoolExecutor / as_completed
market_scanner.scan_market     8         ThreadPoolExecutor / as_completed + progress_cb
market_news_sentiment          10        ThreadPoolExecutor / as_completed
sentiment_stock_picker          8        ThreadPoolExecutor / as_completed
performance_engine (compare)    8        ThreadPoolExecutor / as_completed
─────────────────────────────────────────────────────────────────
```

**Pattern used throughout:**
```python
with ThreadPoolExecutor(max_workers=N) as pool:
    futures = {pool.submit(fn, arg): arg for arg in items}
    for future in as_completed(futures):
        result = future.result()   # handle individually, fail-safe
```

Each worker is independently fail-safe — exceptions are caught per-ticker and skipped, never crashing the full scan.

---

## 12. Deployment & Secrets Management

### Local Development

```
.streamlit/
  secrets.toml          ← git-ignored, local secrets only
    POLYGON_API_KEY = "your_key_here"
    ALPHA_VANTAGE_KEY = ""
```

Run locally:
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m textblob.download_corpora
streamlit run app.py
```

### Streamlit Cloud (Production)

1. Push repo to GitHub (`.streamlit/secrets.toml` excluded by `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select repo, branch `main`, main file `app.py`
4. Advanced settings → Secrets → paste:
   ```toml
   POLYGON_API_KEY = "your_key_here"
   ALPHA_VANTAGE_KEY = ""
   ```
5. Deploy → public URL assigned automatically

### Secret Resolution Priority (config/api_keys.py)

```
1. st.secrets[key]          ← Streamlit Cloud secrets (production)
2. os.environ.get(key)      ← Environment variable (CI/CD, Docker)
3. default value ("")       ← Safe fallback — Polygon disabled, yfinance only
```

### `.gitignore` Coverage

```
venv/               ← virtual environment
.streamlit/secrets.toml  ← local secrets
storage/cache/      ← options pickle cache
*.pkl               ← any stale cache files
__pycache__/        ← compiled bytecode
.env                ← dotenv files
```

---

## 13. File Reference Table

| Path | Purpose | Key Function(s) | v2 Changes |
|------|---------|-----------------|------------|
| `app.py` | Streamlit UI — 6 tabs | `_resolve_tickers`, `_universe_controls`, `_run_prescreen`, `_intent_banner`, `_plotly_defaults` | Full UI overhaul — Plotly, sidebar, inner tabs, session state, logo, novice guides |
| `main.py` | Quant pipeline orchestrator | `run_quant_model(ticker, profile) → dict` | — |
| `config/settings.py` | Risk profiles & factor weights | constants | — |
| `config/market_universe.py` | Ticker universe lists | `SP100, NASDAQ100, SECTORS, BROAD_MARKET` | — |
| `config/api_keys.py` | API credentials | `POLYGON_API_KEY` | Reads from st.secrets → env vars (never hardcoded) |
| `data/fundamentals.py` | Fundamentals with fallback | `get_fundamentals(ticker) → dict` | Added Polygon.io fallback (3 API calls) |
| `data/market_data.py` | OHLCV with fallback | `get_price_history(ticker, period) → DataFrame` | Added Polygon /v2/aggs fallback |
| `data/options_chain.py` | Options chain (3-source fallback) | `get_options_chain`, `get_options_by_expiry`, `get_expirations` | — |
| `data/volatility.py` | Volatility wrapper (back-compat) | `get_options_chain_for_volatility(ticker)` | — |
| `engines/factor_engine.py` | 6-factor scoring + reasoning | `compute_scores(info)`, `build_reasoning(...)` | — |
| `engines/intent_classifier.py` | Signal classifier | `classify_intent(score, vol, profile)` | — |
| `engines/regime_engine.py` | Regime detector | `detect_regime(score)` | — |
| `engines/options_selector.py` | Strategy selector (20 strategies) | `select_options_strategy(intent, profile)` | — |
| `engines/position_sizer.py` | Position allocator | `position_size(intent, profile)` | — |
| `engines/timing_engine.py` | Entry/exit timing rules | `timing_plan()` | — |
| `engines/volatility_engine.py` | Annualised vol calculator | `calculate_volatility(ticker)` | — |
| `engines/risk_engine.py` | Vol-based position adjustment | `risk_management(vol, alloc, profile)` | — |
| `engines/greeks_optimizer.py` | Delta filter | `optimize_by_delta(df, min_d, max_d)` | — |
| `engines/market_scanner.py` | Parallel full-model scan | `scan_market(tickers, run_model, profile, ...)` | — |
| `engines/market_screener.py` | Lightweight pre-screener | `pre_screen(tickers, min_mcap, min_vol, ...)` | — |
| `engines/news_engine.py` | Ticker-specific news (5 RSS) | `get_market_news(ticker, days_back, max_items)` | — |
| `engines/social_sentiment_engine.py` | Reddit sentiment (5 subreddits) | `run_market_sentiment_engine(limit_per_feed)` | — |
| `engines/market_news_sentiment_engine.py` | Financial news sentiment (12 sources) | `get_market_news_sentiment(days_back, max_per_source)` | — |
| `engines/sentiment_stock_picker.py` | Sentiment → stock candidates | `identify_top_stocks(sentiment_data, run_model, ...)` | — |
| `engines/performance_engine.py` | Historical performance metrics | `compute_performance_metrics(ticker)` | — |
| `engines/options_contract_engine.py` | LEAPS contract selector | `select_leaps_contract(ticker, min_months)` | — |
| `engines/options_opportunity_engine.py` | Options opportunity ranker | `rank_option_opportunities(tickers, run_model, profile)` | — |
| `engines/options_payoff_engine.py` | Call payoff calculator | `calculate_call_payoff(strike, premium, price_range)` | — |
| `models/monte_carlo.py` | GBM price simulator | `simulate_price(S0, mu, sigma, T, sims)` | — |
| `models/backtester.py` | MA50 backtest | `backtest(ticker)` | — |
| `storage/cache.py` | Options pickle cache + SQLite init | `save_options_cache`, `load_options_cache`, `init_db` | — |
| `storage/database.py` | Signal history DB | `init_db()` | — |
| `requirements.txt` | Python dependencies | — | Added plotly; pinned versions for Streamlit Cloud compatibility |
| `.gitignore` | Git exclusions | — | New in v2.0 |
| `.streamlit/secrets.toml` | Local dev secrets (git-ignored) | — | New in v2.0 |

---

## 14. Key Dependencies

| Package | Version | Usage |
|---------|---------|-------|
| `streamlit` | ≥ 1.32.0 | Web UI framework |
| `plotly` | ≥ 5.18.0 | Interactive charts (replaces matplotlib throughout) |
| `yfinance` | ≥ 0.2.36 | Primary: fundamentals, price history, options chain |
| `pandas` | ≥ 2.0.0 | All tabular data processing |
| `numpy` | ≥ 1.26.0 | Volatility, Monte Carlo, RSI calculations |
| `requests` | ≥ 2.31.0 | Polygon.io REST API calls |
| `feedparser` | ≥ 6.0.10 | RSS feed parsing (news sources, Reddit) |
| `vaderSentiment` | ≥ 3.3.2 | Financial news & Reddit sentiment scoring |
| `textblob` | ≥ 0.18.0 | Legacy sentiment in `news_engine.py` |
| `scipy` | ≥ 1.11.0 | Statistical utilities |
| `matplotlib` | ≥ 3.8.0 | Retained as dependency (not used in UI — Plotly used instead) |
| `praw` | ≥ 7.7.0 | Reddit API (social sentiment engine) |
| `concurrent.futures` | stdlib | ThreadPoolExecutor for all parallel scans |
| `pickle` | stdlib | Options chain local cache serialisation |
| `sqlite3` | stdlib | Signal history database |

---

## 15. Adding New Features

### Add a new engine

1. Create `engines/my_engine.py` with a single focused function
2. Import and call it in `main.py` within `run_quant_model()`
3. Add the result key to the return dict
4. Display in the relevant tab in `app.py`
5. Document any new settings in `config/settings.py`

### Add a new data source for fundamentals or market data

1. Add a `_mysource_fundamentals(ticker)` function in `data/fundamentals.py`
2. Add it as the next fallback step in `get_fundamentals()` after Polygon
3. Map all returned fields to the same yfinance key names

### Add a new data source for options

1. Add a `_fetch_mysource(ticker, expiry)` function in `data/options_chain.py`
2. Add it as a fallback step in `_get_chain_with_fallback()` before the cache
3. Normalise output to the standard column schema

### Add a new universe

1. Add the ticker list to `config/market_universe.py`
2. Add the option to `UNIVERSE_OPTIONS` in `_universe_controls()` in `app.py`
3. Add the resolution branch in `_resolve_tickers()`

### Add a new news source

1. Add the RSS URL to `NEWS_SOURCES` dict in `engines/market_news_sentiment_engine.py`
2. No other changes needed — the parallel fetcher handles it automatically

### Add a new macro theme

1. Add the theme name and keyword list to `MACRO_THEMES` in `engines/market_news_sentiment_engine.py`
2. Add the theme → ticker mapping to `THEME_TICKERS` in `engines/sentiment_stock_picker.py`

### Add a new risk profile

1. Add to `RISK_PROFILES` in `config/settings.py`
2. Add threshold row in `engines/intent_classifier.py` → `thresholds` dict
3. Add vol threshold row in `engines/risk_engine.py` → `vol_thresholds` dict
4. Add strategy column in `engines/options_selector.py` → `strategies` dict
5. Add to `PROFILE_OPTIONS` constant in `app.py`

---

## 16. Changelog

### v2.0 — 2026-03-15

#### Data Resilience
- **`data/fundamentals.py`** — Added Polygon.io as fallback when yfinance returns < 10 fields or fails. Three Polygon calls: `/v3/reference/tickers` (company metadata), `/vX/reference/financials` (income statement / balance sheet ratios), field-mapped to exact yfinance key names so no downstream changes required. Result dict includes `_source` key for diagnostics.
- **`data/market_data.py`** — Added Polygon.io `/v2/aggs` as fallback for historical OHLCV data. Period strings mapped to calendar days. Returns identical DataFrame schema to yfinance. Raises `ValueError` only if both sources fail.

#### Secrets Management
- **`config/api_keys.py`** — Replaced hardcoded API key with priority-based resolver: `st.secrets` → environment variable → empty default. Key is never committed to version control.
- **`.streamlit/secrets.toml`** — Created for local development (git-ignored).
- **`.gitignore`** — Created covering venv, `__pycache__`, secrets, pickle cache, .env files.
- **`requirements.txt`** — Added `plotly≥5.18.0`; pinned `streamlit≥1.32.0` and `altair≥5.0.0` to resolve Streamlit Cloud altair/vegalite version conflict.

#### UI Overhaul (app.py)
- **Global CSS** — Metric card borders, tab styling, button hover animation, consistent border radius, sidebar text colour fix
- **SVG Logo Banner** — Full-width header with inline SVG candlestick logo mark, gradient text, and 4 pill badges (LIVE DATA · 6-FACTOR MODEL · POLYGON·YFINANCE·CACHE · BETA)
- **Sidebar** — Added persistent sidebar with global risk profile selector (pre-fills all tab selectboxes), quick navigation table, SVG mini logo mark
- **Plotly replaces Matplotlib** — All charts are now interactive (hover, zoom, pan, PNG download). `matplotlib` retained in requirements but not used in UI.
- **Session state** — All expensive results (scan, performance, options, LEAPS, news, sentiment, picks) persisted in `st.session_state` to survive widget interactions
- **Novice guidance** — `🎓 New Here?` expander added to every tab with plain-English explanations, step-by-step instructions, and cross-tab tips

**Tab 1 (Stock Analysis):**
- Replaced `st.json()` output with structured metric cards + full-width intent banner
- Added Plotly horizontal bar chart for factor score breakdown
- Risk Flag shown as `st.warning`, Options Strategy as `st.info`

**Tab 2 (Market Scan):**
- Renamed from "Market Snapshot" to "Market Scan"
- 5 data tables moved into inner `st.tabs` (Signal & Risk · Fundamentals · Momentum · Factor Heatmap · Sector Breakdown)
- Charts moved above tables; pie chart → donut chart; all charts → Plotly
- Sector breakdown tab includes Plotly colour-scale bar chart
- CSV download button added

**Tab 3 (Performance):**
- Mode radio button → `st.tabs(["Single Stock", "Compare Universe"])`
- Sort-by selectbox added to compare mode
- Top 3 Sharpe Ratio rows highlighted with green background
- Sharpe bar chart → Plotly; results persist in session state

**Tab 4 (Options Strategy):**
- Mode radio button → `st.tabs(["Top Opportunities", "LEAPS Generator"])`
- LEAPS output: `st.json()` → metric cards (Strike, Premium, Break-Even, Expiry, Type + Greeks row)
- LEAPS P&L chart → Plotly Scatter with area fill, break-even annotation, strike annotation, hover tooltip
- Raw JSON available in collapsible expander

**Tab 5 (Market News):**
- Sentiment banner (coloured) shown at top before ecosystem
- Ecosystem displayed as metric + info cards (not plain text)
- Articles displayed as expandable cards with sentiment icon

**Tab 6 (Sentiment Engine):**
- Section radio button → `st.tabs(["Financial News", "Reddit"])`
- Financial news: large sentiment banner (### heading) + 4 nested sub-tabs
- Reddit: Most Discussed + Trending Themes → Plotly bar charts; posts → expandable cards

---

*Generated from codebase analysis — c:\Users\shriy\quant_system\options*
