import os
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))
sys.path.insert(0, str(ROOT / "agent"))
import tools  # noqa: E402

# Identité de l'utilisateur : fixée au lancement du serveur, jamais par le LLM.
ROLE = os.getenv("MCP_USER_ROLE", "").strip().lower()

mcp = FastMCP("securedocs-ai")


def _role():
    if ROLE not in tools.rag.ROLES:
        raise ValueError("Utilisateur non identifié : variable MCP_USER_ROLE invalide.")
    return ROLE


@mcp.tool()
def search_documents(question: str, k: int = 4) -> dict:
    """Recherche les passages pertinents parmi les documents d'entreprise
    que l'utilisateur connecté a le droit de consulter."""
    return tools.search_documents(question, _role(), max(1, min(k, 8)))


@mcp.tool()
def get_user_permissions() -> dict:
    """Liste les documents que l'utilisateur connecté peut consulter."""
    return tools.get_user_permissions(_role())


@mcp.tool()
def get_document_metadata(doc_id: str) -> dict:
    """Donne les métadonnées d'un document (département, version, date,
    confidentialité), seulement si l'utilisateur y a accès."""
    return tools.get_document_metadata(doc_id, _role())


if __name__ == "__main__":
    mcp.run()