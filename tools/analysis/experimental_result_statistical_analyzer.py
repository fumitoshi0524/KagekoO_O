"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze experimental measurements."""
    import json
    import math
    import statistics

    try:
        data = json.loads(payload)
        values = data.get("values")
        if not values or not isinstance(values, list) or len(values) < 2:
            return json.dumps({"error": "'values' must be a list of at least 2 numbers."})
        if not all(isinstance(v, (int, float)) for v in values):
            return json.dumps({"error": "All elements in 'values' must be numbers."})

        hypothesized_mean = data.get("hypothesized_mean")
        digits = data.get("digits", 4)
        if not isinstance(digits, int) or digits < 0:
            return json.dumps({"error": "'digits' must be a non-negative integer."})

        n = len(values)
        mean = statistics.mean(values)
        median = statistics.median(values)
        stdev = statistics.stdev(values)
        min_val = min(values)
        max_val = max(values)
        q1 = statistics.median_low(sorted(values)[:n//2]) if n % 2 == 0 else statistics.median_low(sorted(values)[:n//2])
        q3 = statistics.median_high(sorted(values)[n//2:]) if n % 2 == 0 else statistics.median_high(sorted(values)[n//2+1:])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = [v for v in values if v < lower_bound or v > upper_bound]

        result = {
            "sample_size": n,
            "mean": round(mean, digits),
            "median": round(median, digits),
            "standard_deviation": round(stdev, digits),
            "minimum": round(min_val, digits),
            "maximum": round(max_val, digits),
            "q1": round(q1, digits),
            "q3": round(q3, digits),
            "iqr": round(iqr, digits),
            "outliers": [round(v, digits) for v in outliers],
            "outlier_count": len(outliers)
        }

        if hypothesized_mean is not None:
            if not isinstance(hypothesized_mean, (int, float)):
                return json.dumps({"error": "'hypothesized_mean' must be a number."})
            t_statistic = (mean - hypothesized_mean) / (stdev / math.sqrt(n))
            degrees_freedom = n - 1
            # approximate p-value using t-distribution (two-tailed)
            p_value = 2 * (1 - _t_cdf(abs(t_statistic), degrees_freedom))
            result["t_test"] = {
                "hypothesized_mean": round(hypothesized_mean, digits),
                "t_statistic": round(t_statistic, digits),
                "degrees_of_freedom": degrees_freedom,
                "p_value": round(p_value, 10),
                "significant_at_0.05": p_value < 0.05
            }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


def _t_cdf(t, df):
    """Approximate cumulative distribution function for Student's t-distribution."""
    import math
    x = df / (t**2 + df)
    # using regularized incomplete beta function approximation
    a = df / 2.0
    b = 0.5
    return 1 - 0.5 * _betainc(a, b, x)


def _betainc(a, b, x):
    """Compute regularized incomplete beta function via continued fraction."""
    import math
    if x == 0 or x == 1:
        return 0.0
    # use Lentz's continued fraction method
    # simplified approximation: use series expansion for small x, else use symmetry
    if x < (a + 1) / (a + b + 2):
        return _betainc_series(a, b, x)
    else:
        return 1 - _betainc_series(b, a, 1 - x)


def _betainc_series(a, b, x):
    """Series expansion for incomplete beta function."""
    import math
    # compute using log beta
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    # first term
    result = 0.0
    term = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) / a
    result += term
    for k in range(1, 1000):
        term *= (a + b + k - 1) * x / (a + k)
        result += term
        if abs(term) < 1e-12 * abs(result):
            break
    return result


TOOL_SPEC = {
    "name": "experimental_result_statistical_analyzer",
    "description": "Analyze sets of experimental measurements (e.g., repeated trials, sensor readings, assay results) to compute descriptive statistics (mean, median, standard deviation, min/max, quartiles), detect outliers using the IQR method, and optionally perform a one-sample t-test against a hypothesized population mean to assess statistical significance.",
    "category": "analysis",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "values": {
            "type": "array",
            "description": "Array of numeric experimental measurements (must contain at least 2 values).",
            "items": {
                "type": "number"
            },
            "minItems": 2
        },
        "hypothesized_mean": {
            "type": "number",
            "description": "Optional: A hypothesized population mean for the one-sample t-test. If omitted, the t-test is not performed."
        },
        "digits": {
            "type": "integer",
            "description": "Optional: Number of decimal places for rounding results (must be >= 0, default 4).",
            "default": 4,
            "minimum": 0
        }
    },
    "required": [
        "values"
    ]
},
}
