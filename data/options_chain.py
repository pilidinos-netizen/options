import yfinance as yf

def get_options_chain(ticker):
    stock = yf.Ticker(ticker)
    expirations = stock.options
    if not expirations:
        return None
    chain = stock.option_chain(expirations[0])
    return chain.calls, chain.puts