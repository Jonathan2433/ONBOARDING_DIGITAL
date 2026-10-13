/**
 * « Super-administration » — créer une entité depuis des modèles génériques,
 * LOT 9, `T12` (API) puis `T14` (écran), `MVP-L09-US007`, `SUPER` seul.
 *
 * L'ENTITÉ NAÎT VIERGE, LE PREMIER ADMINISTRATEUR EST UNE PERSONNE DÉJÀ CONNUE
 *
 *   Double arbitrage de Jonathan (`T12`) : aucun contenu, aucune responsabilité
 *   Framework, aucun modèle d'onboarding n'est semé. Ce formulaire ne propose
 *   donc AUCUN champ de contenu — seulement l'identité de l'entité et
 *   l'identifiant (UUID) d'une personne déjà existante pour `premier_
 *   administrateur` : aucune route ne liste les personnes TOUTES ENTITÉS
 *   confondues (le trombinoscope est borné à UNE entité), donc ce champ reste
 *   un identifiant saisi, pas un choix dans une liste — résidu nommé, §9.3.
 */
import type { JSX } from 'react';
import { useState } from 'react';

import { creerUneEntite } from '../../api/portail';
import { peutCreerUneEntite, type EntiteCreee } from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Seul un super-administrateur peut créer une entité.';
  }
  if (statut === 409) {
    return 'Ce code d’entité est déjà pris.';
  }
  if (statut === 422) {
    return 'La demande n’est pas valide. Vérifiez les champs renseignés (pays : deux lettres ISO, fuseau IANA).';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

export function SectionSuperAdministration({
  roles,
}: {
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const [code, setCode] = useState('');
  const [nom, setNom] = useState('');
  const [ville, setVille] = useState('');
  const [pays, setPays] = useState('FR');
  const [fuseau, setFuseau] = useState('Europe/Paris');
  const [premierAdministrateur, setPremierAdministrateur] = useState('');
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [creee, setCreee] = useState<EntiteCreee | null>(null);

  if (!peutCreerUneEntite(roles)) {
    return <p>Votre rôle ne porte aucun droit de super-administration.</p>;
  }

  async function creer(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat = await creerUneEntite({
      code,
      nom,
      ville,
      pays,
      fuseau,
      premier_administrateur: premierAdministrateur,
    });
    setEnvoi(false);
    if (resultat.statut === 201 && resultat.corps !== null) {
      setCreee(resultat.corps);
      setCode('');
      setNom('');
      setVille('');
      setPremierAdministrateur('');
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  const pretAEnvoyer =
    code.trim() !== '' &&
    nom.trim() !== '' &&
    ville.trim() !== '' &&
    pays.trim().length === 2 &&
    fuseau.trim() !== '' &&
    premierAdministrateur.trim() !== '';

  return (
    <section
      className="administration-super-administration"
      aria-labelledby="administration-super-administration-titre"
    >
      <h3 id="administration-super-administration-titre">Créer une entité</h3>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {creee === null ? null : (
        <Alerte ton="succes" urgence="information">
          Entité « {creee.code} » créée.
        </Alerte>
      )}
      <div className="administration-champs">
        <label className="administration-champ" htmlFor="entite-code">
          Code
          <input
            id="entite-code"
            onChange={(evenement) => {
              setCode(evenement.target.value);
            }}
            type="text"
            value={code}
          />
        </label>
        <label className="administration-champ" htmlFor="entite-nom">
          Nom
          <input
            id="entite-nom"
            onChange={(evenement) => {
              setNom(evenement.target.value);
            }}
            type="text"
            value={nom}
          />
        </label>
        <label className="administration-champ" htmlFor="entite-ville">
          Ville
          <input
            id="entite-ville"
            onChange={(evenement) => {
              setVille(evenement.target.value);
            }}
            type="text"
            value={ville}
          />
        </label>
        <label className="administration-champ" htmlFor="entite-pays">
          Pays (ISO 3166-1 alpha-2)
          <input
            id="entite-pays"
            maxLength={2}
            onChange={(evenement) => {
              setPays(evenement.target.value.toUpperCase());
            }}
            type="text"
            value={pays}
          />
        </label>
        <label className="administration-champ" htmlFor="entite-fuseau">
          Fuseau (IANA)
          <input
            id="entite-fuseau"
            onChange={(evenement) => {
              setFuseau(evenement.target.value);
            }}
            type="text"
            value={fuseau}
          />
        </label>
        <label className="administration-champ" htmlFor="entite-premier-administrateur">
          Identifiant (UUID) du premier administrateur
          <input
            id="entite-premier-administrateur"
            onChange={(evenement) => {
              setPremierAdministrateur(evenement.target.value);
            }}
            type="text"
            value={premierAdministrateur}
          />
        </label>
        <Bouton
          disabled={envoi || !pretAEnvoyer}
          onClick={() => {
            void creer();
          }}
          type="button"
          variante="primaire"
        >
          {envoi ? 'Envoi…' : 'Créer l’entité'}
        </Bouton>
      </div>
    </section>
  );
}
