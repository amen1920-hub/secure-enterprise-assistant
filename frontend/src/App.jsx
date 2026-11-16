import { useEffect, useRef, useState } from "react";
import { poserQuestion, seConnecter } from "./api.js";

const EXEMPLES = [
  "Combien de jours de congés payés par an ?",
  "Quels sont les niveaux de salaires ?",
  "Quelle est la longueur minimale d'un mot de passe ?",
  "Quels documents puis-je consulter ?",
];

const ETIQUETTES = {
  repondu: ["Réponse sourcée", "ok"],
  permissions: ["Vos accès", "info"],
  metadonnees: ["Informations du document", "info"],
  hors_sujet: ["Aucune information trouvée", "refus"],
  sans_source: ["Aucune source valide", "refus"],
  introuvable: ["Introuvable ou accès refusé", "refus"],
  role_invalide: ["Accès refusé", "refus"],
  erreur: ["Erreur", "refus"],
};

function Connexion({ onConnecte, message }) {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState(message || "");
  const [attente, setAttente] = useState(false);

  async function valider(e) {
    e.preventDefault();
    setErreur("");
    setAttente(true);
    try {
      const r = await seConnecter(email, motDePasse);
      onConnecte({ jeton: r.access_token, email: r.email, role: r.role });
    } catch (err) {
      setErreur(err.statut === 401 ? "Email ou mot de passe incorrect." : "Le serveur ne répond pas.");
    } finally {
      setAttente(false);
    }
  }

  return (
    <div className="centre">
      <form className="carte" onSubmit={valider}>
        <h1>SecureDocs AI</h1>
        <p className="sous-titre">Assistant de connaissances d'entreprise</p>
        <label>Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
               placeholder="employe@novatech.tn" required />
        <label>Mot de passe</label>
        <input type="password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} required />
        {erreur && <p className="erreur">{erreur}</p>}
        <button type="submit" disabled={attente}>{attente ? "Connexion..." : "Se connecter"}</button>
      </form>
    </div>
  );
}

function Chat({ session, onDeconnexion }) {
  const [messages, setMessages] = useState([]);
  const [saisie, setSaisie] = useState("");
  const [attente, setAttente] = useState(false);
  const bas = useRef(null);

  useEffect(() => {
    bas.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, attente]);

  async function envoyer(texte) {
    const question = texte.trim();
    if (!question || attente) return;
    setMessages((m) => [...m, { auteur: "vous", texte: question }]);
    setSaisie("");
    setAttente(true);
    try {
      const r = await poserQuestion(question, session.jeton);
      setMessages((m) => [...m, { auteur: "assistant", texte: r.reponse,
                                  sources: r.sources || [], statut: r.statut }]);
    } catch (err) {
      if (err.statut === 401) {
        onDeconnexion("Session expirée : reconnectez-vous.");
        return;
      }
      setMessages((m) => [...m, { auteur: "assistant", texte: "Le serveur n'a pas pu répondre.",
                                  sources: [], statut: "erreur" }]);
    } finally {
      setAttente(false);
    }
  }

  return (
    <div className="page">
      <header>
        <strong>SecureDocs AI</strong>
        <span className="utilisateur">
          {session.email} <span className="role">{session.role}</span>
          <button className="lien" onClick={() => onDeconnexion("")}>Déconnexion</button>
        </span>
      </header>

      <main>
        {messages.length === 0 && (
          <div className="accueil">
            <p>Posez une question sur les documents auxquels votre rôle donne accès.</p>
            <div className="exemples">
              {EXEMPLES.map((q) => (
                <button key={q} className="exemple" onClick={() => envoyer(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`message ${m.auteur}`}>
            <div className="bulle">
              {m.statut && ETIQUETTES[m.statut] && (
                <span className={`badge ${ETIQUETTES[m.statut][1]}`}>{ETIQUETTES[m.statut][0]}</span>
              )}
              <p className="texte">{m.texte}</p>
              {m.sources && m.sources.length > 0 && (
                <ul className="sources">
                  {m.sources.map((s) => (
                    <li key={s.n}>
                      <strong>[{s.n}] {s.doc_id}</strong> v{s.version} — {s.titre} — {s.section}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}

        {attente && (
          <div className="message assistant">
            <div className="bulle"><p className="texte attente">L'assistant réfléchit...</p></div>
          </div>
        )}
        <div ref={bas} />
      </main>

      <form className="saisie" onSubmit={(e) => { e.preventDefault(); envoyer(saisie); }}>
        <input value={saisie} onChange={(e) => setSaisie(e.target.value)}
               placeholder="Votre question..." maxLength={1000} disabled={attente} />
        <button type="submit" disabled={attente || !saisie.trim()}>Envoyer</button>
      </form>
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [message, setMessage] = useState("");

  if (!session) {
    return <Connexion message={message} onConnecte={(s) => { setMessage(""); setSession(s); }} />;
  }
  return <Chat session={session} onDeconnexion={(msg) => { setMessage(msg); setSession(null); }} />;
}