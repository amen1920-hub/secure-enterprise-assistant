import sys
from rag import retrieve_hybrid

role, question = sys.argv[1], " ".join(sys.argv[2:])
docs, score = retrieve_hybrid(question, role, k=6)
print(f"(meilleur score vectoriel : {score:.3f})")
for rang, d in enumerate(docs, start=1):
    m = d.metadata
    print(f"{rang}  {m['doc_id']:10} {m['titre']} - {m['section']}")