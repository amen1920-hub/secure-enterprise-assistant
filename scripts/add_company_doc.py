import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.yaml"

DOC = {
    "id": "GEN-001",
    "titre": "Présentation de l'entreprise NovaTech Solutions",
    "departement": "Général",
    "confidentialite": "public",
    "roles_autorises": ["employe", "manager", "rh", "finance", "admin"],
    "version": "1.0",
    "date": "2026-01-05",
    "faits_cles": [
        "NovaTech Solutions est une entreprise de services numériques et de conseil informatique",
        "Le siège de NovaTech Solutions est situé à Tunis, en Tunisie",
        "NovaTech Solutions a été créée en 2012",
        "NovaTech Solutions compte 320 employés",
        "L'entreprise compte 6 départements : Ressources humaines, IT, Finance, Juridique, Direction et Production / Projets",
        "Le PDG de NovaTech Solutions est Mehdi Gharbi",
        "Le département Production / Projets est le plus grand avec 247 employés",
        "Le département IT compte 35 employés",
    ],
}

docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
if any(d["id"] == DOC["id"] for d in docs):
    print("GEN-001 existe déjà dans le manifeste")
else:
    docs.insert(0, DOC)
    MANIFEST.write_text(
        yaml.dump({"documents": docs}, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    print(f"GEN-001 ajouté : {len(docs)} documents dans le manifeste")