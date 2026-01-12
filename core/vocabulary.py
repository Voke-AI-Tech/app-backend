import nltk
from lexical_diversity import lex_div as ld

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

cefr_wordlist = {
    'A1': set([
        'about', 'above', 'actor', 'apple', 'area', 'arm', 'ask', 'at', 'aunt', 'away'
    ]),
    'A2': set([
        'ability', 'accept', 'accident', 'adult', 'advice', 'afraid', 'airplane', 'allow'
    ]),
    'B1': set([
        'absolutely', 'academic', 'according', 'achieve', 'act', 'active', 'actual', 'addition'
    ]),
    'B2': set([
        'abandon', 'abstract', 'academic', 'access', 'accurate', 'adapt', 'adjust', 'advocate'
    ]),
    'C1': set([]),
    'C2': set([])
}

def vocabulary_score(text: str) -> float:
    tokens = nltk.word_tokenize(text.lower())
    if not tokens:
        return 0.0
    ttr_score = round(ld.ttr(tokens) * 100, 2)

    advanced_words = [word for word in tokens if word in cefr_wordlist.get('C1', []) or word in cefr_wordlist.get('C2', [])]
    bonus = min(10, len(set(advanced_words)))

    vocab_score_value = min(100, ttr_score + bonus)
    return vocab_score_value
