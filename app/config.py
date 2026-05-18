"""Tier classification thresholds for goals/tripwires.

Tier is informational only (badge in the UI) and is NEVER stored in the
database — `Goal.tier` and `TripWire.tier` are `@property` calls into
`classify_tier`. Adjusting these thresholds takes effect immediately
without a migration.
"""

TIER_THRESHOLDS = {
    "Short": (1, 7),
    "Medium": (8, 90),
    "Long": (91, None),
}


def classify_tier(start_date, end_date):
    if start_date is None or end_date is None:
        return "Unknown"
    duration = (end_date - start_date).days
    for tier, (low, high) in TIER_THRESHOLDS.items():
        if duration >= low and (high is None or duration <= high):
            return tier
    return "Unknown"
