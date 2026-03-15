from data.options_chain import get_options_chain


def get_options_chain_for_volatility(ticker):
    """Thin wrapper — kept for backward compatibility."""
    return get_options_chain(ticker)
