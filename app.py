# app.py

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from main import run_quant_model
from engines.market_scanner import scan_market
from engines.performance_engine import compute_performance_metrics
from engines.options_opportunity_engine import rank_option_opportunities
from engines.options_contract_engine import select_leaps_contract
from engines.options_payoff_engine import calculate_call_payoff
from engines.news_engine import get_market_news
from engines.social_sentiment_engine import run_market_sentiment_engine


DEFAULT_UNIVERSE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL",
    "META","TSLA","AMD","NFLX","JPM"
]

@st.cache_data(ttl=600)
def load_reddit_sentiment():
    return run_market_sentiment_engine()
st.set_page_config(layout="wide")
st.title("📊 Intelligent Investment Research Platform")


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔎 Stock Analysis",
    "📈 Market Snapshot",
    "📊 Performance Dashboard",
    "🔥 Options Strategy",
    "📰 Market News"
])


# =================================================
# TAB 1 — STOCK ANALYSIS
# =================================================
with tab1:

    st.subheader("Single Stock Detailed Analysis")

    with st.expander("📘 What All These Terms Mean (Beginner Friendly Guide)"):

        st.markdown("""
        ### Intent
        This is the system's overall recommendation:
        - **Strong Buy** → Very positive outlook
        - **Buy** → Positive outlook
        - **Hold** → Neutral outlook
        - **Reduce** → Weakening outlook
        - **Sell** → Negative outlook

        ### Confidence (0–100)
        How strong the signal is. Higher number means stronger conviction.

        ### Volatility
        How much the stock price moves up and down in a year.
        High volatility = larger price swings.
        Low volatility = more stable price movement.

        ### Regime
        Current market condition based on model:
        - Bullish → Uptrend likely
        - Neutral → Sideways
        - Bearish → Downtrend risk

        ### Position Size (%)
        Suggested portion of your investment portfolio to allocate.
        Example: 10% means invest 10% of total capital.

        ### Monte Carlo Projection
        A statistical simulation estimating possible future price in one year.
        It does NOT guarantee returns, but gives probability-based outlook.
        """)

    ticker = st.text_input("Enter Stock Ticker Symbol (Example: NVDA)")
    profile = st.selectbox(
        "Select Your Risk Profile",
        ["Conservative","Balanced","Aggressive","Speculator"]
    )

    if st.button("Run Full Analysis"):
        result = run_quant_model(ticker.upper(), profile)
        st.json(result)


# =================================================
# TAB 2 — MARKET SNAPSHOT (Beginner Explanation Added)
# =================================================
with tab2:

    st.subheader("Market Snapshot – Compare Multiple Stocks")

    with st.expander("📘 What Market Snapshot Provides to a Beginner Investor"):

        st.markdown("""
        Market Snapshot helps you:

        • Compare multiple stocks side-by-side  
        • Identify which stock has stronger signals  
        • Understand volatility differences  
        • See which stocks may offer better opportunity  

        For a beginner investor, this helps answer:
        - Which stock looks stronger today?
        - Which stock is riskier?
        - Which stock has better growth signals?

        It acts like a quick comparison dashboard.
        """)

    tickers_input = st.text_area(
        "Enter Multiple Tickers (comma separated)",
        ",".join(DEFAULT_UNIVERSE)
    )

    if st.button("Generate Market Snapshot"):

        tickers = [t.strip().upper() for t in tickers_input.split(",")]
        results = scan_market(tickers, run_quant_model, "Balanced")

        st.dataframe(pd.DataFrame(results), use_container_width=True)


