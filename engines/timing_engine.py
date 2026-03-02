# engines/timing_engine.py

def timing_plan():
    """
    Returns structured timing rules
    """

    return {
        "entry": "Buy on 8-12% pullback from recent high OR near 50-day MA",
        "add": "Add on 15% correction if fundamentals unchanged",
        "exit": "Exit if 20% below entry OR intent flips to SELL"
    }