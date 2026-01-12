def overall_score_f(grammar: float, vocab: float, fluency: float, pronunciation: float, filler_percent: float) -> float:
    filler_penalty = max(0, 100 - filler_percent)
    return round((grammar + vocab + fluency + pronunciation + filler_penalty) / 5.0, 2)

def cefr_score(overall: float) -> str:
    overall_int = int(overall)
    if overall_int < 20: return 'A1'
    elif overall_int < 40: return 'A2'
    elif overall_int < 55: return 'B1'
    elif overall_int < 70: return 'B2'
    elif overall_int < 85: return 'C1'
    else: return 'C2'
