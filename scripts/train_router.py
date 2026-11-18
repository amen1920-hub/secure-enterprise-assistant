import json
import re
from pathlib import Path

import joblib
import numpy as np
from langchain_ollama import OllamaEmbeddings
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "evaluation" / "routing_dataset.json"
MODELE = ROOT / "models" / "router.joblib"
ID = re.compile(r"\b[A-Za-z]{2,4}-\d{3}(?:-V1)?\b")
SEUILS = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9)

emb = OllamaEmbeddings(model="bge-m3")


def vecteurs(textes):
    sortie = []
    for i in range(0, len(textes), 64):
        sortie += emb.embed_documents(textes[i:i + 64])
        print(f"  embeddings : {min(i + 64, len(textes))}/{len(textes)}", end="\r")
    print()
    v = np.array(sortie, dtype=float)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def compter(jeu):
    return {c: sum(1 for x in jeu if x["classe"] == c)
            for c in ("permissions", "metadonnees", "recherche")}


def cascade(clf, X, textes, tau):
    """Applique les règles de la cascade : identifiant obligatoire pour 'metadonnees',
    et repli sur 'recherche' si la confiance est sous le seuil."""
    proba = clf.predict_proba(X)
    resultat = []
    for texte, ligne in zip(textes, proba):
        classe, confiance = clf.classes_[ligne.argmax()], ligne.max()
        if classe == "metadonnees" and not ID.search(texte):
            classe = "recherche"
        if confiance < tau:
            classe = "recherche"
        resultat.append(classe)
    return resultat


def rapport(nom, clf, X, jeu):
    textes = [x["texte"] for x in jeu]
    vrai = [x["classe"] for x in jeu]
    print(f"\n===== {nom} ({len(jeu)} questions) =====")
    print(f"{'seuil':>6} {'précision':>10} {'faux déclenchements d outil':>30}")
    for tau in SEUILS:
        pred = cascade(clf, X, textes, tau)
        juste = sum(p == v for p, v in zip(pred, vrai)) / len(vrai)
        faux = sum(1 for p, v in zip(pred, vrai) if v == "recherche" and p != "recherche")
        total = sum(1 for v in vrai if v == "recherche")
        print(f"{tau:>6} {juste:>10.1%} {faux:>14} sur {total} de contenu")
    pred = cascade(clf, X, textes, 0.0)
    print("\nDétail (seuil 0.0, avec la règle d'identifiant) :")
    print(classification_report(vrai, pred, zero_division=0))
    etiquettes = ["permissions", "metadonnees", "recherche"]
    print("Matrice de confusion (lignes = vrai, colonnes = prédit) :", etiquettes)
    print(confusion_matrix(vrai, pred, labels=etiquettes))
    erreurs = [(t, v, p) for t, v, p in zip(textes, vrai, pred) if v != p]
    if erreurs:
        print("\nErreurs :")
        for t, v, p in erreurs[:15]:
            print(f"  vrai={v:12} prédit={p:12} | {t}")


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    train, test, difficiles = data["train"], data["test"], data["difficiles"]
    print("Entraînement :", len(train), compter(train))
    print("Test         :", len(test), compter(test))
    print("Difficiles   :", len(difficiles), compter(difficiles))

    print("\nCalcul des embeddings...")
    X_train = vecteurs([x["texte"] for x in train])
    X_test = vecteurs([x["texte"] for x in test])
    X_diff = vecteurs([x["texte"] for x in difficiles])

    clf = LogisticRegression(max_iter=3000, C=10, class_weight="balanced")
    clf.fit(X_train, [x["classe"] for x in train])

    rapport("TEST généré", clf, X_test, test)
    rapport("DIFFICILES écrites à la main", clf, X_diff, difficiles)

    MODELE.parent.mkdir(exist_ok=True)
    joblib.dump(clf, MODELE)
    print(f"\nModèle enregistré : {MODELE}")


if __name__ == "__main__":
    main()