# Intelligent Investment Research Platform — Architecture & Developer Reference

> Version: 1.0 | Last updated: 2026-03-15
> Stack: Python 3.13 · Streamlit · yfinance · Polygon.io · VADER · feedparser · ThreadPoolExecutor

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
7. [Options Data Fallback Chain](#7-options-data-fallback-chain)
8. [Market Sentiment Architecture](#8-market-sentiment-architecture)
9. [Scoring & Threshold Reference](#9-scoring--threshold-reference)
10. [Concurrency Model](#10-concurrency-model)
11. [File Reference Table](#11-file-reference-table)
12. [Key Dependencies](#12-key-dependencies)
13. [Adding New Features](#13-adding-new-features)

---

## 1. System Overview

This platform is a **modular quantitative research system** for options and equity analysis. It combines:

- **Fundamental factor scoring** across 6 weighted metrics
- **Risk-profile-aware signal classification** (5-level intent: STRONG BUY → SELL)
- **Options strategy selection** with 20 distinct strategy-profile combinations
- **Multi-source options data** with Polygon → yfinance → local cache fallback
- **Broad market scanning** across S&P 100, NASDAQ 100, and sector universes
- **Financial news sentiment** aggregated from 12 professional sources
- **Reddit retail sentiment** across 5 subreddits
- **Sentiment-driven stock picking** mapping bullish news themes to quant-validated candidates
- **Monte Carlo price projection** via Geometric Brownian Motion

---

## 2. High-Level Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         STREAMLIT UI  (app.py)                               ║
║                                                                              ║
║  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐ ┌────────────────────┐ ║
║  │ Tab 1       │ │ Tab 2        │ │ Tab 3          │ │ Tab 4              │ ║
║  │ Stock       │ │ Market       │ │ Performance    │ │ Options Strategy   │ ║
║  │ Analysis    │ │ Snapshot     │ │ Dashboard      │ │ Marketplace        │ ║
║  └──────┬──────┘ └──────┬───────┘ └───────┬────────┘ └────────┬───────────┘ ║
║         │               │                 │                    │             ║
║  ┌──────┴──────┐ ┌──────┴───────┐         │         ┌────────┴───────────┐ ║
║  │ Tab 5       │ │ Tab 6        │         │         │ LEAPS Generator    │ ║
║  │ Market News │ │ Sentiment    │         │         │ Top 10 Scanner     │ ║
║  │             │ │ Dashboard    │         │         └────────────────────┘ ║
║  └─────────────┘ └──────────────┘         │                                 ║
╚══════════════════════════════════════════╪═════════════════════════════════╝
                                           │
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
║ intent_classif ║           ║   └── yfinance       ║    ║ backtester.py     ║
║ regime_engine  ║◄──────────║ market_data.py       ║    ╚═══════════════════╝
║ options_select ║           ║   └── yfinance       ║
║ position_sizer ║◄──────────║ options_chain.py     ║    ╔═══════════════════╗
║ timing_engine  ║           ║   ├── Polygon.io     ║    ║  STORAGE LAYER    ║
║ volatility_eng ║           ║   ├── yfinance       ║    ║                   ║
║ risk_engine    ║           ║   └── local cache ───╫────║ cache.py (pickle) ║
╚════════════════╝           ║ volatility.py        ║    ║ database.py (SQL) ║
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
║  FACTOR_WEIGHTS      SECTORS, BROAD_MARKET    ALPHA_VANTAGE_KEY            ║
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
│  get_fundamentals  │──► yfinance .info dict
└────────┬───────────┘     (revenueGrowth, grossMargins, operatingMargins,
         │                  debtToEquity, returnOnEquity, forwardPE,
         │                  marketCap, sector, shortName)
         ▼
┌────────────────────┐
│  compute_scores    │──► Factor scores dict
└────────┬───────────┘     {growth, profitability, efficiency,
         │                  leverage, roe, valuation, total}
         │                  total ∈ [-1.60, +3.45]
         ▼
┌────────────────────┐
│ calculate_volatility│──► annualised vol (float)
└────────┬───────────┘     (252-day rolling std of daily returns)
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
│  select_options_strategy           │──► strategy string
│  (intent, risk_profile)            │    20 distinct strategies
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
│  get_price_history │──► current_price
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

The Streamlit frontend. Six tabs, all sharing shared helper functions.

| Tab | Name | Primary Engine(s) Called |
|-----|------|--------------------------|
| 1 | Stock Analysis | `run_quant_model` |
| 2 | Market Snapshot | `scan_market`, `pre_screen` |
| 3 | Performance Dashboard | `compute_performance_metrics` |
| 4 | Options Strategy | `rank_option_opportunities`, `select_leaps_contract` |
| 5 | Market News | `get_market_news` |
| 6 | Sentiment Dashboard | `get_market_news_sentiment`, `identify_top_stocks`, `run_market_sentiment_engine` |

**Shared Helpers (defined in `app.py`):**

```
_resolve_tickers(universe_choice, selected_sectors, custom_input) -> list[str]
    Converts universe selector state to a flat ticker list.
    Supports: S&P 100, NASDAQ 100, Broad Market, Sector, Custom.

_universe_controls(prefix, default_top_n, show_top_n) -> (choice, sectors, custom, top_n, min_mcap, min_vol)
    Renders universe selector widgets (unique keys via prefix).
    Used in Tab 2, Tab 3 (compare mode), Tab 4.

_run_prescreen(raw_tickers, top_n, min_mcap, min_vol, sectors) -> (run_tickers, summary, failed)
    Thin wrapper around pre_screen(); returns sorted list ready for full model.
```

**Session State Keys:**

| Key | Set by | Used by |
|-----|--------|---------|
| `fin_sent_data` | "Fetch Financial News Sentiment" button | Top-5 picker |
| `picker_result` | "Identify Top Stocks" button | Pick cards display |

---

### 4.2 Controller Layer — `main.py`

```python
run_quant_model(ticker: str, risk_profile: str) -> dict
```

Orchestrates the full 12-stage pipeline in sequential order. The only entry point used by all UI tabs.

**Stage sequence:**
```
1  get_fundamentals(ticker)                       → info dict
2  compute_scores(info)                           → scores dict
3  calculate_volatility(ticker)                   → float
4  classify_intent(score, vol, profile)           → (intent, confidence)
5  detect_regime(score)                           → str
6  select_options_strategy(intent, profile)       → str
7  position_size(intent, profile)                 → float
8  risk_management(vol, allocation, profile)      → (float, str)
9  get_price_history(ticker)                      → DataFrame → current_price
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
select_leaps_contract(ticker, min_months=10) -> {Expiration, Strike, Premium, Contract Symbol}
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
**Purpose:** 5-year historical performance statistics.

```
compute_performance_metrics(ticker) -> {Total Return (%), Annual Return (%),
                                        Annual Volatility (%), Sharpe Ratio, Max Drawdown (%)}
```

---

### 4.4 Data Layer — `data/`

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

**Normalised output columns (both Polygon and yfinance):**

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

---

## 5. Full Quant Pipeline

```
run_quant_model("NVDA", "Aggressive")
│
├─► get_fundamentals("NVDA")
│     └── yfinance.Ticker("NVDA").info
│         Returns: {revenueGrowth: 0.22, grossMargins: 0.74,
│                   operatingMargins: 0.55, debtToEquity: 42,
│                   returnOnEquity: 0.91, forwardPE: 35, ...}
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

## 7. Options Data Fallback Chain

```
get_options_chain(ticker)
         │
         ├─ POLYGON_API_KEY set?
         │    YES ──► GET /v3/snapshot/options/{ticker}
         │            ├─ Success → normalise to DataFrame
         │            │           save_options_cache(ticker, calls, puts)
         │            │           return (calls, puts)          ← source: Polygon
         │            └─ Fail → log warning, proceed to step 2
         │
         ├─ yfinance fallback
         │    ──► yf.Ticker(ticker).options → expirations
         │        yf.Ticker(ticker).option_chain(exp) → chain
         │        ├─ Success → save_options_cache(ticker, calls, puts)
         │        │           return (calls, puts)              ← source: yfinance
         │        └─ Fail → log warning, proceed to step 3
         │
         └─ Local cache fallback
              ──► load_options_cache(ticker)
                  ├─ Fresh (< 4h) → return (calls, puts)       ← source: cache
                  └─ Stale or missing → return (None, None)
```

---

## 8. Market Sentiment Architecture

```
Tab 6 — Sentiment Dashboard
│
├─ Section A: Financial News Sentiment
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
│   └── identify_top_stocks(sentiment_data, run_model, profile)
│        │
│        ├── Score & rank bullish themes
│        ├── Map themes → THEME_TICKERS
│        ├── ThreadPoolExecutor (8 workers): run_quant_model per candidate
│        ├── Add sentiment_bonus to quant composite score
│        └── Return top N picks with full model output + theme context
│
└─ Section B: Reddit Retail Sentiment
    │
    └── run_market_sentiment_engine()
         ├── feedparser → r/stocks, r/investing, r/wallstreetbets, r/finance, r/economy
         ├── VADER sentiment per post
         ├── Ticker extraction (regex [A-Z]{2,5})
         └── Returns: market score, ticker table, top tickers/keywords, sample posts
```

---

## 9. Scoring & Threshold Reference

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

## 10. Concurrency Model

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

Each worker is independently fail-safe — exceptions are caught and the ticker is skipped, never crashing the full scan.

---

## 11. File Reference Table

| Path | Purpose | Key Function(s) |
|------|---------|-----------------|
| `app.py` | Streamlit UI — 6 tabs | `_resolve_tickers`, `_universe_controls`, `_run_prescreen` |
| `main.py` | Quant pipeline orchestrator | `run_quant_model(ticker, profile) → dict` |
| `config/settings.py` | Risk profiles & factor weights | constants |
| `config/market_universe.py` | Ticker universe lists | `SP100, NASDAQ100, SECTORS, BROAD_MARKET` |
| `config/api_keys.py` | API credentials | `POLYGON_API_KEY` |
| `config/api/live_data.py` | Polygon last-trade wrapper | `get_price_polygon(ticker, key)` |
| `data/fundamentals.py` | yfinance fundamentals | `get_fundamentals(ticker) → dict` |
| `data/market_data.py` | OHLCV downloader | `get_price_history(ticker, period) → DataFrame` |
| `data/options_chain.py` | Options chain (3-source fallback) | `get_options_chain`, `get_options_by_expiry`, `get_expirations` |
| `data/volatility.py` | Volatility wrapper (back-compat) | `get_options_chain_for_volatility(ticker)` |
| `engines/factor_engine.py` | 6-factor scoring + reasoning | `compute_scores(info)`, `build_reasoning(...)` |
| `engines/intent_classifier.py` | Signal classifier | `classify_intent(score, vol, profile)` |
| `engines/regime_engine.py` | Regime detector | `detect_regime(score)` |
| `engines/options_selector.py` | Strategy selector (20 strategies) | `select_options_strategy(intent, profile)` |
| `engines/position_sizer.py` | Position allocator | `position_size(intent, profile)` |
| `engines/timing_engine.py` | Entry/exit timing rules | `timing_plan()` |
| `engines/volatility_engine.py` | Annualised vol calculator | `calculate_volatility(ticker)` |
| `engines/risk_engine.py` | Vol-based position adjustment | `risk_management(vol, alloc, profile)` |
| `engines/greeks_optimizer.py` | Delta filter | `optimize_by_delta(df, min_d, max_d)` |
| `engines/market_scanner.py` | Parallel full-model scan | `scan_market(tickers, run_model, profile, ...)` |
| `engines/market_screener.py` | Lightweight pre-screener | `pre_screen(tickers, min_mcap, min_vol, ...)` |
| `engines/news_engine.py` | Ticker-specific news (5 RSS) | `get_market_news(ticker, days_back, max_items)` |
| `engines/social_sentiment_engine.py` | Reddit sentiment (5 subreddits) | `run_market_sentiment_engine(limit_per_feed)` |
| `engines/market_news_sentiment_engine.py` | Financial news sentiment (12 sources) | `get_market_news_sentiment(days_back, max_per_source)` |
| `engines/sentiment_stock_picker.py` | Sentiment → stock candidates | `identify_top_stocks(sentiment_data, run_model, ...)` |
| `engines/performance_engine.py` | 5-year performance metrics | `compute_performance_metrics(ticker)` |
| `engines/options_contract_engine.py` | LEAPS contract selector | `select_leaps_contract(ticker, min_months)` |
| `engines/options_opportunity_engine.py` | Options opportunity ranker | `rank_option_opportunities(tickers, run_model, profile)` |
| `engines/options_payoff_engine.py` | Call payoff calculator | `calculate_call_payoff(strike, premium, price_range)` |
| `models/monte_carlo.py` | GBM price simulator | `simulate_price(S0, mu, sigma, T, sims)` |
| `models/backtester.py` | MA50 backtest | `backtest(ticker)` |
| `storage/cache.py` | Options pickle cache + SQLite init | `save_options_cache`, `load_options_cache`, `init_db` |
| `storage/database.py` | Signal history DB | `init_db()` |

---

## 12. Key Dependencies

| Package | Usage |
|---------|-------|
| `streamlit` | Web UI framework |
| `yfinance` | Fundamentals, price history, options chain fallback |
| `pandas` | All tabular data processing |
| `numpy` | Volatility, Monte Carlo, RSI calculations |
| `matplotlib` | Charts in Streamlit (bar, pie, payoff diagrams) |
| `requests` | Polygon.io API calls |
| `feedparser` | RSS feed parsing (news, Reddit) |
| `vaderSentiment` | Financial news & Reddit sentiment scoring |
| `textblob` | Legacy sentiment in `news_engine.py` |
| `beautifulsoup4` | HTML cleaning in social sentiment engine |
| `concurrent.futures` | ThreadPoolExecutor for all parallel scans |
| `pickle` | Options chain local cache serialisation |
| `sqlite3` | Signal history database (stdlib) |

---

## 13. Adding New Features

### Add a new engine

1. Create `engines/my_engine.py` with a single focused function
2. Import and call it in `main.py` within `run_quant_model()`
3. Add the result key to the return dict
4. Display in the relevant tab in `app.py`
5. Document any new settings in `config/settings.py`

### Add a new data source for options

1. Add a `_fetch_mysource(ticker, expiry)` function in `data/options_chain.py`
2. Add it as a fallback step in `_get_chain_with_fallback()` before the cache
3. Normalise output to the standard column schema (contractSymbol, strike, expiration, bid, ask, lastPrice, volume, openInterest, impliedVolatility, delta, gamma, theta, vega)

### Add a new universe

1. Add the ticker list to `config/market_universe.py`
2. Add the option to the `UNIVERSE_OPTIONS` list inside `_universe_controls()` in `app.py`
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
5. Add to all `st.selectbox` calls in `app.py`

---

*Generated from codebase analysis — c:\Users\shriy\quant_system\options*
