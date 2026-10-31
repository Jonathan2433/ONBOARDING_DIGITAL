/**
 * La page detaillee d'un cercle, a l'ecran — LOT 6, `T9`, story `MVP-L06-US002`.
 *
 * LE CRITERE, MOT POUR MOT
 *
 *   « Couleur, description, membres et Booster sont affiches sans reposer
 *   uniquement sur la couleur. »
 *
 * LA COULEUR N'EST JAMAIS LA SEULE INFORMATION, ET C'EST LE COUPLE DU §7.42
 *
 *   `jetonDeCouleur` est nullable au contrat (`circle.color_token`, modele §8.1).
 *   Un cercle sans jeton reste parfaitement lisible : le nom est un `<h2>` en
 *   texte, la couleur ne fait que teinter une bordure. `couleurDuCercle` rend
 *   `undefined` pour un jeton nul OU inconnu, et les deux cas laissent la
 *   bordure neutre — jamais la chaine « None », defaut `T10-8`.
 *
 * LA PAGINATION SUIT LE §18.2, ET LE PARAMETRE VIT EN ETAT LOCAL
 *
 *   Comme le trombinoscope de `T10` du LOT 5 : la page courante n'est pas dans
 *   l'adresse, elle est dans l'etat du composant. Changer de page ne change pas
 *   l'URL de la ressource consultee — un cercle a une seule adresse d'ecran.
 *
 * CHANTIER FRONT, S5 (`DEC-672`) : `CARTE`/`BADGE`
 *
 *   **Mesure avant tout code** : ni `Carte` ni `Badge` n'etaient employes ici —
 *   l'identite du cercle et ses membres vivaient dans un `<article>`/`<dl>`/
 *   `<ul>` ecrits a la main, « Principal »/« Secondaire » en simple texte.
 *   Deux `Carte` (identite, membres) et un `Badge` pour le type d'appartenance.
 *
 *   **La bordure de couleur migre d'un conteneur a l'autre, et ce n'est pas
 *   cosmetique.** `Carte` n'accepte aucune `className` (`ProprietesCarte`,
 *   `packages/ui`) : la variable `--cercle-couleur` ne peut donc plus etre
 *   portee par la carte elle-meme. Elle revient sur un conteneur dedie,
 *   `.cercle-identite`, qui la DECLARE et la CONSOMME — exactement le motif
 *   de `.framework-carte-cercle` — et c'est CE MEME element qui recoit le
 *   style en ligne ci-dessous, jamais un parent ni un enfant.
 *   **Un defaut latent trouve en mesurant, non construit par cette sous-etape**
 *   est corrige au passage : l'ancienne regle (`.cercle-entete`) declarait
 *   deja `--cercle-couleur`, mais sur un element DIFFERENT de celui qui
 *   recevait l'inline (le `<header>` enfant, quand l'inline visait
 *   l'`<article>` parent) — une regle qui cible un element GAGNE toujours
 *   sur un style pose EN LIGNE par un ANCETRE pour la meme propriete. La
 *   bordure coloree ne pouvait donc jamais s'afficher, par aucun cercle, et
 *   aucun test ne l'eprouvait.
 *
 * CHANTIER FRONT, S12 (`DEC-673`) : LA PHOTO DU BOOSTER ET DES MEMBRES
 *
 *   `TitulaireDuCercle.photo` et `MembreDuCercle.photo` suivent exactement la
 *   convention du trombinoscope et du profil (S11) : un cadre hexagonal
 *   (`--decoupe-hexagone`) sur fond de marque colore quand `photo` est `null`,
 *   l'image elle-meme sinon — meme motif, meme initiales, aucune nouvelle
 *   mesure de contraste. Arbitrage de Jonathan (`AskUserQuestion`,
 *   29/10/2026) : la page de synthese Framework reste hors de cette
 *   sous-etape, reportee.
 *
 * CHANTIER FRONT, S13 (`DEC-673`) : LE COMPTEUR DE MEMBRES EN GROS CHIFFRE
 *
 *   Arbitrage de Jonathan (`AskUserQuestion`, 29/10/2026) : seul le compteur
 *   strict — « Membres (N) » — recoit l'accent, jamais la pagination ni un
 *   texte d'etat. `Carte.titre` accepte desormais un `ReactNode` (packages/ui)
 *   pour isoler le nombre dans `.ex-carte__titre-chiffre` sans changer le nom
 *   accessible de la region (`aria-labelledby` lit le texte concatene).
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { couleurDuCercle } from '../affichage';
import { lireLeCercle } from '../api/organisation';
import { cheminDeRubrique, cheminEditionCercle } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import { peutEditerUnContenu, TAILLE_PAR_DEFAUT, type PageDuCercle } from '@onboarding/contracts';
import { Alerte, Badge, Carte } from '@onboarding/ui';

const TAILLE = TAILLE_PAR_DEFAUT;

/** « Principal » ou « Secondaire » — §8.2, la distinction porte des droits (`ARB-DROIT-004`). */
function libelleDAppartenance(type: string): string {
  return type === 'principal' ? 'Principal' : 'Secondaire';
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'page'; readonly page: PageDuCercle }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageCercle(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const { codeCercle } = useParams<{ codeCercle: string }>();
  const [page, setPage] = useState(1);
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    if (codeCercle === undefined) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireLeCercle(entite.code, codeCercle, page, TAILLE, abandon.signal).then(
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
  }, [entite.code, codeCercle, page]);

  const roles = permissions?.roles ?? null;
  //  **REFUS PAR DEFAUT, §20.1** — pas de lien pour une action que l'API
  //  refuserait. `T10` : la portee LOCALE (SON cercle) reste resolue par
  //  l'API seule, ce predicat ne fait que ne pas PROPOSER un lien inutile.
  const peutEditer = roles !== null && peutEditerUnContenu(roles);

  const retour = (
    <p className="cercle-retour">
      <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
        Retour au Framework
      </Link>
      {codeCercle !== undefined && peutEditer ? (
        <>
          {' '}
          ·{' '}
          <Link className="app-lien" to={cheminEditionCercle(entite.code, codeCercle)}>
            Editer ce cercle
          </Link>
        </>
      ) : null}
    </p>
  );

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement du cercle…</Alerte>;
  }

  if (etat.phase === 'erreur') {
    return (
      <>
        <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour consulter ce cercle.'
            : etat.statut === 404
              ? "Ce cercle est introuvable, ou n'est plus actif."
              : "Le cercle n'a pas pu etre charge. Reessayez dans un instant."}
        </Alerte>
        {retour}
      </>
    );
  }

  const c = etat.page;
  const couleur = couleurDuCercle(c.jetonDeCouleur);

  return (
    <div className="cercle">
      <div
        className="cercle-identite"
        style={couleur === undefined ? undefined : ({ '--cercle-couleur': couleur } as never)}
      >
        <Carte titre={c.nom}>
          {c.description === null ? null : <p className="cercle-description">{c.description}</p>}
          <dl className="cercle-champs">
            <dt>Booster</dt>
            <dd>
              {c.booster === null ? (
                'Aucun Booster'
              ) : (
                <span className="cercle-booster">
                  {c.booster.photo === null ? (
                    <span aria-hidden="true" className="cercle-avatar">
                      {c.booster.prenom.slice(0, 1)}
                      {c.booster.nom.slice(0, 1)}
                    </span>
                  ) : (
                    <img alt="" className="cercle-photo" src={c.booster.photo} />
                  )}
                  {c.booster.prenom} {c.booster.nom}
                </span>
              )}
            </dd>
          </dl>
        </Carte>
      </div>

      <Carte
        titre={
          <>
            Membres (<span className="ex-carte__titre-chiffre">{c.totalDesMembres}</span>)
          </>
        }
      >
        {c.membres.length === 0 ? (
          <Alerte>Aucun membre pour le moment.</Alerte>
        ) : (
          <ul className="cercle-liste-membres">
            {c.membres.map((membre) => (
              <li key={membre.appartenance}>
                <span className="cercle-membre-identite">
                  {membre.photo === null ? (
                    <span aria-hidden="true" className="cercle-avatar">
                      {membre.prenom.slice(0, 1)}
                      {membre.nom.slice(0, 1)}
                    </span>
                  ) : (
                    <img alt="" className="cercle-photo" src={membre.photo} />
                  )}
                  <span className="cercle-membre-nom">
                    {membre.prenom} {membre.nom}
                  </span>
                </span>
                <Badge ton={membre.typeDAppartenance === 'principal' ? 'marque' : 'neutre'}>
                  {libelleDAppartenance(membre.typeDAppartenance)}
                </Badge>
              </li>
            ))}
          </ul>
        )}

        {c.pages > 1 ? (
          <nav aria-label="Pagination des membres du cercle" className="cercle-pagination">
            <button
              type="button"
              className="cercle-page"
              disabled={c.page <= 1}
              onClick={() => {
                setPage((precedente) => Math.max(1, precedente - 1));
              }}
            >
              Page precedente
            </button>
            <span className="cercle-position">
              Page {c.page} sur {c.pages}
            </span>
            <button
              type="button"
              className="cercle-page"
              disabled={c.page >= c.pages}
              onClick={() => {
                setPage((precedente) => precedente + 1);
              }}
            >
              Page suivante
            </button>
          </nav>
        ) : null}
      </Carte>

      {retour}
    </div>
  );
}
