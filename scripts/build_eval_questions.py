import json
import random
import yaml
from pathlib import Path
from langchain_ollama import ChatOllama

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.yaml"
OUT = ROOT / "evaluation" / "eval_questions.json"
ROLES = {"employe", "manager", "rh", "finance", "admin"}

random.seed(42)
llm = ChatOllama(model="qwen2.5:7b", temperature=0.2, format="json")


def a_un_chiffre(texte):
    return any(c.isdigit() for c in texte)


def question_depuis_fait(titre, fait, actuel=False):
    consigne = " Utilise le mot « actuellement » dans la question." if actuel else ""
    prompt = f"""Document : « {titre} »
Fait : {fait}

Écris UNE question en français, claire et autonome, qu'un employé poserait
et dont la réponse est exactement ce fait. Ne donne pas la réponse dans la question.{consigne}
Réponds en JSON : {{"question": "..."}}"""
    for _ in range(3):
        try:
            q = json.loads(llm.invoke(prompt).content)["question"].strip()
            if q.endswith("?"):
                return q
        except Exception:
            pass
    return f"Que dit le document « {titre} » à propos de : {fait} ?"


def main():
    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    par_id = {d["id"]: d for d in docs}
    actuelles = [d for d in docs if d.get("statut", "actuelle") != "obsolete"]
    questions = []

    def ajouter(type_, q, role, doc_id, reponse, **extra):
        questions.append({
            "id": f"Q{len(questions) + 1:03d}",
            "type": type_,
            "question": q,
            "role": role,
            "doc_attendu": doc_id,
            "reponse_attendue": reponse,
            **extra,
        })

    # 1. Questions simples (documents sans version multiple)
    simples = [d for d in actuelles if "famille" not in d
               and any(a_un_chiffre(f) for f in d["faits_cles"])]
    random.shuffle(simples)
    for d in simples[:30]:
        fait = next(f for f in d["faits_cles"] if a_un_chiffre(f))
        role = random.choice(d["roles_autorises"])
        ajouter("simple", question_depuis_fait(d["titre"], fait), role, d["id"], fait)

    # 2. Questions de version
    for d in actuelles:
        if d.get("famille") != d["id"]:
            continue
        ancien = par_id.get(f"{d['id']}-V1")
        if not ancien:
            continue
        for actuel, vieux in zip(d["faits_cles"], ancien["faits_cles"]):
            if actuel != vieux and a_un_chiffre(actuel):
                role = random.choice(d["roles_autorises"])
                ajouter("version",
                        question_depuis_fait(d["titre"], actuel, actuel=True),
                        role, d["id"], actuel,
                        doc_obsolete=ancien["id"], reponse_obsolete=vieux)
                break

    # 3. Questions interdites (le rôle n'a pas le droit)
    sensibles = [d for d in actuelles if d["confidentialite"] != "public"
                 and ROLES - set(d["roles_autorises"])]
    random.shuffle(sensibles)
    for d in sensibles[:12]:
        fait = next((f for f in d["faits_cles"] if a_un_chiffre(f)), d["faits_cles"][0])
        role = random.choice(sorted(ROLES - set(d["roles_autorises"])))
        ajouter("interdit", question_depuis_fait(d["titre"], fait), role,
                d["id"], "REFUS")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    for t in ("simple", "version", "interdit"):
        print(t, ":", sum(q["type"] == t for q in questions))
    print(f"Total : {len(questions)} questions écrites dans {OUT}")
    if len(questions) < 50:
        print("Attention : moins de 50 questions, on en ajoutera.")


if __name__ == "__main__":
    main()