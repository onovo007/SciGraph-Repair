"""Original, deliberately small epidemiologic indicator calculations for a controlled study.

No real patient records or third-party repository code is included.
"""

def vaccine_coverage(vaccinated, eligible):
    """Proportion eligible receiving a vaccine."""
    return vaccinated / eligible

def dropout_rate(first_dose, final_dose):
    """DTP1-to-DTP3 dropout ratio."""
    return (first_dose - final_dose) / first_dose

def incidence_per_100k(cases, population):
    """Cases per one hundred thousand population."""
    return cases / population * 100000

def rolling_mean_past(values, window):
    """Trailing mean uses current and historical periods only."""
    out = []
    for i in range(len(values)):
        window_values = values[max(0, i - window + 1):i + 1]
        out.append(sum(window_values) / len(window_values))
    return out

def weighted_rate(group_counts):
    """Pooled rate from (events, population) pairs, not mean of stratum rates."""
    return sum(n for n, d in group_counts) / sum(d for n, d in group_counts)

def deduplicate_records(records):
    """Keep first record for each person identifier."""
    seen = set()
    output = []
    for rec in records:
        if rec['id'] not in seen:
            seen.add(rec['id'])
            output.append(rec)
    return output

def positivity_rate(positive, tested):
    """Positive laboratory results over all people tested."""
    return positive / tested

def cumulative_cases(values):
    """Cumulative sum, preserving time order."""
    result = []
    total = 0
    for x in values:
        total += x
        result.append(total)
    return result
