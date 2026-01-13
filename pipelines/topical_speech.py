import os
import shutil
import io

async def topical_speech_pipeline(name: str, audio_path: str, segments: list, duration_seconds: float):
    from core.speech_eval import extract_word_and_text, analyze_pauses_for_fillers, advanced_filler_analysis
    from core.grammar import grammar_score
    from core.vocabulary import vocabulary_score
    from core.fluency import fluency_score_f, compute_wpm_over_time
    from core.pronunciation import extract_word_audio_clips, pronunciation_score_f, find_mispronounced_words, WORD_CLIPS_TEMP_DIR
    from core.scoring import overall_score_f, cefr_score
    from services.llm import improve_fluency_by_line, generate_report_summary_text
    from services.visualization import plot_pentagon, plot_fluency_curve
    from reports.pdf_generator import generate_report

    words, full_text = extract_word_and_text(segments)

    # Read audio content once into an in-memory buffer
    with open(audio_path, "rb") as f:
        audio_content = f.read()
    
    # Pass separate BytesIO objects to avoid state sharing/interference
    silent_pauses, vocalized_fillers = analyze_pauses_for_fillers(io.BytesIO(audio_content), segments)
    wpm = (len(words) / (segments[-1].end / 60.0)) if segments and segments[-1].end > 0 else 0
    
    filler_data, filler_percent = advanced_filler_analysis(full_text, vocalized_fillers)

    grammar_errs, grammar_score_val = grammar_score(full_text)
    vocab_score = vocabulary_score(full_text)
    fluency_score = fluency_score_f(wpm, silent_pauses, duration_seconds)
    
    clips = extract_word_audio_clips(io.BytesIO(audio_content), segments)
    pronunciation_score = pronunciation_score_f(clips)
    
    overall_score = overall_score_f(grammar_score_val, vocab_score, fluency_score, pronunciation_score, filler_percent)
    filler_score = int(filler_percent)

    overall_cefr = cefr_score(overall_score)
    grammer_cefr = cefr_score(grammar_score_val)
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
        grammar_score_val, grammer_cefr,
        vocab_score, vocab_cefr,
        fluency_score, fluency_cefr,
        pronunciation_score, pronunciation_cefr,
        overall_score, overall_cefr,
        filler_score, filler_cefr,
        pentagon_plot_base64, fluency_plot_base64,
        summary_html
    )
    
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
            "summary_points": summary_points
        }
    finally:
        # Clean up the word_clips directory
        if os.path.exists(WORD_CLIPS_TEMP_DIR):
            try:
                shutil.rmtree(WORD_CLIPS_TEMP_DIR)
            except Exception as e:
                print(f"Error cleaning up word clips: {e}")
