import csv
import re
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "metadata.csv"

ROLES_VALIDES = {"employe", "manager", "rh", "finance", "admin"}
NIVEAUX_VALIDES = {"public", "restreint", "confidentiel"}
CHAMPS = ["id", "titre", "departement", "confidentialite",
          "roles_autorises", "version", "date", "faits_cles"]


def normaliser(texte):
    return re.sub(r"[\s\u00a0\u202f]", "", texte)


def nombres(fait):
    brut = re.findall(r"\d+(?:[\s\u00a0\u202f.,]\d+)*", fait)
    return [normaliser(n) for n in brut]


def main():
    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    erreurs, avertissements, lignes = [], [], []
    ids_vus = set()
    faits_total, faits_ok, faits_verifiables = 0, 0, 0

    for d in docs:
        did = d.get("id", "???")
        for champ in CHAMPS:
            if champ not in d or d[champ] in (None, "", []):
                erreurs.append(f"{did} : champ manquant '{champ}'")
        if did in ids_vus:
            erreurs.append(f"{did} : identifiant en double")
        ids_vus.add(did)

        if d.get("confidentialite") not in NIVEAUX_VALIDES:
            erreurs.append(f"{did} : confidentialité invalide '{d.get('confidentialite')}'")
        roles_inconnus = set(d.get("roles_autorises", [])) - ROLES_VALIDES
        if roles_inconnus:
            erreurs.append(f"{did} : rôles inconnus {sorted(roles_inconnus)}")

        fichier = RAW / f"{did}.md"
        if not fichier.exists():
            erreurs.append(f"{did} : fichier manquant ({fichier.name})")
            continue

        texte = fichier.read_text(encoding="utf-8")
        if len(texte.split()) < 150:
            avertissements.append(f"{did} : document très court ({len(texte.split())} mots)")

        texte_norm = normaliser(texte)
        for fait in d.get("faits_cles", []):
            faits_total += 1
            nums = nombres(fait)
            if not nums:
                continue
            faits_verifiables += 1
            if all(n in texte_norm for n in nums):
                faits_ok += 1
            else:
                avertissements.append(f"{did} : fait absent du texte -> {fait}")

        lignes.append({
            "id": did,
            "titre": d["titre"],
            "departement": d["departement"],
            "confidentialite": d["confidentialite"],
            "roles_autorises": "|".join(d["roles_autorises"]),
            "version": d["version"],
                        "date": d["date"],
            "statut": d.get("statut", "actuelle"),
            "famille": d.get("famille", did),
            "chemin": f"data/raw/{did}.md",
        })

    print(f"Documents dans le manifeste : {len(docs)}")
    print(f"Faits clés : {faits_total} (vérifiables par chiffre : {faits_verifiables}, retrouvés : {faits_ok})")
    print(f"Erreurs : {len(erreurs)} | Avertissements : {len(avertissements)}")
    for e in erreurs:
        print("  ERREUR :", e)
    for a in avertissements[:30]:
        print("  attention :", a)

    if erreurs:
        print("Corrige les erreurs avant de continuer : metadata.csv n'a pas été écrit.")
        return

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes)} lignes écrites dans {OUT}")


if __name__ == "__main__":
    main()