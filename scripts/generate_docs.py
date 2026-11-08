import argparse
import yaml
from pathlib import Path
from langchain_ollama import ChatOllama

MODEL = "qwen2.5:7b"
ROOT = Path(__file__).resolve().parent.parent
PROFILE = (ROOT / "data" / "company_profile.md").read_text(encoding="utf-8")
MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"

llm = ChatOllama(model=MODEL, temperature=0.3)


def construire_prompt(doc):
    faits = "\n".join(f"- {f}" for f in doc["faits_cles"])
    return f"""Tu rédiges un document interne officiel de l'entreprise fictive NovaTech Solutions.

PROFIL DE L'ENTREPRISE (à respecter strictement) :
{PROFILE}

DOCUMENT À RÉDIGER :
- Titre : {doc['titre']}
- Département : {doc['departement']}
- Version : {doc['version']} ({doc['date']})

FAITS CLÉS À INTÉGRER TELS QUELS (mêmes chiffres, même formulation) :
{faits}

CONSIGNES :
- Écris en français, dans un ton formel et professionnel.
- Structure le document en sections numérotées avec des titres (## 1. ..., ## 2. ...).
- Longueur : 300 à 500 mots.
- Intègre tous les faits clés ci-dessus sans en modifier les chiffres.
- N'invente aucun chiffre qui contredit le profil de l'entreprise.
- Commence directement par le contenu (pas d'introduction du type « Voici le document »).
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Nombre maximum de documents à générer")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    a_generer = [d for d in docs if not (RAW / f"{d['id']}.md").exists()]
    if args.limit:
        a_generer = a_generer[: args.limit]

    print(f"{len(a_generer)} document(s) à générer sur {len(docs)}")
    for i, doc in enumerate(a_generer, start=1):
        print(f"[{i}/{len(a_generer)}] {doc['id']} : {doc['titre']}")
        corps = llm.invoke(construire_prompt(doc)).content.strip()
        entete = (
            f"---\n"
            f"id: {doc['id']}\n"
            f"titre: {doc['titre']}\n"
            f"departement: {doc['departement']}\n"
            f"version: \"{doc['version']}\"\n"
            f"date: \"{doc['date']}\"\n"
            f"---\n\n"
            f"# {doc['titre']}\n\n"
        )
        (RAW / f"{doc['id']}.md").write_text(entete + corps + "\n", encoding="utf-8")
    print("Terminé.")


if __name__ == "__main__":
    main()