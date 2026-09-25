/**
 * Gerer les liens internes de l'entite, a l'ecran — LOT 6, `T10`,
 * `MVP-L06-US005`.
 *
 * DEUX POPULATIONS, UNE SEULE ROUTE DE LECTURE — `T8`
 *
 *   L'accueil ne sert que les liens ACTIFS ; cette route sert LES DEUX, sans
 *   quoi desactiver un lien serait un aller sans retour. Un lien inactif reste
 *   donc visible ICI, marque comme tel, pour pouvoir etre reactive.
 *
 * DESACTIVER N'EST PAS ARCHIVER
 *
 *   Le modele §15.3 declare `active` a cote de `archived_at` : on desactive
 *   pour retirer de l'affichage sans perdre la definition. **Aucune route
 *   n'archive un lien** (§13, §19), donc cet ecran ne propose pas de
 *   suppression — seulement une case a cocher « Actif ».
 *
 * L'ICONE EST UN TEXTE LIBRE — `QO-123`
 *
 *   Voir `../icones.tsx`. Aucune convention n'est tranchee (bibliotheque
 *   choisie : `lucide-react`, mais l'obligation, le vocabulaire et le lien
 *   entre type de lien et icone restent a Lea). Le champ reste donc un texte
 *   libre, avec un apercu qui ne fait rien sur un nom inconnu.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import {
  creerUnLien,
  lireLesLiensPourGestion,
  modifierUnLien,
  reordonnerLesLiens,
} from '../api/gestionDesLiens';
import { IconeDeLien } from '../icones';
import { useEntiteConsultee } from './CadreApplicatif';

import {
  peutGererLesLiensInternes,
  TYPES_DE_LIEN_NOMMES,
  type DemandeDeChampsDeLien,
  type LienInterne,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'liste'; readonly liens: readonly LienInterne[] }
  | { readonly phase: 'erreur'; readonly statut: number };

const CHAMPS_VIDES = {
  libelle: '',
  url: '',
  type_de_lien: 'OTHER',
  description: '',
  reference_d_icone: '',
};

/**
 * `exactOptionalPropertyTypes` refuse `{ description: undefined }` : un champ
 * facultatif ABSENT n'est pas un champ present a `undefined`. Cette fonction
 * n'inclut la clef que lorsque la valeur est reellement fournie.
 */
function champsDeLien(
  base: Omit<DemandeDeChampsDeLien, 'description' | 'reference_d_icone'>,
  description: string,
  referenceDIcone: string,
): DemandeDeChampsDeLien {
  return {
    ...base,
    ...(description === '' ? {} : { description }),
    ...(referenceDIcone === '' ? {} : { reference_d_icone: referenceDIcone }),
  };
}

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expire. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre role ne permet pas de gerer les liens de cette entite.';
  }
  if (statut === 409) {
    return 'Ce lien a change depuis votre derniere lecture. Rechargez avant de reessayer.';
  }
  if (statut === 422) {
    return "L'adresse n'est pas acceptee : seul https, avec un hote, est autorise.";
  }
  return "L'action n'a pas pu aboutir. Reessayez dans un instant.";
}

