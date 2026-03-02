import yfinance as yf

def backtest(ticker):
    data = yf.download(ticker, period="5y")
    data["MA50"] = data["Close"].rolling(50).mean()
    data["Signal"] = data["Close"] > data["MA50"]
    returns = data["Close"].pct_change()
    strategy = returns * data["Signal"].shift(1)
    return (1 + strategy).cumprod()