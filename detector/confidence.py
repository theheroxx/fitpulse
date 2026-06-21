#detector/confidence.py
def calculate_confidence(score, reasons):
    """
    Confidence based on:
    - how extreme score is
    - how many rules triggered
    """

    base = 0.6

    if score > 80 or score < 20:
        base += 0.2

    if len(reasons) >= 3:
        base += 0.1

    return min(1.0, round(base, 2))