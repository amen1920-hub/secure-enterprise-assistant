from langchain_ollama import ChatOllama, OllamaEmbeddings

# Test du LLM
llm = ChatOllama(model="qwen2.5:3b")
reponse = llm.invoke("Explique ce qu'est un RAG en deux phrases.")
print("LLM :", reponse.content)

# Test des embeddings
emb = OllamaEmbeddings(model="bge-m3")
vecteur = emb.embed_query("politique de congés payés")
print("Embeddings : vecteur de taille", len(vecteur))