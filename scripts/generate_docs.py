import argparse
import re
import time
import yaml
from pathlib import Path
from langchain_ollama import ChatOllama

MODEL = "qwen2.5:7b"
GENERATION = "2"
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"

llm = ChatOllama(model=MODEL, temperature=0.3)


def construire_prompt(doc):
    faits = "\n".join(f"- {f}" for f in doc["faits_cles"])
    return f"""Tu rédiges un document interne officiel de l'entreprise fictive NovaTech Solutions (services numériques, siège à Tunis, monnaie : dinar tunisien, TND).

DOCUMENT À RÉDIGER :
- Titre : {doc['titre']}
- Département : {doc['departement']}
- Version : {doc['version']} (date : {doc['date']})

FAITS CLÉS À INTÉGRER TELS QUELS (mêmes chiffres, même formulation) :
{faits}

CONSIGNES :
- Écris en français, sans mots anglais, dans un ton formel et professionnel.
- Structure : 4 à 6 sections numérotées (## 1. ..., ## 2. ...), toutes en rapport direct avec le titre du document.
- Longueur : 200 à 400 mots.
- Intègre tous les faits clés sans en modifier les chiffres.
- Écris tous les nombres en chiffres (par exemple 12, 30 ou 100%), jamais en toutes lettres comme « douze », « trente » ou « cent pour cent ».
- N'invente AUCUN chiffre, pourcentage, montant, délai ou date qui ne figure pas dans les faits clés.
- Ne traite aucun autre sujet que celui du titre : pas de section sur le télétravail, les mots de passe, les horaires, les rôles d'accès ou les règles générales de l'entreprise, sauf si le titre du document l'exige.
- Si tu mentionnes la version ou la date, écris exactement : version {doc['version']}, date {doc['date']}.
- Commence directement par la première section (pas de titre principal, pas d'introduction du type « Voici le document »).
"""


def nettoyer(corps):
    corps = corps.strip()
    # Retire un éventuel titre principal « # ... » écrit par le modèle.
    while corps.startswith("# "):
        corps = corps.split("\n", 1)[1].lstrip() if "\n" in corps else ""
    return corps.strip()


def a_jour(fichier):
    if not fichier.exists():
        return False
    return f'generation: "{GENERATION}"' in fichier.read_text(encoding="utf-8")[:600]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Nombre maximum de documents à générer")
    parser.add_argument("--ids", nargs="*", default=None,
                        help="Régénère uniquement ces identifiants")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    if args.ids:
        a_generer = [d for d in docs if d["id"] in args.ids]
    else:
        a_generer = [d for d in docs if not a_jour(RAW / f"{d['id']}.md")]
    if args.limit:
        a_generer = a_generer[: args.limit]

    print(f"{len(a_generer)} document(s) à générer sur {len(docs)}")
    for i, doc in enumerate(a_generer, start=1):
        debut = time.time()
        corps = nettoyer(llm.invoke(construire_prompt(doc)).content)
        entete = (
            f"---\n"
            f"id: {doc['id']}\n"
            f"titre: {doc['titre']}\n"
            f"departement: {doc['departement']}\n"
            f"version: \"{doc['version']}\"\n"
            f"date: \"{doc['date']}\"\n"
            f"generation: \"{GENERATION}\"\n"
            f"---\n\n"
            f"# {doc['titre']}\n\n"
        )
        (RAW / f"{doc['id']}.md").write_text(entete + corps + "\n", encoding="utf-8")
        print(f"[{i}/{len(a_generer)}] {doc['id']} : {doc['titre']} ({time.time() - debut:.0f} s)")
    print("Terminé.")


if __name__ == "__main__":
    main()