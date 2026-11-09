import re
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.yaml"


def lire_document(chemin):
    texte = chemin.read_text(encoding="utf-8")
    texte = re.sub(r"^---\n.*?\n---\n", "", texte, count=1, flags=re.S)
    return texte.strip()


def decouper(texte, max_car=900):
    """Découpe par section (## ou ###), puis par paragraphes si une section est trop longue."""
    sections = re.split(r"(?m)^(?=#{2,3} )", texte)
    chunks = []
    for s in sections:
        s = s.strip()
        if len(s) < 60:
            continue
        titre = s.splitlines()[0].lstrip("# ").strip() if s.startswith("#") else "Introduction"
        if len(s) <= max_car:
            chunks.append((titre, s))
            continue
        courant = ""
        for p in s.split("\n\n"):
            if courant and len(courant) + len(p) > max_car:
                chunks.append((titre, courant.strip()))
                courant = ""
            courant += p + "\n\n"
        if courant.strip():
            chunks.append((titre, courant.strip()))
    return chunks


if __name__ == "__main__":
    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    total = 0
    longueurs = []
    for d in docs:
        chunks = decouper(lire_document(RAW / f"{d['id']}.md"))
        total += len(chunks)
        longueurs += [len(c[1]) for c in chunks]
        print(f"{d['id']:12} {len(chunks)} chunks")
    print(f"\nTotal : {total} chunks, longueur moyenne {sum(longueurs) // len(longueurs)} caractères")
    print("\nExemple de chunk :")
    titre, texte = decouper(lire_document(RAW / "RH-001.md"))[0]
    print(f"[{titre}]\n{texte}")