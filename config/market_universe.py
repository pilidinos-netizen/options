# config/market_universe.py
# Curated ticker universes for broad market scanning.

SP100 = [
    "AAPL","ABBV","ABT","ACN","ADBE","AIG","ALL","AMGN","AMT","AMZN",
    "AXP","BA","BAC","BIIB","BK","BKNG","BLK","BMY","C","CAT",
    "CHTR","CL","CMCSA","COF","COP","COST","CRM","CSCO","CVS","CVX",
    "D","DHR","DIS","DUK","EMR","EXC","F","FDX","GD","GE",
    "GILD","GM","GOOGL","GS","HD","HON","IBM","INTC","JNJ","JPM",
    "KHC","KO","LIN","LLY","LMT","LOW","MA","MCD","MDLZ","MDT",
    "MET","META","MMM","MO","MRK","MS","MSFT","NEE","NFLX","NKE",
    "NVDA","ORCL","OXY","PEP","PFE","PG","PM","PYPL","QCOM","RTX",
    "SBUX","SCHW","SO","SPG","T","TGT","TJX","TMO","TSLA","TXN",
    "UNH","UNP","UPS","USB","V","VZ","WFC","WMT","XOM","AMD",
]

NASDAQ100 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","COST","NFLX",
    "AMD","ADBE","CSCO","INTC","QCOM","TXN","INTU","AMGN","SBUX","BKNG",
    "MDLZ","GILD","ADI","REGN","VRTX","PANW","KLAC","SNPS","CDNS","MRVL",
    "AMAT","LRCX","ASML","ABNB","FTNT","MELI","DXCM","FAST","CTAS","ODFL",
    "CPRT","IDXX","ROST","BIIB","VRSK","ANSS","PYPL","ADP","PCAR","CHTR",
    "ILMN","NXPI","MNST","DLTR","PAYX","ORLY","EA","WDAY","ZS","CRWD",
    "TEAM","TTD","DDOG","MDB","SNOW","COIN","PLTR","ARM","AXON","GEHC",
    "ON","CEG","AZN","PDD","SGEN","BMRN","ALGN","ENPH","FANG","LULU",
    "KDP","TTWO","WBD","LCID","ZM","DOCU","RIVN","OKTA","SPLK","NET",
    "DASH","RBLX","LYFT","UBER","ABNB","HOOD","SOFI","OPEN","SPCE","IONQ",
]

SECTORS = {
    "Technology": [
        "AAPL","MSFT","NVDA","GOOGL","META","TSLA","AMD","ADBE","CRM","ORCL",
        "CSCO","INTC","QCOM","TXN","IBM","ACN","AVGO","PANW","CRWD","ZS",
        "PLTR","SNOW","DDOG","NET","WDAY","NOW","INTU","TEAM","MDB","FTNT",
    ],
    "Financials": [
        "JPM","BAC","WFC","GS","MS","C","AXP","COF","BLK","USB",
        "BK","SCHW","MET","AIG","ALL","V","MA","PYPL","COIN","HOOD",
    ],
    "Healthcare": [
        "JNJ","UNH","PFE","ABBV","MRK","ABT","LLY","BMY","DHR","GILD",
        "BIIB","MDT","TMO","CVS","REGN","VRTX","AMGN","ILMN","IDXX","DXCM",
    ],
    "Energy": [
        "XOM","CVX","COP","OXY","SLB","MPC","PSX","VLO","PXD","EOG",
        "KMI","WMB","OKE","HAL","BKR","DVN","FANG","APA","MRO","HES",
    ],
    "Consumer": [
        "AMZN","HD","WMT","COST","TGT","MCD","SBUX","NKE","PG","KO",
        "PEP","CL","MO","PM","KHC","MDLZ","BKNG","ABNB","UBER","DASH",
    ],
    "Industrials": [
        "BA","CAT","HON","GE","GD","LMT","RTX","UNP","UPS","FDX",
        "EMR","MMM","DE","ETN","ROK","PH","AME","GWW","FAST","CTAS",
    ],
    "Utilities & Telecom": [
        "NEE","DUK","SO","D","EXC","AEP","XEL","PCG","SRE","ED",
        "T","VZ","CMCSA","CHTR","TMUS","DISH","LUMN","PARA","WBD","DIS",
    ],
}

# All unique tickers across SP100 + NASDAQ100
BROAD_MARKET = sorted(set(SP100 + NASDAQ100))
