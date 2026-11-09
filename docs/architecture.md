# Architecture

## Schéma général

```mermaid
flowchart TD
    U[Utilisateur avec un rôle] --> UI[Interface web React]
    UI --> API[API FastAPI + authentification JWT]
    API --> AG[Agent LangGraph]
    AG --> MCP[Serveur MCP]
    MCP --> T1[search_documents]
    MCP --> T2[get_user_permissions]
    MCP --> T3[get_document_metadata]
    T1 --> F[Filtre par rôle]
    F --> DB[(Qdrant : base vectorielle + métadonnées)]
    DB --> RR[Reranker]
    RR --> LLM[LLM Ollama qwen2.5:3b]
    LLM --> R[Réponse avec citations]
    R --> UI
```

## Flux d'une question

1. L'utilisateur se connecte et pose une question.
2. L'API identifie son rôle grâce au jeton JWT.
3. L'agent LangGraph vérifie les permissions de ce rôle.
4. La recherche ne porte que sur les documents autorisés (filtre appliqué avant la récupération).
5. Les passages trouvés sont reclassés par le reranker.
6. Le LLM répond uniquement à partir de ces passages et cite ses sources.
7. Si aucun document autorisé ne répond, l'assistant refuse ou dit qu'il ne sait pas.

## Pipeline d'ingestion

Documents (PDF, DOCX, MD) → extraction du texte → découpage en chunks → métadonnées (département, confidentialité, rôles, version, date) → embeddings `bge-m3` → Qdrant.