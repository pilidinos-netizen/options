import yfinance as yf

def get_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    return stock.info