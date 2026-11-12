import re
import sys
from pathlib import Path
from typing import TypedDict
from langgraph.graph import END, StateGraph

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))
import rag  # noqa: E402


class Etat(TypedDict, total=False):
    question: str
    role: str
    docs: list
    score: float
    reponse: str
    sources: list
    statut: str


def refus(statut, message=None, score=0.0):
    return {"reponse": message or rag.REFUS, "sources": [],
            "score": score, "statut": statut}


def verifier_role(etat):
    if etat["role"] not in rag.ROLES:
        return refus("role_invalide", "Rôle inconnu : accès refusé.")
    return {}


def rechercher(etat):
    docs, score = rag.retrieve_hybrid(etat["question"], etat["role"], k=4)
    return {"docs": docs, "score": score}


def refuser_hors_sujet(etat):
    return refus("hors_sujet", score=etat["score"])


def generer(etat):
    prompt = rag.construire_prompt(etat["question"], etat["docs"])
    return {"reponse": rag.llm.invoke(prompt).content.strip()}


def verifier_citations(etat):
    cites = {int(n) for n in re.findall(r"\[(\d+)\]", etat["reponse"])}
    if rag.REFUS in etat["reponse"] or not cites:
        return refus("sans_source", score=etat["score"])
    sources = [{
        "n": i,
        "doc_id": d.metadata["doc_id"],
        "titre": d.metadata["titre"],
        "version": d.metadata["version"],
        "section": d.metadata["section"],
    } for i, d in enumerate(etat["docs"], start=1) if i in cites]
    return {"sources": sources, "statut": "repondu"}


def apres_role(etat):
    return "stop" if etat.get("statut") == "role_invalide" else "suite"


def apres_recherche(etat):
    if not etat["docs"] or etat["score"] < rag.SEUIL:
        return "refuser"
    return "generer"


def construire_agent():
    g = StateGraph(Etat)
    g.add_node("verifier_role", verifier_role)
    g.add_node("rechercher", rechercher)
    g.add_node("refuser_hors_sujet", refuser_hors_sujet)
    g.add_node("generer", generer)
    g.add_node("verifier_citations", verifier_citations)

    g.set_entry_point("verifier_role")
    g.add_conditional_edges("verifier_role", apres_role,
                            {"stop": END, "suite": "rechercher"})
    g.add_conditional_edges("rechercher", apres_recherche,
                            {"refuser": "refuser_hors_sujet", "generer": "generer"})
    g.add_edge("refuser_hors_sujet", END)
    g.add_edge("generer", "verifier_citations")
    g.add_edge("verifier_citations", END)
    return g.compile()


agent = construire_agent()


def ask(question, role):
    etat = agent.invoke({"question": question, "role": role})
    return {k: etat.get(k) for k in ("reponse", "sources", "score", "statut")}


if __name__ == "__main__":
    if sys.argv[1:2] == ["--graph"]:
        print(agent.get_graph().draw_mermaid())
        sys.exit()
    role, question = sys.argv[1], " ".join(sys.argv[2:])
    r = ask(question, role)
    print(f"(rôle : {role} | statut : {r['statut']} | score : {r['score']:.3f})")
    print("\nRéponse :\n" + r["reponse"])
    for s in r["sources"]:
        print(f"  [{s['n']}] {s['doc_id']} v{s['version']} - {s['titre']} - {s['section']}")