def grammar_score(text: str) -> tuple[int, float]:
    import language_tool_python
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    grammar_errors = len(matches)
    num_sentences = max(1, text.count('.') + text.count('!') + text.count('?'))
    error_rate = grammar_errors / num_sentences
    grammar_score_value = max(0, 100 - error_rate * 20)  # Tunable scaling
    return grammar_errors, round(grammar_score_value, 2)
