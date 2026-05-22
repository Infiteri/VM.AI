import re
import numpy as np

URGENT = {'urgent', 'asap', 'critical', 'deadline', 'important', 'immediately'}
HARD = {'hard', 'difficult', 'complex', 'tough', 'challenging', 'heavy', 'intense'}
EASY = {'easy', 'simple', 'quick', 'light', 'trivial', 'basic', 'gentle'}
TIME = {'minute', 'hour', 'day', 'week', 'month', 'today', 'tomorrow'}

def extract_features(texts):
    if isinstance(texts, str):
        texts = [texts]
    feats = []
    for t in texts:
        w = t.lower().split()
        n_chars = len(t)
        n_words = len(w)
        feats.append([
            n_words,
            n_chars,
            n_chars / max(n_words, 1),
            t.count('!'),
            sum(1 for c in t if c.isupper()),
            sum(1 for c in t if c.isupper()) / max(n_chars, 1),
            sum(1 for x in w if x in URGENT),
            sum(1 for x in w if x in HARD),
            sum(1 for x in w if x in EASY),
            sum(1 for x in w if x in TIME),
            int(bool(re.search(r'\d+', t))),
        ])
    return np.array(feats)
