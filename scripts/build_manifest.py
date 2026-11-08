import json
import yaml
from pathlib import Path
from langchain_ollama import ChatOllama

MODEL = "qwen2.5:7b"
ROOT = Path(__file__).resolve().parent.parent
PROFILE = (ROOT / "data" / "company_profile.md").read_text(encoding="utf-8")
OUT = ROOT / "data" / "manifest.yaml"

TOUS = ["employe", "manager", "rh", "finance", "admin"]

# Droits d'accès fixés ici, conformément à docs/roles.md
CATEGORIES = [
    {"prefix": "RH", "departement": "RH", "confidentialite": "public",
     "roles": TOUS, "n": 8,
     "theme": "politiques RH générales (congés, télétravail, horaires, recrutement, formation, absences)"},
    {"prefix": "RHC", "departement": "RH", "confidentialite": "confidentiel",
     "roles": ["rh", "admin"], "n": 5,
     "theme": "documents RH confidentiels (grille des salaires, primes, évaluations, procédures disciplinaires)"},
    {"prefix": "IT", "departement": "IT", "confidentialite": "public",
     "roles": TOUS, "n": 8,
     "theme": "procédures informatiques (VPN, mots de passe, incidents, matériel, messagerie, sauvegardes)"},
    {"prefix": "FIN", "departement": "Finance", "confidentialite": "restreint",
     "roles": ["manager", "finance", "admin"], "n": 6,
     "theme": "documents financiers (budget annuel, frais de mission, rapports trimestriels, achats)"},
    {"prefix": "JUR", "departement": "Juridique", "confidentialite": "public",
     "roles": TOUS, "n": 5,
     "theme": "documents juridiques publics (charte de confidentialité, RGPD, code de conduite)"},
    {"prefix": "JURR", "departement": "Juridique", "confidentialite": "restreint",
     "roles": ["rh", "admin"], "n": 4,
     "theme": "documents juridiques restreints (modèles de contrats, litiges, clauses de non-concurrence)"},
    {"prefix": "DIR", "departement": "Direction", "confidentialite": "confidentiel",
     "roles": ["admin"], "n": 4,
     "theme": "documents de direction (stratégie 2026-2028, plan de restructuration, acquisitions)"},
]

llm = ChatOllama(model=MODEL, temperature=0.4, format="json")


def proposer(cat, deja):
    prompt = f"""Tu aides à construire une base documentaire pour une entreprise fictive.

PROFIL DE L'ENTREPRISE (à respecter strictement) :
{PROFILE}

Propose {cat['n']} documents internes du département {cat['departement']}.
Thème : {cat['theme']}.
Titres déjà utilisés (à ne pas répéter) : {deja}

Pour chaque document, donne un titre et 4 à 5 faits clés précis et chiffrés
(durées, montants en TND, seuils, délais, pourcentages), cohérents avec le profil.

Réponds uniquement en JSON, sous cette forme :
{{"documents": [{{"titre": "...", "faits_cles": ["...", "..."]}}]}}"""
    for _ in range(3):
        try:
            data = json.loads(llm.invoke(prompt).content)
            docs = data["documents"]
            if len(docs) >= 1:
                return docs[: cat["n"]]
        except Exception as e:
            print("  nouvel essai :", e)
    raise RuntimeError(f"Échec pour la catégorie {cat['prefix']}")


def main():
    manifest, titres = [], []
    for i_cat, cat in enumerate(CATEGORIES):
        print(f"Génération : {cat['prefix']} ({cat['n']} documents)")
        docs = proposer(cat, titres)
        for i, d in enumerate(docs, start=1):
            titres.append(d["titre"])
            manifest.append({
                "id": f"{cat['prefix']}-{i:03d}",
                "titre": d["titre"],
                "departement": cat["departement"],
                "confidentialite": cat["confidentialite"],
                "roles_autorises": cat["roles"],
                "version": "1.0",
                "date": f"2026-{(i_cat + i) % 9 + 1:02d}-15",
                "faits_cles": d["faits_cles"],
            })
    OUT.write_text(
        yaml.dump({"documents": manifest}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"{len(manifest)} documents écrits dans {OUT}")


if __name__ == "__main__":
    main()