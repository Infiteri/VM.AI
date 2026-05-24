import os
import re

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(ROOT, "models", "regressors")
DIFF_PATH = os.path.join(MODELS_DIR, "difficulty_regressor.pkl")
IMP_PATH = os.path.join(MODELS_DIR, "importance_regressor.pkl")

URGENT = {'urgent', 'asap', 'critical', 'deadline', 'important', 'immediately'}
HARD = {'hard', 'difficult', 'complex', 'tough', 'challenging', 'heavy', 'intense'}
EASY = {'easy', 'simple', 'quick', 'light', 'trivial', 'basic', 'gentle'}
TIME = {'minute', 'hour', 'day', 'week', 'month', 'today', 'tomorrow'}


def extract_features(texts):
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


class RegressorPredictor:
    def __init__(self):
        self.encoder = SentenceTransformer('all-mpnet-base-v2')
        self.diff_model = joblib.load(DIFF_PATH)
        self.imp_model = joblib.load(IMP_PATH)

    def predict(self, text: str):
        if isinstance(text, str):
            text = [text]
        emb = self.encoder.encode(text, show_progress_bar=False)
        feats = extract_features(text)
        X = np.concatenate([emb, feats], axis=1)
        d = float(np.clip(self.diff_model.predict(X), 0, 1)[0])
        i = float(np.clip(self.imp_model.predict(X), 0, 1)[0])
        return d, i
