def scan_market(tickers, run_model, profile):
    results = []

    for t in tickers:
        try:
            result = run_model(t, profile)
            results.append((t, result["Confidence"]))
        except:
            continue

    return sorted(results, key=lambda x: x[1], reverse=True)