# =================================================
# TAB 3 — PERFORMANCE DASHBOARD
# =================================================
with tab3:

    st.subheader("Historical Performance Metrics")

    with st.expander("📘 Performance Terms Explained in Simple English"):

        st.markdown("""
        ### Total Return
        Overall gain or loss over the past 5 years.

        ### Annual Return
        Average yearly return.

        ### Annual Volatility
        Average yearly price fluctuation percentage.
        Higher means more risk.

        ### Sharpe Ratio
        Measures return compared to risk.
        Higher Sharpe = better reward for risk taken.

        ### Max Drawdown
        Largest drop from peak price historically.
        Shows worst historical loss period.
        """)

    perf_ticker = st.text_input("Ticker for Performance Review", "NVDA")

    if st.button("Analyze Performance"):
        metrics = compute_performance_metrics(perf_ticker.upper())
        st.json(metrics)


# =================================================
# TAB 4 — OPTIONS STRATEGY CENTER
# =================================================
# =================================================
# TAB 4 — OPTIONS STRATEGY CENTER
# =================================================
with tab4:

    st.subheader("Options Strategy Marketplace Scanner")

    with st.expander("📘 What This Section Does"):
        st.markdown("""
        This section scans multiple stocks and ranks the Top 10
        best option opportunities based on:

        • Model confidence strength  
        • Stock volatility (price movement potential)  
        • Liquidity (ease of trading options)  
        • Strategy alignment with market outlook  

        Higher Opportunity Score = Better overall setup.
        """)

    mode = st.radio(
        "Choose Mode",
        ["Top 10 Marketplace Opportunities", "Generate LEAPS Contract"],
        key="options_mode"
    )

    profile_opt = st.selectbox(
        "Risk Profile",
        ["Conservative","Balanced","Aggressive","Speculator"],
        key="options_profile"
    )

    # ---------------------------------------------
    # MODE 1 — TOP 10 MARKETPLACE OPTIONS
    # ---------------------------------------------
    if mode == "Top 10 Marketplace Opportunities":

        tickers_input = st.text_area(
            "Enter Tickers to Scan (comma separated)",
            ",".join(DEFAULT_UNIVERSE),
            key="options_tickers"
        )

        if st.button("Scan Marketplace for Top 10", key="scan_options"):

            tickers = [t.strip().upper() for t in tickers_input.split(",")]

            results = rank_option_opportunities(
                tickers,
                run_quant_model,
                profile_opt
            )

            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No valid option opportunities found.")

    # ---------------------------------------------
    # MODE 2 — LEAPS CONTRACT GENERATOR
    # ---------------------------------------------
    if mode == "Generate LEAPS Contract":

        opt_ticker = st.text_input("Ticker", "NVDA")

        if st.button("Generate LEAPS Contract"):

            contract = select_leaps_contract(opt_ticker.upper())
            st.json(contract)

            strike = contract["Strike"]
            premium = contract["Premium"]

            break_even = strike + premium
            st.write(f"Break-even Price: {round(break_even,2)}")

            price_range = np.linspace(strike * 0.5, strike * 1.8, 150)
            payoff = calculate_call_payoff(strike, premium, price_range)

            fig, ax = plt.subplots()
            ax.plot(price_range, payoff)
            ax.axhline(0)
            ax.set_title("Option Profit / Loss at Expiration")
            st.pyplot(fig)

# =================================================
# TAB 5 — MARKET NEWS
# =================================================
# =================================================
# TAB 5 — MARKET NEWS
# =================================================
with tab5:

    st.subheader("Market News & Impact Analysis")

    # Define ticker FIRST
    news_ticker = st.text_input("Ticker for News", "NVDA", key="news_input")

    # Then button
    if st.button("Fetch News", key="fetch_news_button"):

        news_data = get_market_news(news_ticker.upper())

        if "Error" in news_data:
            st.warning(news_data["Error"])
        else:
            st.write("### Company Ecosystem")
            st.write(f"Company: {news_data['Ecosystem']['company']}")
            st.write(f"Industry: {news_data['Ecosystem']['industry']}")
            st.write(f"Competitors: {', '.join(news_data['Ecosystem']['competitors'])}")
            st.write(f"Suppliers: {', '.join(news_data['Ecosystem']['suppliers'])}")

            st.write("### Summary")
            st.write(news_data["Summary"])

            st.write("### Sentiment")
            st.write(f"Sentiment Score: {news_data['Sentiment Score']}")
            st.write(f"Classification: {news_data['Sentiment Label']}")

            st.write("### Financial Announcements")
            if news_data["Impact Analysis"]:
                for k, v in news_data["Impact Analysis"].items():
                    st.write(f"**{k}:** {v}")

            st.write("### Articles")
            for article in news_data["Articles"]:
                st.markdown(f"**{article['Title']}**")
                st.write(f"Source: {article['Source']}")
                st.write(f"Published: {article['Published']}")
                if article["Announcements"]:
                    st.write(f"Detected Announcement: {', '.join(article['Announcements'])}")
                st.markdown(f"[Read Article]({article['Link']})")
                st.markdown("---")
