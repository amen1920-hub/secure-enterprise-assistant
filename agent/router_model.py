import re
from pathlib import Path

import joblib
import numpy as np
from langchain_ollama import OllamaEmbeddings

ROOT = Path(__file__).resolve().parent.parent
MODELE = ROOT / "models" / "router.joblib"
SEUIL = 0.7
ID = re.compile(r"\b([A-Za-z]{2,4}-\d{3}(?:-V1)?)\b")

# Demande de lecture ou de résumé d'un document désigné par son identifiant.
RESUME_ID = re.compile(r"\b(r[ée]sum\w*|contenu|lire|lis|lecture)\b", re.IGNORECASE)
# Demande de résumé sans identifiant : on demande une précision.
RESUME = re.compile(r"\br[ée]sum\w*", re.IGNORECASE)

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
    m = ID.search(question)
    if m and RESUME_ID.search(question):
        return "document", m.group(1).upper(), 1.0
    if not m and RESUME.search(question):
        return "precision", "", 1.0
    try:
        clf, emb = _charger()
        v = np.array(emb.embed_query(question), dtype=float)
        v = (v / np.linalg.norm(v)).reshape(1, -1)
        proba = clf.predict_proba(v)[0]
    except Exception:
        return "recherche", "", 0.0
    classe, confiance = clf.classes_[proba.argmax()], float(proba.max())
    if classe == "metadonnees" and m and confiance >= SEUIL:
        return "metadonnees", m.group(1).upper(), confiance
    if classe == "permissions" and confiance >= SEUIL:
        return "permissions", "", confiance
    return "recherche", "", confiance