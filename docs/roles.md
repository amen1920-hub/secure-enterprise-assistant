# Rôles et permissions

## Rôles

| Rôle | Description |
|---|---|
| employe | Employé standard |
| manager | Responsable d'équipe |
| rh | Ressources humaines |
| finance | Service financier |
| admin | Direction / administrateur |

## Niveaux de confidentialité

| Niveau | Signification |
|---|---|
| public | Visible par tous les employés |
| restreint | Visible seulement par certains rôles |
| confidentiel | Visible par très peu de rôles |

## Matrice d'accès par catégorie de documents

| Catégorie | employe | manager | rh | finance | admin |
|---|---|---|---|---|---|
| RH public (congés, télétravail) | ✅ | ✅ | ✅ | ✅ | ✅ |
| RH confidentiel (salaires, évaluations) | ❌ | ❌ | ✅ | ❌ | ✅ |
| IT (VPN, mots de passe, incidents) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Finance restreint (budget, rapports) | ❌ | ✅ (partiel) | ❌ | ✅ | ✅ |
| Juridique public (chartes, RGPD) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Juridique restreint (contrats) | ❌ | ❌ | ✅ | ❌ | ✅ |
| Direction (stratégie, restructuration) | ❌ | ❌ | ❌ | ❌ | ✅ |

## Règle principale

Le filtrage par rôle est appliqué **avant** la récupération des documents. Le LLM ne voit jamais un document interdit.