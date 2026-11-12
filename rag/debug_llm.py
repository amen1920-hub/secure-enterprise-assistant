import os
import sys
from langchain_ollama import ChatOllama
import rag

if os.getenv("MODEL"):
    rag.llm = ChatOllama(model=os.getenv("MODEL"), temperature=0)

role, question = sys.argv[1], " ".join(sys.argv[2:])
resultats = rag.retrieve_scored(question, role, k=4)
for i, (d, s) in enumerate(resultats, start=1):
    print(f"[{i}] {s:.3f}  {d.metadata['doc_id']} - {d.metadata['section']}")
print("\n--- Réponse brute du LLM ---")
print(rag.llm.invoke(rag.construire_prompt(question, [d for d, _ in resultats])).content)