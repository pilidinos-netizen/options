import requests

def get_price_polygon(ticker, api_key):
    url = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={api_key}"
    r = requests.get(url)
    return r.json()