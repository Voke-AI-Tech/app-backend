import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

# Ensure required NLTK data is available
for resource in ['punkt', 'punkt_tab', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng']:
    try:
        nltk.data.find(f'tokenizers/{resource}' if 'punkt' in resource else f'taggers/{resource}')
    except LookupError:
        nltk.download(resource, quiet=True)


# Common grammar error patterns (regex-based heuristics)
_ERROR_PATTERNS = [
    # Subject-verb agreement
    (r'\b(I|we|they|you)\s+(is|was|has)\b', 'subject-verb agreement'),
    (r'\b(he|she|it)\s+(are|were|have)\b', 'subject-verb agreement'),
    (r'\b(everybody|everyone|nobody|someone|anyone)\s+(are|were|have)\b', 'subject-verb agreement'),
    # Double negatives
    (r"\b(don't|doesn't|didn't|won't|can't|couldn't|wouldn't|shouldn't)\s+\w*\s*\b(no|nothing|nobody|nowhere|neither)\b", 'double negative'),
    # Repeated words
    (r'\b(\w+)\s+\1\b', 'repeated word'),
    # a/an misuse
    (r'\ba\s+[aeiouAEIOU]\w+', 'a/an misuse'),
    (r'\ban\s+[^aeiouAEIOU\s]\w+', 'a/an misuse'),
    # Common confused words
    (r'\btheir\s+(is|was|are|were)\b', 'confused word (their/there)'),
    (r'\byour\s+(is|was|are|were|welcome)\b', 'confused word (your/you\'re)'),
    (r'\bits\s+(a\s+)?(is|was|are|were)\b', 'confused word (its/it\'s)'),
    # Missing verb after subject pronouns
    (r'\b(I|he|she|we|they)\s+(very|really|also|never|always|often)\s+(very|really|also|never|always|often)\b', 'missing verb'),
    # Incorrect past tense
    (r'\bdid\s+\w+ed\b', 'incorrect past tense after did'),
    # Double comparatives/superlatives
    (r'\bmore\s+\w+er\b', 'double comparative'),
    (r'\bmost\s+\w+est\b', 'double superlative'),
]

_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), desc) for p, desc in _ERROR_PATTERNS]


def _count_pattern_errors(text: str) -> int:
    """Count grammar errors detected by regex patterns."""
    error_count = 0
    for pattern, _ in _COMPILED_PATTERNS:
        matches = pattern.findall(text)
        error_count += len(matches)
    return error_count


def _check_sentence_structure(sentences: list[str]) -> int:
    """Check for basic sentence structure issues using POS tagging."""
    errors = 0
    for sent in sentences:
        words = word_tokenize(sent)
        if len(words) < 2:
            continue
        try:
            tagged = nltk.pos_tag(words)
        except Exception:
            continue

        # Check if sentence has at least one verb
        pos_tags = [tag for _, tag in tagged]
        verb_tags = {'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'MD'}
        has_verb = any(tag in verb_tags for tag in pos_tags)

        # Check if sentence has at least one noun or pronoun
        noun_tags = {'NN', 'NNS', 'NNP', 'NNPS', 'PRP', 'PRP$', 'WP'}
        has_noun = any(tag in noun_tags for tag in pos_tags)

        if not has_verb and len(words) > 3:
            errors += 1
        if not has_noun and len(words) > 3:
            errors += 1

    return errors


def grammar_score(text: str) -> tuple[int, float]:
    """Score grammar using nltk-based heuristic analysis.

    Returns (error_count, score) where score is 0-100.
    """
    if not text or not text.strip():
        return 0, 100.0

    sentences = sent_tokenize(text)
    num_sentences = max(1, len(sentences))

    # Count errors from regex patterns
    pattern_errors = _count_pattern_errors(text)

    # Count errors from sentence structure analysis
    structure_errors = _check_sentence_structure(sentences)

    total_errors = pattern_errors + structure_errors
    error_rate = total_errors / num_sentences
    grammar_score_value = max(0, 100 - error_rate * 20)  # Same tunable scaling as before
    return total_errors, round(grammar_score_value, 2)
