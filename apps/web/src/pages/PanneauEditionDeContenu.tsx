/**
 * Editer une page de contenu — LOT 6, `T10`, `MVP-L06-US004` (3/3).
 *
 * CE QUE CET ECRAN NE FAIT PAS, ET C'EST DELIBERE — `QO-121`
 *
 *   Le corpus ne nomme AUCUN champ de `payload_json` pour aucun des onze types
 *   de bloc du `DEC-577` : ni ce qu'un « texte », un « titre » ou une « carte de
 *   lien » doivent porter, ni ce que « texte riche limite » borne. L'inventer
 *   serait §6.5 — une hypothese deguisee en decision est pire qu'une case vide.
 *
 *   **CET ECRAN NE PROPOSE DONC AUCUN FORMULAIRE DE CREATION D'UN NOUVEAU
 *   BLOC.** Il permet de RE-ORDONNER et de RETIRER les blocs EXISTANTS — ce qui
 *   ne suppose rien de leurs champs — et affiche leur contenu tel quel, en JSON
 *   brut plutot que sous une forme qui pretendrait en connaitre le sens.
 *   L'ajout d'un bloc arrive quand `QO-121` sera tranchee par Lea.
 *
 * LA LISTE REMPLACE LA LISTE, COTE API — ET C'EST CE QUE CET ECRAN RESPECTE
 *
 *   `PUT …/contenu` archive tout bloc absent de la liste envoyee (modele §2.4).
 *   Reordonner ou retirer un bloc est donc une modification LOCALE tant que
 *   « Enregistrer » n'a pas ete confirme — rien n'est perdu avant ce geste, et
 *   rien ne s'enregistre sans lui.
 *
 * LE FRONTEND N'EST PAS L'AUTORITE
 *
 *   Comme partout ailleurs (matrice §2.6) : les predicats `peutXxx` de
 *   `@onboarding/contracts` servent a ne pas PROPOSER une action que l'API
 *   refuserait, jamais a la garantir. La portee LOCALE — le Booster de SON
 *   cercle — n'est resolue que par l'API : un role suffisant peut donc recevoir
 *   un 403 malgre un bouton visible, et cet ecran le rapporte tel quel.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import {
  agirSurLeContenu,
  creerUnePage,
  ecrireLeContenu,
  lireLesPagesDeGestion,
  lireUnePagePourGestion,
  type ActionSurLeContenu,
} from '../api/gestionDuContenu';

import {
  peutCreerUnContenu,
  peutEditerUnContenu,
  peutRestaurerUnContenu,
  type BlocDeContenu,
  type DemandeDeCreationDePage,
  type PageDeContenuPourEdition,
  type PageDeGestion,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

export interface ProprietesEdition {
  readonly codeEntite: string;
  readonly roles: readonly string[] | null;
  /** Quelle page de la liste de gestion correspond a CETTE ressource — un cercle, un bureau. */
  readonly cibleCorrespond: (page: PageDeGestion) => boolean;
  /** Ce qui est envoye si aucune page n'existe encore. */
  readonly demandeDeCreation: DemandeDeCreationDePage;
}

interface BlocDeTravail {
  readonly identifiant: string;
  readonly typeDeBloc: string;
  readonly contenu: Readonly<Record<string, unknown>>;
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'aucune-page' }
  | { readonly phase: 'creation-en-cours' }
  | {
      readonly phase: 'page';
      readonly donnee: PageDeContenuPourEdition;
      readonly titreDeTravail: string;
      readonly blocsDeTravail: readonly BlocDeTravail[];
      readonly enregistrement: 'repos' | 'envoi';
    }
  | { readonly phase: 'erreur'; readonly statut: number };

function versBlocsDeTravail(blocs: readonly BlocDeContenu[]): BlocDeTravail[] {
  return blocs.map((b) => ({
    identifiant: b.identifiant,
    typeDeBloc: b.typeDeBloc,
    contenu: b.contenu,
  }));
}

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expire. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre role ne permet pas cette action sur cette page.';
  }
  if (statut === 409) {
    return 'Cette page a change depuis votre derniere lecture. Rechargez avant de reessayer.';
  }
  if (statut === 404) {
    return 'Cette page est introuvable, ou hors de votre perimetre.';
  }
  return "L'action n'a pas pu aboutir. Reessayez dans un instant.";
}

const LIBELLES_D_ETAT: Readonly<Record<string, string>> = {
  draft: 'Brouillon',
  published: 'Publiee',
  archived: 'Archivee',
};

