import json
import re
import yaml
from pathlib import Path
from langchain_ollama import ChatOllama

MODEL = "qwen2.5:7b"
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"

A_VERSIONNER = ["RH-001", "RH-002", "IT-001", "IT-002",
                "FIN-001", "FIN-002", "JUR-001", "RHC-001"]

llm = ChatOllama(model=MODEL, temperature=0.3, format="json")


def chiffres(texte):
    return set(re.findall(r"\d+", texte))


def changer_nombre(fait):
    def remplacer(m):
        n = int(m.group())
        return str(n + max(1, n // 5))
    return re.sub(r"\d+", remplacer, fait, count=1)


def anciens_faits(doc):
    originaux = doc["faits_cles"]
    faits = "\n".join(f"- {f}" for f in originaux)
    prompt = f"""Voici les faits clés de la version actuelle (2026) du document « {doc['titre']} » :
{faits}

Écris les faits clés de l'ANCIENNE version (2025) du même document :
- même nombre de faits, même sujet, même ordre ;
- change les chiffres (durées, montants, pourcentages, seuils) de façon réaliste ;
- chaque fait contenant un chiffre doit avoir au moins un chiffre différent.

Réponds uniquement en JSON : {{"faits_cles": ["...", "..."]}}"""
    nouveaux = []
    for _ in range(3):
        try:
            data = json.loads(llm.invoke(prompt).content)["faits_cles"]
            nouveaux = [str(x) for x in data]
            if len(nouveaux) == len(originaux):
                break
        except Exception as e:
            print("  nouvel essai :", e)
    # Plan B : compléter ou tronquer, puis forcer un changement de chiffre
    nouveaux = (nouveaux + originaux)[: len(originaux)]
    for i, (a, n) in enumerate(zip(originaux, nouveaux)):
        if chiffres(a) and chiffres(a) == chiffres(n):
            nouveaux[i] = changer_nombre(n)
    return nouveaux


def mettre_a_jour_entete(doc_id):
    fichier = RAW / f"{doc_id}.md"
    if fichier.exists():
        t = fichier.read_text(encoding="utf-8")
        t = re.sub(r'^version: ".*"$', 'version: "2.0"', t, count=1, flags=re.M)
        fichier.write_text(t, encoding="utf-8")


def main():
    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    ids = {d["id"] for d in docs}
    resultat = []
    for d in docs:
        resultat.append(d)
        if d["id"] not in A_VERSIONNER:
            continue
        ancien_id = f"{d['id']}-V1"
        if ancien_id in ids:
            print(f"{d['id']} : déjà versionné, ignoré")
            continue
        print(f"{d['id']} : création de la version 1.0")
        d["version"] = "2.0"
        d["statut"] = "actuelle"
        d["famille"] = d["id"]
        resultat.append({
            "id": ancien_id,
            "titre": d["titre"],
            "departement": d["departement"],
            "confidentialite": d["confidentialite"],
            "roles_autorises": d["roles_autorises"],
            "version": "1.0",
            "date": "2025-01-15",
            "statut": "obsolete",
            "famille": d["id"],
            "faits_cles": anciens_faits(d),
        })
        mettre_a_jour_entete(d["id"])
    MANIFEST.write_text(
        yaml.dump({"documents": resultat}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Manifeste mis à jour : {len(resultat)} documents")


if __name__ == "__main__":
    main()