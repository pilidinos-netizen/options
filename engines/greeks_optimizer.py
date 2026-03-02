def optimize_by_delta(options_df, min_delta, max_delta):
    return options_df[
        (options_df["delta"] >= min_delta) &
        (options_df["delta"] <= max_delta)
    ]