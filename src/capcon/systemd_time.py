import re

SYSTEMD_TIME_UNITS = {
    "usec": 0.000001,
    "us": 0.000001,
    "μs": 0.000001,
    "msec": 0.001,
    "ms": 0.001,
    "seconds": 1,
    "second": 1,
    "sec": 1,
    "s": 1,
    "": 1,  # empty string defaults to seconds
    "minutes": 60,
    "minute": 60,
    "min": 60,
    "m": 60,
    "hours": 3600,
    "hour": 3600,
    "hr": 3600,
    "h": 3600,
    "days": 86400,
    "day": 86400,
    "d": 86400,
}

SYSTEMD_SPAN_RE = re.compile(r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Zμ]+)?")


def parse_systemd_timespan(timespan: str) -> float:
    total_seconds = 0.0

    # Check if the string is just a number (systemd defaults to seconds)
    if timespan.strip().isdigit():
        return float(timespan)

    matches = list(SYSTEMD_SPAN_RE.finditer(timespan))
    if not matches:
        raise ValueError(f"Invalid time span format: {timespan}")

    for match in matches:
        val = float(match.group("val"))
        unit = match.group("unit") or ""

        if unit not in SYSTEMD_TIME_UNITS:
            raise ValueError(f"Unknown time unit: '{unit}' in '{timespan}'")

        total_seconds += val * SYSTEMD_TIME_UNITS[unit]

    return total_seconds


# Systemd exact multipliers converted entirely to MICROSECONDS (int)
# This prevents floating-point rounding errors during division.
SYSTEMD_UNITS_DESC = [
    ("d", 86400000000),  # 24 * 3600 * 1_000_000
    ("h", 3600000000),  # 3600 * 1_000_000
    ("m", 60000000),  # 60 * 1_000_000
    ("s", 1000000),  # 1 * 1_000_000
    ("ms", 1000),  # 1000 microseconds in an ms
    ("us", 1),  # 1 microsecond
]


def format_systemd_timespan(seconds: float) -> str:
    if seconds == 0:
        return "0s"

    # Convert base seconds to total microseconds
    us_total = int(round(seconds * 1_000_000))
    parts = []

    # Greedily divide by the largest units first
    for unit_name, unit_us_value in SYSTEMD_UNITS_DESC:
        if us_total >= unit_us_value:
            # How many of this unit fit into the remaining time?
            count = us_total // unit_us_value
            # What is the remainder?
            us_total = us_total % unit_us_value

            parts.append(f"{count}{unit_name}")

    return " ".join(parts)
