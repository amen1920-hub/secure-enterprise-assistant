import sys
from rag import retrieve_hybrid, retrieve_reranked

role, question = sys.argv[1], " ".join(sys.argv[2:])

docs, vec = retrieve_hybrid(question, role, k=6)
print(f"Hybride seul (score vectoriel {vec:.3f}) :")
for i, d in enumerate(docs, start=1):
    print(f"  {i}  {d.metadata['doc_id']:10} {d.metadata['titre']} - {d.metadata['section']}")

docs, vec, scores = retrieve_reranked(question, role, k=6)
print("\nAprès reranker :")
for i, (d, s) in enumerate(zip(docs, scores), start=1):
    print(f"  {i}  {s:.3f}  {d.metadata['doc_id']:10} {d.metadata['titre']} - {d.metadata['section']}")