export function PageGestionDesLiens(): JSX.Element | null {
  const { entite, permissions } = useEntiteConsultee();
  const codeEntite = entite.code;
  const roles = permissions?.roles ?? null;
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });
  const [formulaireOuvert, setFormulaireOuvert] = useState(false);
  const [nouveau, setNouveau] = useState(CHAMPS_VIDES);
  const [erreurEnvoi, setErreurEnvoi] = useState<string | null>(null);

  useEffect(() => {
    const abandon = new AbortController();
    void lireLesLiensPourGestion(codeEntite, abandon.signal).then(
      (reponse) => {
        if (abandon.signal.aborted) {
          return;
        }
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'liste', liens: reponse.corps.liens }
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
  }, [codeEntite]);

  if (roles === null) {
    return null;
  }
  if (!peutGererLesLiensInternes(roles)) {
    //  **REFUS PAR DEFAUT, §20.1.** Cet ecran n'est propose a personne d'autre.
    return (
      <Alerte urgence="information">Vous n&rsquo;avez pas de droit de gestion des liens.</Alerte>
    );
  }

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement des liens…</Alerte>;
  }
  if (etat.phase === 'erreur') {
    return (
      <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
        {messageDeRefus(etat.statut)}
      </Alerte>
    );
  }

  const liens = etat.liens;

  async function recharger(): Promise<void> {
    const reponse = await lireLesLiensPourGestion(codeEntite);
    if (reponse.statut === 200 && reponse.corps !== null) {
      setEtat({ phase: 'liste', liens: reponse.corps.liens });
    } else {
      setEtat({ phase: 'erreur', statut: reponse.statut });
    }
  }

  async function deplacer(rang: number, delta: 1 | -1): Promise<void> {
    const cible = rang + delta;
    if (cible < 0 || cible >= liens.length) {
      return;
    }
    const ordre = liens.map((l) => l.identifiant);
    const echange = ordre[rang];
    const autre = ordre[cible];
    if (echange === undefined || autre === undefined) {
      return;
    }
    ordre[rang] = autre;
    ordre[cible] = echange;
    setErreurEnvoi(null);
    const resultat = await reordonnerLesLiens(codeEntite, { ordre });
    if (resultat.statut === 200 && resultat.corps !== null) {
      setEtat({ phase: 'liste', liens: resultat.corps.liens });
    } else {
      setErreurEnvoi(messageDeRefus(resultat.statut));
    }
  }

  async function basculerActif(lien: LienInterne): Promise<void> {
    setErreurEnvoi(null);
    const resultat = await modifierUnLien(codeEntite, lien.identifiant, {
      ...champsDeLien(
        { libelle: lien.libelle, url: lien.url, type_de_lien: lien.typeDeLien, actif: !lien.actif },
        lien.description ?? '',
        lien.referenceDIcone ?? '',
      ),
      version: lien.version,
    });
    if (resultat.statut === 200) {
      await recharger();
    } else {
      setErreurEnvoi(messageDeRefus(resultat.statut));
    }
  }

  async function creer(): Promise<void> {
    setErreurEnvoi(null);
    if (nouveau.libelle === '' || nouveau.url === '') {
      setErreurEnvoi('Le libelle et l’adresse sont obligatoires.');
      return;
    }
    const resultat = await creerUnLien(
      codeEntite,
      champsDeLien(
        {
          libelle: nouveau.libelle,
          url: nouveau.url,
          type_de_lien: nouveau.type_de_lien,
          actif: true,
        },
        nouveau.description,
        nouveau.reference_d_icone,
      ),
    );
    if (resultat.statut === 201) {
      setNouveau(CHAMPS_VIDES);
      setFormulaireOuvert(false);
      await recharger();
    } else {
      setErreurEnvoi(messageDeRefus(resultat.statut));
    }
  }

  return (
    <section className="liens-gestion">
      {erreurEnvoi === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreurEnvoi}
        </Alerte>
      )}

      {liens.length === 0 ? (
        <Alerte urgence="information">Aucun lien pour le moment.</Alerte>
      ) : (
        <ol className="liens-liste">
          {liens.map((lien, rang) => (
            <li key={lien.identifiant} className="liens-lien" data-actif={String(lien.actif)}>
              <span className="liens-lien-icone">
                <IconeDeLien reference={lien.referenceDIcone} />
              </span>
              <div className="liens-lien-details">
                <span className="liens-lien-libelle">{lien.libelle}</span>
                <span className="liens-lien-url">{lien.url}</span>
              </div>
              <div className="liens-lien-actions">
                <button disabled={rang === 0} onClick={() => void deplacer(rang, -1)} type="button">
                  Monter
                </button>
                <button
                  disabled={rang === liens.length - 1}
                  onClick={() => void deplacer(rang, 1)}
                  type="button"
                >
                  Descendre
                </button>
                <button
                  onClick={() => {
                    void basculerActif(lien);
                  }}
                  type="button"
                >
                  {lien.actif ? 'Desactiver' : 'Activer'}
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      {formulaireOuvert ? (
        <form
          className="liens-formulaire"
          onSubmit={(evenement) => {
            evenement.preventDefault();
            void creer();
          }}
        >
          <label htmlFor="lien-libelle">
            Libelle
            <input
              id="lien-libelle"
              onChange={(e) => {
                setNouveau({ ...nouveau, libelle: e.target.value });
              }}
              required
              type="text"
              value={nouveau.libelle}
            />
          </label>
          <label htmlFor="lien-url">
            Adresse (https uniquement)
            <input
              id="lien-url"
              onChange={(e) => {
                setNouveau({ ...nouveau, url: e.target.value });
              }}
              required
              type="text"
              value={nouveau.url}
            />
          </label>
          <label htmlFor="lien-type">
            Type
            <select
              id="lien-type"
              onChange={(e) => {
                setNouveau({ ...nouveau, type_de_lien: e.target.value });
              }}
              value={nouveau.type_de_lien}
            >
              {TYPES_DE_LIEN_NOMMES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="lien-icone">
            Icone (nom lucide-react, ex. link, book-open — facultatif)
            <input
              id="lien-icone"
              onChange={(e) => {
                setNouveau({ ...nouveau, reference_d_icone: e.target.value });
              }}
              type="text"
              value={nouveau.reference_d_icone}
            />
          </label>
          <div className="liens-formulaire-actions">
            <Bouton type="submit" variante="primaire">
              Creer le lien
            </Bouton>
            <Bouton
              onClick={() => {
                setFormulaireOuvert(false);
                setNouveau(CHAMPS_VIDES);
              }}
              type="button"
              variante="secondaire"
            >
              Annuler
            </Bouton>
          </div>
        </form>
      ) : (
        <Bouton
          onClick={() => {
            setFormulaireOuvert(true);
          }}
          type="button"
          variante="secondaire"
        >
          Nouveau lien
        </Bouton>
      )}
    </section>
  );
}
