import re
import sys
from pathlib import Path
from typing import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))
sys.path.insert(0, str(ROOT / "agent"))
import rag  # noqa: E402
import tools  # noqa: E402


# --- Outils exposés au LLM : volontairement SANS paramètre "role" ---------

class ListerMesDocuments(BaseModel):
    """Liste les documents que l'utilisateur a le droit de consulter."""


class InfosDocument(BaseModel):
    """Donne les informations (département, version, date, confidentialité)
    d'un document précis dont l'utilisateur donne l'identifiant."""
    doc_id: str = Field(description="Identifiant du document, par exemple RH-001")


class RechercherDansLesDocuments(BaseModel):
    """Répond à toute question sur le contenu des documents de l'entreprise."""


CONSIGNE = (
    "Tu es un routeur. Choisis exactement un outil :\n"
    "- ListerMesDocuments : l'utilisateur demande la liste des documents auxquels il a accès.\n"
    "- InfosDocument : l'utilisateur demande les informations (version, date, département, "
    "confidentialité) d'un document dont il donne l'identifiant, par exemple RH-001.\n"
    "- RechercherDansLesDocuments : tout le reste, y compris les questions sur le contenu."
)

routeur_llm = rag.llm.bind_tools(
    [ListerMesDocuments, InfosDocument, RechercherDansLesDocuments])


class Etat(TypedDict, total=False):
    question: str
    role: str
    route: str
    doc_id: str
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


def router(etat):
    messages = [SystemMessage(content=CONSIGNE), HumanMessage(content=etat["question"])]
    try:
        appels = routeur_llm.invoke(messages).tool_calls
    except Exception:
        appels = []
    if appels:
        nom = appels[0]["name"]
        if nom == "ListerMesDocuments":
            return {"route": "permissions"}
        if nom == "InfosDocument":
            doc_id = str(appels[0]["args"].get("doc_id", "")).upper().strip()
            if doc_id:
                return {"route": "metadonnees", "doc_id": doc_id}
    return {"route": "recherche"}


def lister_permissions(etat):
    r = tools.get_user_permissions(etat["role"])
    lignes = [f"- {d['doc_id']} : {d['titre']} ({d['confidentialite']})"
              for d in r["documents"]]
    texte = f"Vous avez accès à {r['nombre']} documents :\n" + "\n".join(lignes)
    return {"reponse": texte, "sources": [], "score": 0.0, "statut": "permissions"}


def infos_document(etat):
    m = tools.get_document_metadata(etat["doc_id"], etat["role"])
    if "erreur" in m:
        return refus("introuvable", m["erreur"])
    texte = (f"{m['doc_id']} : {m['titre']} - département {m['departement']}, "
             f"confidentialité {m['confidentialite']}, version {m['version']} "
             f"({m['date']}).")
    return {"reponse": texte, "sources": [], "score": 0.0, "statut": "metadonnees"}


def rechercher(etat):
    docs, score = rag.retrieve_hybrid(etat["question"], etat["role"], k=4)
    return {"docs": docs, "score": score}


def refuser_hors_sujet(etat):
    return refus("hors_sujet", score=etat["score"])

def generer(etat):
    prompt = rag.construire_prompt(etat["question"], etat["docs"])
    reponse = rag.llm.invoke(prompt).content.strip()
    if rag.REFUS not in reponse and not re.search(r"\[\d+\]", reponse):
        rappel = ("Rappel obligatoire : termine chaque information par le numéro de sa "
                  "source entre crochets, par exemple [1].\n\nRÉPONSE :")
        reponse = rag.llm.invoke(prompt.replace("RÉPONSE :", rappel)).content.strip()
    return {"reponse": reponse}


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


def apres_routeur(etat):
    return etat["route"]


def apres_recherche(etat):
    if not etat["docs"] or etat["score"] < rag.SEUIL:
        return "refuser"
    return "generer"


def construire_agent():
    g = StateGraph(Etat)
    g.add_node("verifier_role", verifier_role)
    g.add_node("router", router)
    g.add_node("lister_permissions", lister_permissions)
    g.add_node("infos_document", infos_document)
    g.add_node("rechercher", rechercher)
    g.add_node("refuser_hors_sujet", refuser_hors_sujet)
    g.add_node("generer", generer)
    g.add_node("verifier_citations", verifier_citations)

    g.set_entry_point("verifier_role")
    g.add_conditional_edges("verifier_role", apres_role,
                            {"stop": END, "suite": "router"})
    g.add_conditional_edges("router", apres_routeur, {
        "permissions": "lister_permissions",
        "metadonnees": "infos_document",
        "recherche": "rechercher"})
    g.add_edge("lister_permissions", END)
    g.add_edge("infos_document", END)
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