export function PanneauEditionDeContenu({
  codeEntite,
  roles,
  cibleCorrespond,
  demandeDeCreation,
}: ProprietesEdition): JSX.Element | null {
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    const abandon = new AbortController();

    //  **N'APPELLE MEME PAS `/pages/gestion` SANS ROLE EDITORIAL.** La route
    //  est gardee par `ROLES_D_ECRITURE_EDITORIALE` cote API (garde_d_ecriture) :
    //  un appel sans ce role serait refuse en 403 a coup sur. Le tenter quand
    //  meme gaspillerait une requete et, surtout, afficherait un « Chargement… »
    //  — role ARIA `status` — a un lecteur qui n'a RIEN a faire ici : le §20.1
    //  est le refus par defaut, jusqu'a la requete elle-meme.
    if (roles === null || !peutEditerUnContenu(roles)) {
      return undefined;
    }

    async function charger(): Promise<void> {
      const liste = await lireLesPagesDeGestion(codeEntite, abandon.signal);
      if (abandon.signal.aborted) {
        return;
      }
      if (liste.statut !== 200 || liste.corps === null) {
        setEtat({ phase: 'erreur', statut: liste.statut });
        return;
      }
      const trouvee = liste.corps.pages.find(cibleCorrespond);
      if (trouvee === undefined) {
        setEtat({ phase: 'aucune-page' });
        return;
      }
      const detail = await lireUnePagePourGestion(codeEntite, trouvee.identifiant, abandon.signal);
      if (abandon.signal.aborted) {
        return;
      }
      if (detail.statut !== 200 || detail.corps === null) {
        setEtat({ phase: 'erreur', statut: detail.statut });
        return;
      }
      setEtat({
        phase: 'page',
        donnee: detail.corps,
        titreDeTravail: detail.corps.titre,
        blocsDeTravail: versBlocsDeTravail(detail.corps.blocs),
        enregistrement: 'repos',
      });
    }

    void charger().catch((cause: unknown) => {
      if (!abandon.signal.aborted) {
        setEtat({ phase: 'erreur', statut: 0 });
      }
      return cause;
    });

    return () => {
      abandon.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `cibleCorrespond` change a chaque rendu (fermeture)
  }, [codeEntite, roles]);

  async function recharger(identifiantPage: string): Promise<void> {
    const detail = await lireUnePagePourGestion(codeEntite, identifiantPage);
    if (detail.statut === 200 && detail.corps !== null) {
      setEtat({
        phase: 'page',
        donnee: detail.corps,
        titreDeTravail: detail.corps.titre,
        blocsDeTravail: versBlocsDeTravail(detail.corps.blocs),
        enregistrement: 'repos',
      });
    } else {
      setEtat({ phase: 'erreur', statut: detail.statut });
    }
  }

  async function creer(): Promise<void> {
    setEtat({ phase: 'creation-en-cours' });
    const cree = await creerUnePage(codeEntite, demandeDeCreation);
    if (cree.statut === 201 && cree.corps !== null) {
      await recharger(cree.corps.identifiant);
    } else {
      setEtat({ phase: 'erreur', statut: cree.statut });
    }
  }

  //  **MEME REFUS PAR DEFAUT QUE L'EFFET CI-DESSUS, ET C'EST LA MEME REGLE
  //  DEUX FOIS POUR DEUX RAISONS DIFFERENTES** : la n'appelle pas une route
  //  refusee, ici n'affiche RIEN — ni bouton, ni etat de chargement — a un
  //  role qui n'a aucune action possible sur cette page (§20.1).
  if (roles === null || !peutEditerUnContenu(roles)) {
    return null;
  }

  if (etat.phase === 'chargement' || etat.phase === 'creation-en-cours') {
    return <Alerte urgence="information">Chargement…</Alerte>;
  }

  if (etat.phase === 'erreur') {
    return (
      <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {messageDeRefus(etat.statut)}
      </Alerte>
    );
  }

  if (etat.phase === 'aucune-page') {
    if (!peutCreerUnContenu(roles)) {
      //  **REFUS PAR DEFAUT, §20.1** — pas de bouton pour une action refusee.
      return <Alerte urgence="information">Aucun contenu editorial pour le moment.</Alerte>;
    }
    return (
      <section className="edition-panneau">
        <Alerte urgence="information">Aucun contenu editorial pour le moment.</Alerte>
        <Bouton
          onClick={() => {
            void creer();
          }}
          type="button"
          variante="primaire"
        >
          Creer la page
        </Bouton>
      </section>
    );
  }

  const { donnee, titreDeTravail, blocsDeTravail, enregistrement } = etat;
  const peutEditer = peutEditerUnContenu(roles);
  const peutRestaurer = peutRestaurerUnContenu(roles);

  function definirLesBlocs(nouveaux: readonly BlocDeTravail[]): void {
    setEtat({ phase: 'page', donnee, titreDeTravail, blocsDeTravail: nouveaux, enregistrement });
  }

  function monter(rang: number): void {
    if (rang <= 0) {
      return;
    }
    const copie = [...blocsDeTravail];
    const bloc = copie[rang];
    const precedent = copie[rang - 1];
    if (bloc === undefined || precedent === undefined) {
      return;
    }
    copie[rang - 1] = bloc;
    copie[rang] = precedent;
    definirLesBlocs(copie);
  }

  function descendre(rang: number): void {
    monter(rang + 1);
  }

  function retirer(rang: number): void {
    definirLesBlocs(blocsDeTravail.filter((_, i) => i !== rang));
  }

  async function enregistrer(): Promise<void> {
    setEtat({ phase: 'page', donnee, titreDeTravail, blocsDeTravail, enregistrement: 'envoi' });
    const resultat = await ecrireLeContenu(codeEntite, donnee.identifiant, {
      version: donnee.version,
      titre: titreDeTravail,
      blocs: blocsDeTravail.map((b) => ({ type_de_bloc: b.typeDeBloc, contenu: b.contenu })),
    });
    if (resultat.statut === 200 && resultat.corps !== null) {
      setEtat({
        phase: 'page',
        donnee: { ...donnee, version: resultat.corps.version, blocs: resultat.corps.blocs },
        titreDeTravail,
        blocsDeTravail: versBlocsDeTravail(resultat.corps.blocs),
        enregistrement: 'repos',
      });
    } else {
      setEtat({ phase: 'erreur', statut: resultat.statut });
    }
  }

  async function agir(action: ActionSurLeContenu): Promise<void> {
    const resultat = await agirSurLeContenu(action, codeEntite, donnee.identifiant, donnee.version);
    if (resultat.statut === 200 && resultat.corps !== null) {
      await recharger(donnee.identifiant);
    } else {
      setEtat({ phase: 'erreur', statut: resultat.statut });
    }
  }

  const aModifie =
    titreDeTravail !== donnee.titre ||
    blocsDeTravail.length !== donnee.blocs.length ||
    blocsDeTravail.some((b, i) => b.identifiant !== donnee.blocs[i]?.identifiant);

  return (
    <section className="edition-panneau">
      <p className="edition-etat">
        Etat : <strong>{LIBELLES_D_ETAT[donnee.etat] ?? donnee.etat}</strong>
        {' — version '}
        {donnee.version}
      </p>

      {peutEditer ? (
        <>
          <label className="edition-champ" htmlFor="edition-titre">
            Titre
            <input
              id="edition-titre"
              onChange={(evenement) => {
                setEtat({
                  phase: 'page',
                  donnee,
                  titreDeTravail: evenement.target.value,
                  blocsDeTravail,
                  enregistrement,
                });
              }}
              type="text"
              value={titreDeTravail}
            />
          </label>

          <div className="edition-blocs">
            <h3>Blocs ({blocsDeTravail.length})</h3>
            <Alerte urgence="information">
              L&rsquo;ajout d&rsquo;un nouveau bloc arrive quand le vocabulaire de ses champs sera
              tranche (QO-121). Vous pouvez reordonner ou retirer les blocs existants.
            </Alerte>
            {blocsDeTravail.length === 0 ? (
              <p>Aucun bloc.</p>
            ) : (
              <ol className="edition-liste-blocs">
                {blocsDeTravail.map((bloc, rang) => (
                  <li key={bloc.identifiant} className="edition-bloc">
                    <span className="edition-bloc-type">{bloc.typeDeBloc}</span>
                    <pre className="edition-bloc-apercu">{JSON.stringify(bloc.contenu)}</pre>
                    <div className="edition-bloc-actions">
                      <button
                        disabled={rang === 0}
                        onClick={() => {
                          monter(rang);
                        }}
                        type="button"
                      >
                        Monter
                      </button>
                      <button
                        disabled={rang === blocsDeTravail.length - 1}
                        onClick={() => {
                          descendre(rang);
                        }}
                        type="button"
                      >
                        Descendre
                      </button>
                      <button
                        onClick={() => {
                          retirer(rang);
                        }}
                        type="button"
                      >
                        Retirer
                      </button>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <Bouton
            disabled={!aModifie || enregistrement === 'envoi'}
            onClick={() => {
              void enregistrer();
            }}
            type="button"
            variante="primaire"
          >
            {enregistrement === 'envoi' ? 'Enregistrement…' : 'Enregistrer'}
          </Bouton>
        </>
      ) : null}

      <div className="edition-cycle-de-vie">
        {donnee.etat === 'draft' && peutEditer ? (
          <Bouton
            onClick={() => {
              void agir('publication');
            }}
            type="button"
            variante="secondaire"
          >
            Publier
          </Bouton>
        ) : null}
        {(donnee.etat === 'draft' || donnee.etat === 'published') && peutEditer ? (
          <Bouton
            onClick={() => {
              void agir('archivage');
            }}
            type="button"
            variante="secondaire"
          >
            Archiver
          </Bouton>
        ) : null}
        {donnee.etat === 'archived' && peutRestaurer ? (
          <Bouton
            onClick={() => {
              void agir('restauration');
            }}
            type="button"
            variante="secondaire"
          >
            Restaurer
          </Bouton>
        ) : null}
      </div>
    </section>
  );
}
