import io
import os
import shutil

async def live_conversation_pipeline(name: str, session: dict):
    """Evaluate the full Live conversation after the session ends.

    Audio chunks from each turn are stored as individual valid WAV files.
    We concatenate them via pydub so the combined buffer is a valid audio file.
    """
    from core.speech_eval import extract_word_and_text, analyze_pauses_for_fillers, advanced_filler_analysis
    from core.grammar import grammar_score
    from core.vocabulary import vocabulary_score
    from core.fluency import fluency_score_f, compute_wpm_over_time
    from core.pronunciation import extract_word_audio_clips, pronunciation_score_f, find_mispronounced_words, WORD_CLIPS_TEMP_DIR
    from core.scoring import overall_score_f, cefr_score
    from services.llm import improve_fluency_by_line, generate_report_summary_text
    from services.visualization import plot_pentagon, plot_fluency_curve
    from reports.pdf_generator import generate_report
    from pydub import AudioSegment

    segments = session["segments_all"]
    if not segments:
        return None

    # Concatenate audio chunks into one valid AudioSegment, then export to a buffer
    combined_segment = None
    for chunk_bytes in session["audio_chunks"]:
        seg = AudioSegment.from_file(io.BytesIO(chunk_bytes))
        combined_segment = seg if combined_segment is None else combined_segment + seg

    if combined_segment is None:
        return None

    combined_buffer = io.BytesIO()
    combined_segment.export(combined_buffer, format="wav")
    combined_audio_bytes = combined_buffer.getvalue()

    words, full_text = extract_word_and_text(segments)
    duration_seconds = segments[-1].end if segments else 0

    silent_pauses, vocalized_fillers = analyze_pauses_for_fillers(io.BytesIO(combined_audio_bytes), segments)
    wpm = (len(words) / (duration_seconds / 60.0)) if duration_seconds > 0 else 0

    filler_data, filler_percent = advanced_filler_analysis(full_text, vocalized_fillers)

    grammar_errs, grammar_score_val = grammar_score(full_text)
    vocab_score = vocabulary_score(full_text)
    fluency_score = fluency_score_f(wpm, silent_pauses, duration_seconds)

    clips = extract_word_audio_clips(io.BytesIO(combined_audio_bytes), segments)
    pronunciation_score = pronunciation_score_f(clips)

    overall_score = overall_score_f(grammar_score_val, vocab_score, fluency_score, pronunciation_score, filler_percent)
    filler_score = int(filler_percent)

    overall_cefr = cefr_score(overall_score)
    grammar_cefr = cefr_score(grammar_score_val)
    vocab_cefr = cefr_score(vocab_score)
    fluency_cefr = cefr_score(fluency_score)
    pronunciation_cefr = cefr_score(pronunciation_score)
    filler_cefr = cefr_score(filler_score)

    segments_dict = [{"text": getattr(seg, "text", "")} for seg in segments]
    improved_lines = improve_fluency_by_line(segments_dict)

    mispronounced = find_mispronounced_words(clips)

    pentagon_plot_base64 = plot_pentagon([
        grammar_score_val,
        vocab_score,
        fluency_score,
        pronunciation_score,
        max(0, 100 - filler_percent)
    ])

    time_points, wpm_values = compute_wpm_over_time(segments, total_time=duration_seconds)
    fluency_plot_base64 = plot_fluency_curve(time_points, wpm_values)

    summary_points = generate_report_summary_text(
        transcript=full_text,
        overall_score=overall_score,
        grammar_score=grammar_score_val,
        vocabulary_score=vocab_score,
        fluency_score=fluency_score,
        pronunciation_score=pronunciation_score,
        filler_word_score=filler_score
    )

    summary_html = "<ul>" + "".join(f"<li>{p}</li>" for p in summary_points) + "</ul>"

    pdf_bytes_io, pdf_filename = await generate_report(
        name,
        grammar_score_val, grammar_cefr,
        vocab_score, vocab_cefr,
        fluency_score, fluency_cefr,
        pronunciation_score, pronunciation_cefr,
        overall_score, overall_cefr,
        filler_score, filler_cefr,
        pentagon_plot_base64, fluency_plot_base64,
        summary_html
    )

    fluency_over_time = [
        {"time": t, "wpm": w}
        for t, w in zip(time_points, wpm_values)
    ]

    try:
        return {
            "pdf_bytes_io": pdf_bytes_io,
            "pdf_filename": pdf_filename,
            "overall_score": overall_score,
            "grammar_score": grammar_score_val,
            "vocabulary_score": vocab_score,
            "fluency_score": fluency_score,
            "pronunciation_score": pronunciation_score,
            "filler_score": filler_score,
            "improved_lines": improved_lines,
            "mispronounced_words": mispronounced,
            "summary_points": summary_points,
            "words_per_minute": round(wpm, 1),
            "word_count": len(words),
            "pause_count": len(silent_pauses),
            "filler_words_data": filler_data,
            "fluency_over_time": fluency_over_time,
            "full_text": full_text,
        }
    finally:
        if os.path.exists(WORD_CLIPS_TEMP_DIR):
            try:
                shutil.rmtree(WORD_CLIPS_TEMP_DIR)
            except Exception as e:
                print(f"Error cleaning up word clips: {e}")
