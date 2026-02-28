"""Shared utility functions for KF-KAFE Operations Platform."""


def fmt_inr(amount) -> str:
    """
    Format a number as Indian Rupee with proper comma grouping.
    Examples: 25 → ₹25 | 1500 → ₹1,500 | 125000 → ₹1,25,000 | 1250000 → ₹12,50,000
    """
    try:
        amount = int(float(amount))
    except (TypeError, ValueError):
        return "₹0"

    if amount < 0:
        return "-" + fmt_inr(-amount)

    s = str(amount)
    if len(s) <= 3:
        return f"₹{s}"

    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        if len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        else:
            groups.insert(0, rest)
            rest = ""
    return f"₹{','.join(groups)},{last3}"


def fmt_inr_float(amount, decimals: int = 2) -> str:
    """Format with decimal places: ₹1,25,000.50"""
    try:
        f = float(amount)
    except (TypeError, ValueError):
        return "₹0.00"
    int_part = fmt_inr(int(f))
    if decimals > 0:
        dec_str = f"{f:.{decimals}f}".split(".")[1]
        return f"{int_part}.{dec_str}"
    return int_part


CATEGORY_COLORS = {
    "Desi Teas":        "#F59E0B",
    "Desi Coffee":      "#92400E",
    "Water Based Teas": "#10B981",
    "Ice Coffee":       "#3B82F6",
    "Hot Coffee":       "#8B5CF6",
    "Cold Coffee":      "#2DD4BF",
    "Mocktails":        "#EC4899",
    "Milkshake":        "#F97316",
    "Natural Juices":   "#84CC16",
    "Fruit Juices":     "#06B6D4",
    "Fruit Bowl":       "#EAB308",
}

CATEGORY_ORDER = [
    "Desi Teas", "Desi Coffee", "Water Based Teas",
    "Ice Coffee", "Hot Coffee", "Cold Coffee",
    "Mocktails", "Milkshake", "Natural Juices",
    "Fruit Juices", "Fruit Bowl",
]
