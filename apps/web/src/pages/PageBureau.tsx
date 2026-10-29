/**
 * La page detaillee d'un bureau, a l'ecran — LOT 6, `T9`, story `MVP-L06-US003`.
 *
 * LE CRITERE, MOT POUR MOT
 *
 *   « BDS, BDE et BDG sont configurables ; un a trois responsables actifs sont
 *   affiches. » Aucun code de bureau n'est ecrit dans ce fichier : le bureau est
 *   resolu par son code dans l'adresse, comme `T4` l'a fait cote API.
 *
 * LA BORNE DU §8.4 EST RAPPORTEE, JAMAIS EXIGEE — MEME PARTI QUE LE CONTRAT
 *
 *   `respecteLaBorneDuHuitQuatre` vient de `@onboarding/contracts` et repond a
 *   une QUESTION, pas une exigence : un bureau en brouillon a zero responsable
 *   ne l'enfreint pas. L'ecran ne bloque donc rien et ne masque rien — il montre
 *   les responsables tels que l'API les rend, zero ou quatre compris, et signale
 *   l'ecart quand le bureau est publie sans respecter la borne, plutot que de le
 *   taire ou de le refuser (§7.20).
 *
 * AUCUNE PAGINATION, ET CE N'EST PAS UN OUBLI
 *
 *   Les responsables sont un ensemble BORNE par le §8.4, jamais une population :
 *   le §18.2 regit les populations, et en paginer trois inventerait un parametre
 *   que le cahier ne demande pas (§6.5). Meme raisonnement que `bureaux.py`.
 *
 * CHANTIER FRONT, S5 (`DEC-672`) : `CARTE`, ICONE DE BUREAU
 *
 *   **Mesure avant tout code** : `Badge` servait deja l'etat publie/brouillon
 *   depuis `T9` du LOT 6 — seul `Carte` manquait ici, a la difference de
 *   `PageFramework`/`PageCercle` ou les deux etaient absents. Deux `Carte`
 *   (identite, responsables) remplacent le `<article>`/`<header>` ecrits a la
 *   main. Une icone decorative (`Building2`, `lucide-react`, `aria-hidden`)
 *   rejoint le badge d'etat — aucun code de bureau (BDS/BDE/BDG…) n'etant
 *   ferme (`test_bureaux.py`, « entierement configurables »), une icone PAR
 *   TYPE de bureau est hors de portee : une seule icone generique marque la
 *   ressource, jamais une seconde source d'information (§13.2, « icones
 *   maitrisees »).
 *
 * CHANTIER FRONT, S12 (`DEC-673`) : LA PHOTO DES RESPONSABLES
 *
 *   `ResponsableDuBureau.photo` suit exactement la convention du trombinoscope
 *   et du profil (S11) : un cadre hexagonal sur fond de marque colore quand
 *   `photo` est `null`, l'image sinon. Arbitrage de Jonathan
 *   (`AskUserQuestion`, 29/10/2026) : la page de synthese Framework reste hors
 *   de cette sous-etape.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import { Link, useParams } from 'react-router';

import { lireLeBureau } from '../api/organisation';
import { cheminDeRubrique, cheminEditionBureau } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import {
  peutEditerUnContenu,
  type PageDuBureau,
  respecteLaBorneDuHuitQuatre,
} from '@onboarding/contracts';
import { Alerte, Badge, Carte } from '@onboarding/ui';

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'page'; readonly page: PageDuBureau }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageBureau(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const { codeBureau } = useParams<{ codeBureau: string }>();
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    if (codeBureau === undefined) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireLeBureau(entite.code, codeBureau, abandon.signal).then(
      (reponse) => {
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'page', page: reponse.corps }
            : { phase: 'erreur', statut: reponse.statut },
        );
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setEtat({ phase: 'erreur', statut: 0 });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [entite.code, codeBureau]);

  const roles = permissions?.roles ?? null;
  const peutEditer = roles !== null && peutEditerUnContenu(roles);

  const retour = (
    <p className="bureau-retour">
      <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
        Retour au Framework
      </Link>
      {codeBureau !== undefined && peutEditer ? (
        <>
          {' '}
          ·{' '}
          <Link className="app-lien" to={cheminEditionBureau(entite.code, codeBureau)}>
            Editer ce bureau
          </Link>
        </>
      ) : null}
    </p>
  );

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement du bureau…</Alerte>;
  }

  if (etat.phase === 'erreur') {
    return (
      <>
        <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour consulter ce bureau.'
            : etat.statut === 404
              ? "Ce bureau est introuvable, ou n'est plus actif."
              : "Le bureau n'a pas pu etre charge. Reessayez dans un instant."}
        </Alerte>
        {retour}
      </>
    );
  }

  const b = etat.page;
  //  Rapportee, jamais exigee — voir l'en-tete du module.
  const conforme = respecteLaBorneDuHuitQuatre(b);

  return (
    <div className="bureau">
      <Carte titre={b.nom}>
        <div className="bureau-entete-meta">
          <Building2 className="icone-bureau" aria-hidden="true" size={20} />
          <Badge ton={b.publie ? 'marque' : 'neutre'}>{b.publie ? 'Publie' : 'Brouillon'}</Badge>
        </div>
        {b.description === null ? null : <p className="bureau-description">{b.description}</p>}
        <dl className="bureau-champs">
          <dt>Localisation</dt>
          <dd>{b.localisation ?? 'Non renseignee'}</dd>
        </dl>
      </Carte>

      <Carte titre={`Responsables (${String(b.nombreDeResponsables)})`}>
        {!conforme ? (
          //  **RAPPORTE, PAS BLOQUE.** Ce bureau est publie et sa base ne respecte
          //  pas « un a trois » — le declencheur qui le garantira est `T7`, deja
          //  livre pour les publications a venir, mais rien ne le retablit sur un
          //  etat deja en base. L'ecran le dit plutot que de le cacher (§7.20).
          <Alerte ton="avertissement" urgence="information">
            Ce bureau est publie avec {b.nombreDeResponsables} responsable
            {b.nombreDeResponsables > 1 ? 's' : ''}, hors de la fourchette attendue d&rsquo;un a
            trois (§8.4).
          </Alerte>
        ) : null}
        {b.responsables.length === 0 ? (
          <Alerte>Aucun responsable pour le moment.</Alerte>
        ) : (
          <ul className="bureau-liste-responsables">
            {b.responsables.map((responsable) => (
              <li key={responsable.identifiant}>
                {responsable.photo === null ? (
                  <span aria-hidden="true" className="bureau-avatar">
                    {responsable.prenom.slice(0, 1)}
                    {responsable.nom.slice(0, 1)}
                  </span>
                ) : (
                  <img alt="" className="bureau-photo" src={responsable.photo} />
                )}
                <span>
                  {responsable.prenom} {responsable.nom}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Carte>

      {retour}
    </div>
  );
}
