import argparse
import json
import re
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"
SORTIE = ROOT / "evaluation"

SUSPECT = re.compile(
    r"r[èe]gles? de base|r[ôo]les? d.acc[èe]s|conformit[ée] aux r[èe]gles", re.IGNORECASE)
VERSION = re.compile(r"version\s+(\d+\.\d+)", re.IGNORECASE)


def sans_entete(texte):
    return re.sub(r"^---\n.*?\n---\n", "", texte, count=1, flags=re.S)


def normaliser(texte):
    return re.sub(r"(?<=\d)[\s\u00a0\u202f](?=\d{3}\b)", "", texte)


def nombres(texte, ignorer_titres=True):
    texte = normaliser(texte)
    if ignorer_titres:
        texte = re.sub(r"(?m)^#{1,6} .*$", "", texte)
    texte = re.sub(r"(?m)^\s*\d+[.)]\s", "", texte)
    return set(re.findall(r"\d+(?:[.,]\d+)?", texte))


def significatif(n):
    return len(re.sub(r"\D", "", n)) >= 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--etiquette", default="avant")
    args = parser.parse_args()

    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    hors_sujet, versions, inventes, mots = [], [], [], []
    for d in docs:
        fichier = RAW / f"{d['id']}.md"
        if not fichier.exists():
            continue
        texte = sans_entete(fichier.read_text(encoding="utf-8"))
        mots.append(len(texte.split()))

        titres = re.findall(r"(?m)^#{1,6} (.*)$", texte)
        if any(SUSPECT.search(t) for t in titres):
            hors_sujet.append(d["id"])

        m = VERSION.search(texte)
        if m and m.group(1) != str(d["version"]):
            versions.append(f"{d['id']} (texte {m.group(1)}, métadonnées {d['version']})")

        autorises = nombres(
            " ".join(d["faits_cles"]) + " " + d["titre"] + " "
            + str(d["date"]) + " " + str(d["version"]), ignorer_titres=False)
        inconnus = sorted(n for n in nombres(texte) - autorises if significatif(n))
        if inconnus:
            inventes.append(f"{d['id']} : {', '.join(inconnus[:6])}")

    n = len(mots)
    print(f"Documents audités : {n}")
    print(f"Mots par document (moyenne) : {sum(mots) // n}")
    print(f"Sections hors sujet (règles de base, rôles d'accès...) : {len(hors_sujet)} documents")
    print(f"Version du texte différente des métadonnées : {len(versions)} documents")
    print(f"Nombres absents des faits clés : {len(inventes)} documents")
    for titre, liste in (("Sections hors sujet", hors_sujet),
                         ("Versions incohérentes", versions),
                         ("Nombres absents des faits clés", inventes)):
        if liste:
            print(f"\n{titre} (12 premiers) :")
            for x in liste[:12]:
                print("  ", x)

    SORTIE.mkdir(exist_ok=True)
    resultat = {"documents": n, "mots_moyens": sum(mots) // n,
                "hors_sujet": hors_sujet, "versions": versions, "nombres": inventes}
    (SORTIE / f"audit_donnees_{args.etiquette}.json").write_text(
        json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nRésultat enregistré : evaluation/audit_donnees_{args.etiquette}.json")


if __name__ == "__main__":
    main()