with tab6:

    st.header("📊 Reddit Retail Sentiment Engine")

    st.caption("Analyzing Reddit discussions across investing communities")


    # Refresh button
    if st.button("🔄 Refresh Sentiment Data"):
        st.cache_data.clear()


    # Load data
    data = load_reddit_sentiment()


    # --------------------------------
    # Overall Market Sentiment
    # --------------------------------
    st.subheader("Overall Market Sentiment")

    sentiment_score = data.get("Market Sentiment Score", 0)

    if sentiment_score > 0.05:
        sentiment_label = "Bullish"
        st.success(f"Market Sentiment: {sentiment_label} ({sentiment_score})")

    elif sentiment_score < -0.05:
        sentiment_label = "Bearish"
        st.error(f"Market Sentiment: {sentiment_label} ({sentiment_score})")

    else:
        sentiment_label = "Neutral"
        st.warning(f"Market Sentiment: {sentiment_label} ({sentiment_score})")


    # --------------------------------
    # Ticker Sentiment Table
    # --------------------------------
    st.subheader("Ticker Sentiment Table")

    ticker_table = data.get("Ticker Sentiment Table", [])

    if ticker_table:

        df = pd.DataFrame(ticker_table)

        df.columns = [
            "Ticker",
            "Mentions",
            "Sentiment Score",
            "Sentiment"
        ]


        # Color formatting
        def color_sentiment(val):

            if val == "bullish":
                return "color: green"

            if val == "bearish":
                return "color: red"

            return "color: gray"


        styled_df = df.style.applymap(
            color_sentiment,
            subset=["Sentiment"]
        )

        st.dataframe(
            styled_df,
            use_container_width=True
        )

    else:
        st.info("No ticker sentiment detected.")


    # --------------------------------
    # Top Discussed Tickers
    # --------------------------------
    st.subheader("🔥 Most Discussed Tickers")

    top_tickers = data.get("Top Tickers", [])

    if top_tickers:

        top_df = pd.DataFrame(
            top_tickers,
            columns=["Ticker", "Mentions"]
        )

        st.dataframe(
            top_df,
            use_container_width=True
        )

    else:
        st.info("No ticker discussion detected.")


    # --------------------------------
    # Top Keywords
    # --------------------------------
    st.subheader("📊 Trending Market Themes")

    top_keywords = data.get("Top Keywords", [])

    if top_keywords:

        kw_df = pd.DataFrame(
            top_keywords,
            columns=["Keyword", "Mentions"]
        )

        st.dataframe(
            kw_df,
            use_container_width=True
        )

    else:
        st.info("No market themes detected.")


    # --------------------------------
    # Sample Posts
    # --------------------------------
    st.subheader("📰 Sample Market Posts")

    posts = data.get("Sample Posts", [])

    for post in posts:

        st.markdown(f"**{post['title']}**")

        st.write(f"Tickers: {', '.join(post['tickers']) if post['tickers'] else 'None'}")

        st.write(f"Keywords: {', '.join(post['keywords']) if post['keywords'] else 'None'}")

        st.write(f"Sentiment: {post['label']} ({post['sentiment']})")

        st.divider()
