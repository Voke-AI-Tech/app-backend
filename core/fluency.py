def detect_pauses(segments: list, threshold: float = 0.6) -> list[tuple[float, float, float]]:
    pauses = []
    for i in range(1, len(segments)):
        gap = float(segments[i].start) - float(segments[i - 1].end)
        if gap > threshold:
            pauses.append((segments[i - 1].end, segments[i].start, gap))
    return pauses

def calculate_wpm(words: list[str], total_time_sec: float) -> float:
    if total_time_sec == 0:
        return 0.0
    return round(len(words) / (total_time_sec / 60.0), 2)

def fluency_score_f(wpm: float, pauses: list[tuple[float, float, float]], total_time_sec: float) -> float:
    ideal_wpm_min, ideal_wpm_max = 110, 160

    # WPM Score
    if wpm < ideal_wpm_min:
        wpm_score = wpm / ideal_wpm_min
    elif wpm > ideal_wpm_max:
        wpm_score = ideal_wpm_max / wpm
    else:
        wpm_score = 1.0

    # Pause Score
    if total_time_sec == 0:
        pause_score = 0.0
    else:
        long_pauses = len([p for p in pauses if p[2] > 1.0])
        pause_score = max(0.0, 1 - (long_pauses / (total_time_sec / 10)))

    fluency_score_value = round((wpm_score * 0.6 + pause_score * 0.4) * 100, 2)
    return fluency_score_value

def compute_wpm_over_time(segments: list, total_time: float, window_size: float = 2.0) -> tuple[list[float], list[float]]:
    wpm_over_time = []
    time_points = []

    current_window_start = 0.0

    while current_window_start < total_time:
        current_window_end = current_window_start + window_size

        word_count = sum(
            1
            for seg in segments
            for word in seg.words
            if current_window_start <= float(word.start) < current_window_end
        )

        wpm = (word_count / window_size) * 60  # WPM in this window
        wpm_over_time.append(wpm)
        time_points.append(current_window_start + window_size / 2)

        current_window_start += window_size
    if not time_points: # Handle case where no time points are generated
        return [0.0], [0.0]
    return time_points, wpm_over_time
