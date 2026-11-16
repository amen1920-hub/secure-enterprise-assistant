async function requete(chemin, options = {}, jeton) {
  const entetes = { "Content-Type": "application/json" };
  if (jeton) entetes.Authorization = `Bearer ${jeton}`;
  const reponse = await fetch(`/api${chemin}`, { ...options, headers: entetes });
  if (!reponse.ok) {
    const erreur = new Error("Erreur " + reponse.status);
    erreur.statut = reponse.status;
    throw erreur;
  }
  return reponse.json();
}

export const seConnecter = (email, password) =>
  requete("/login", { method: "POST", body: JSON.stringify({ email, password }) });

export const poserQuestion = (question, jeton) =>
  requete("/ask", { method: "POST", body: JSON.stringify({ question }) }, jeton);

export const mesDocuments = (jeton) => requete("/documents", {}, jeton);