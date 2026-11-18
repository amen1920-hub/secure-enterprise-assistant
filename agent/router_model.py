import re
from pathlib import Path

import joblib
import numpy as np
from langchain_ollama import OllamaEmbeddings

ROOT = Path(__file__).resolve().parent.parent
MODELE = ROOT / "models" / "router.joblib"
SEUIL = 0.7
ID = re.compile(r"\b([A-Za-z]{2,4}-\d{3}(?:-V1)?)\b")

_clf = None
_emb = None


def _charger():
    global _clf, _emb
    if _clf is None:
        _clf = joblib.load(MODELE)
        _emb = OllamaEmbeddings(model="bge-m3")
    return _clf, _emb


def decider(question):
    """Renvoie (route, doc_id, confiance). Dans le doute : recherche."""
    try:
        clf, emb = _charger()
        v = np.array(emb.embed_query(question), dtype=float)
        v = (v / np.linalg.norm(v)).reshape(1, -1)
        proba = clf.predict_proba(v)[0]
    except Exception:
        return "recherche", "", 0.0
    classe, confiance = clf.classes_[proba.argmax()], float(proba.max())
    m = ID.search(question)
    if classe == "metadonnees" and m and confiance >= SEUIL:
        return "metadonnees", m.group(1).upper(), confiance
    if classe == "permissions" and confiance >= SEUIL:
        return "permissions", "", confiance
    return "recherche", "", confiance