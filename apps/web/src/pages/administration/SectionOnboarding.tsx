/**
 * « Onboarding » — le groupe du cahier §10.8, déjà construit par LOT 7 `T14`.
 *
 * EXTRAIT TEL QUEL DE L'ANCIENNE `PageAdministration.tsx` MONOLITHIQUE — LOT 9, `T14`
 *
 *   Le catalogue des tâches et les modèles d'onboarding n'ont AUCUNE règle
 *   changée ici : `T14` du LOT 9 ne fait que les déplacer sous un onglet
 *   nommé, parmi les sept groupes du cahier. Le suivi des tâches en retard
 *   est déplacé sous « Pilotage » (cahier §10.8 : rapports), qui est son
 *   groupe propre — ce n'est pas un hasard de rangement, c'est la même
 *   section qui change de voisinage.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import {
  archiverUneVersionDeModele,
  creerUneTacheDeReference,
  creerUneVersionDeModele,
  creerUnModeleOnboarding,
  definirLesTachesDeVersion,
  lireLeCatalogueDeTaches,
  lireLesModelesOnboarding,
  publierUneVersionDeModele,
  restaurerUneVersionDeModele,
} from '../../api/administration';
import {
  ROLES_ADMINISTRATION_ONBOARDING,
  ROLES_RESTAURATION_DES_MODELES_ONBOARDING,
  type CatalogueDeTaches,
  type ModeleOnboardingAvecVersions,
  type PageDesModelesOnboarding,
  type TacheDeReference,
  type VersionDeModeleOnboarding,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

export function peutGererLOnboarding(roles: readonly string[] | null): boolean {
  return roles !== null && roles.some((role) => ROLES_ADMINISTRATION_ONBOARDING.includes(role));
}

function peutRestaurerUneVersion(roles: readonly string[] | null): boolean {
  return (
    roles !== null && roles.some((role) => ROLES_RESTAURATION_DES_MODELES_ONBOARDING.includes(role))
  );
}

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre rôle ne permet pas cette action dans cette entité.';
  }
  if (statut === 409) {
    return 'Cette ressource a changé d’état depuis votre dernière lecture. Rechargez la page.';
  }
  if (statut === 422) {
    return 'La demande n’est pas valide. Vérifiez les champs renseignés.';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

const LIBELLES_D_ETAT_DE_VERSION: Readonly<Record<string, string>> = {
  draft: 'Brouillon',
  published: 'Publiée',
  retired: 'Archivée',
};

/** Le catalogue des tâches de référence — matrice §9, ferme `ECART-013`. */
function SectionCatalogue({
  code,
  catalogue,
  onCree,
}: {
  readonly code: string;
  readonly catalogue: CatalogueDeTaches;
  readonly onCree: () => void;
}): JSX.Element {
  const [codeDeTravail, setCodeDeTravail] = useState('');
  const [titreDeTravail, setTitreDeTravail] = useState('');
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function creer(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat = await creerUneTacheDeReference(code, {
      code: codeDeTravail,
      title: titreDeTravail,
      portee: 'ENTITE',
    });
    setEnvoi(false);
    if (resultat.statut === 201 && resultat.corps !== null) {
      setCodeDeTravail('');
      setTitreDeTravail('');
      onCree();
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <section className="administration-catalogue" aria-labelledby="administration-catalogue-titre">
      <h3 id="administration-catalogue-titre">Catalogue des tâches</h3>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {catalogue.taches.length === 0 ? (
        <p>Aucune tâche de référence pour le moment.</p>
      ) : (
        <ul className="administration-liste-du-catalogue">
          {catalogue.taches.map((tache) => (
            <li key={tache.identifiant}>
              <strong>{tache.code}</strong> — {tache.titre}
              {tache.entiteId === null ? <em> (globale)</em> : null}
            </li>
          ))}
        </ul>
      )}
      <div className="administration-champs">
        <label className="administration-champ" htmlFor="catalogue-code">
          Code (identifiant stable)
          <input
            id="catalogue-code"
            onChange={(evenement) => {
              setCodeDeTravail(evenement.target.value);
            }}
            type="text"
            value={codeDeTravail}
          />
        </label>
        <label className="administration-champ" htmlFor="catalogue-titre">
          Titre
          <input
            id="catalogue-titre"
            onChange={(evenement) => {
              setTitreDeTravail(evenement.target.value);
            }}
            type="text"
            value={titreDeTravail}
          />
        </label>
        <Bouton
          disabled={envoi || codeDeTravail.trim() === '' || titreDeTravail.trim() === ''}
          onClick={() => {
            void creer();
          }}
          type="button"
          variante="primaire"
        >
          {envoi ? 'Envoi…' : 'Créer une tâche de référence'}
        </Bouton>
      </div>
    </section>
  );
}

/** Une version, ses tâches et son cycle de vie — matrice §9. */
function CarteDeVersion({
  code,
  modele,
  version,
  catalogue,
  peutRestaurer,
  onAgi,
}: {
  readonly code: string;
  readonly modele: string;
  readonly version: VersionDeModeleOnboarding;
  readonly catalogue: CatalogueDeTaches;
  readonly peutRestaurer: boolean;
  readonly onAgi: () => void;
}): JSX.Element {
  const [ligne, setLigne] = useState<
    readonly { readonly reference: string; readonly jours: number }[]
  >([]);
  const [referenceDeTravail, setReferenceDeTravail] = useState('');
  const [joursDeTravail, setJoursDeTravail] = useState(0);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function agir(
    action: 'taches' | 'publication' | 'archivage' | 'restauration',
  ): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat =
      action === 'taches'
        ? await definirLesTachesDeVersion(code, modele, version.id, {
            taches: ligne.map((l) => ({
              task_reference_id: l.reference,
              required: true,
              due_offset_days: l.jours,
            })),
          })
        : action === 'publication'
          ? await publierUneVersionDeModele(code, modele, version.id)
          : action === 'archivage'
            ? await archiverUneVersionDeModele(code, modele, version.id)
            : await restaurerUneVersionDeModele(code, modele, version.id);
    setEnvoi(false);
    if (resultat.statut === 200 && resultat.corps !== null) {
      onAgi();
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <li className="administration-version">
      <span className="administration-version-numero">Version {version.numero}</span>{' '}
      <span className="administration-version-etat">
        {LIBELLES_D_ETAT_DE_VERSION[version.etat] ?? version.etat}
      </span>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {version.etat === 'draft' ? (
        <div className="administration-composition">
          {ligne.length === 0 ? null : (
            <ul>
              {ligne.map((l, rang) => {
                const tache = catalogue.taches.find((t) => t.identifiant === l.reference);
                return (
                  <li key={`${l.reference}-${String(rang)}`}>
                    {tache?.titre ?? l.reference} — J+{l.jours}
                  </li>
                );
              })}
            </ul>
          )}
          <label>
            Tâche du catalogue
            <select
              onChange={(evenement) => {
                setReferenceDeTravail(evenement.target.value);
              }}
              value={referenceDeTravail}
            >
              <option value="">— choisir —</option>
              {catalogue.taches.map((tache: TacheDeReference) => (
                <option key={tache.identifiant} value={tache.identifiant}>
                  {tache.titre}
                </option>
              ))}
            </select>
          </label>
          <label>
            Échéance (jours après l’arrivée)
            <input
              min={0}
              onChange={(evenement) => {
                setJoursDeTravail(Number(evenement.target.value));
              }}
              type="number"
              value={joursDeTravail}
            />
          </label>
          <Bouton
            disabled={referenceDeTravail === ''}
            onClick={() => {
              setLigne([...ligne, { reference: referenceDeTravail, jours: joursDeTravail }]);
              setReferenceDeTravail('');
              setJoursDeTravail(0);
            }}
            type="button"
            variante="secondaire"
          >
            Ajouter à la liste
          </Bouton>
          <div className="administration-actions">
            <Bouton
              disabled={envoi || ligne.length === 0}
              onClick={() => {
                void agir('taches');
              }}
              type="button"
              variante="secondaire"
            >
              {envoi ? 'Envoi…' : 'Enregistrer les tâches'}
            </Bouton>
            <Bouton
              disabled={envoi}
              onClick={() => {
                void agir('publication');
              }}
              type="button"
              variante="primaire"
            >
              Publier cette version
            </Bouton>
          </div>
        </div>
      ) : version.etat === 'published' ? (
        <div className="administration-actions">
          <Bouton
            disabled={envoi}
            onClick={() => {
              void agir('archivage');
            }}
            type="button"
            variante="secondaire"
          >
            Archiver cette version
          </Bouton>
        </div>
      ) : peutRestaurer ? (
        <div className="administration-actions">
          <Bouton
            disabled={envoi}
            onClick={() => {
              void agir('restauration');
            }}
            type="button"
            variante="secondaire"
          >
            Restaurer cette version
          </Bouton>
        </div>
      ) : null}
    </li>
  );
}

/** Un modèle et ses versions — matrice §9, modèle §13.2 à §13.4. */
function CarteDeModele({
  code,
  modele,
  catalogue,
  peutRestaurer,
  onAgi,
}: {
  readonly code: string;
  readonly modele: ModeleOnboardingAvecVersions;
  readonly catalogue: CatalogueDeTaches;
  readonly peutRestaurer: boolean;
  readonly onAgi: () => void;
}): JSX.Element {
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function nouvelleVersion(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat = await creerUneVersionDeModele(code, modele.id, {});
    setEnvoi(false);
    if (resultat.statut === 201 && resultat.corps !== null) {
      onAgi();
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <li className="administration-modele">
      <h4>{modele.nom}</h4>
      <p>
        Portée : {modele.portee} — Statut cible : {modele.statutCible}
      </p>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {modele.versions.length === 0 ? (
        <p>Aucune version pour le moment.</p>
      ) : (
        <ul className="administration-liste-des-versions">
          {modele.versions.map((version) => (
            <CarteDeVersion
              key={version.id}
              catalogue={catalogue}
              code={code}
              modele={modele.id}
              onAgi={onAgi}
              peutRestaurer={peutRestaurer}
              version={version}
            />
          ))}
        </ul>
      )}
      <Bouton
        disabled={envoi}
        onClick={() => {
          void nouvelleVersion();
        }}
        type="button"
        variante="secondaire"
      >
        {envoi ? 'Envoi…' : 'Créer une nouvelle version'}
      </Bouton>
    </li>
  );
}

/** Les modèles gérés par l'appelant, dans son propre périmètre — matrice §9. */
function SectionModeles({
  code,
  modeles,
  catalogue,
  peutRestaurer,
  onAgi,
}: {
  readonly code: string;
  readonly modeles: PageDesModelesOnboarding;
  readonly catalogue: CatalogueDeTaches;
  readonly peutRestaurer: boolean;
  readonly onAgi: () => void;
}): JSX.Element {
  const [nomDeTravail, setNomDeTravail] = useState('');
  const [statutCibleDeTravail, setStatutCibleDeTravail] = useState<'mission' | 'intercontract'>(
    'mission',
  );
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function creer(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const resultat = await creerUnModeleOnboarding(code, {
      name: nomDeTravail,
      target_status: statutCibleDeTravail,
      portee: 'ENTITY',
    });
    setEnvoi(false);
    if (resultat.statut === 201 && resultat.corps !== null) {
      setNomDeTravail('');
      onAgi();
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <section className="administration-modeles" aria-labelledby="administration-modeles-titre">
      <h3 id="administration-modeles-titre">Modèles d’onboarding</h3>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {modeles.modeles.length === 0 ? (
        <p>Aucun modèle pour le moment.</p>
      ) : (
        <ul className="administration-liste-des-modeles">
          {modeles.modeles.map((modele) => (
            <CarteDeModele
              key={modele.id}
              catalogue={catalogue}
              code={code}
              modele={modele}
              onAgi={onAgi}
              peutRestaurer={peutRestaurer}
            />
          ))}
        </ul>
      )}
      <div className="administration-champs">
        <label className="administration-champ" htmlFor="modele-nom">
          Nom du modèle
          <input
            id="modele-nom"
            onChange={(evenement) => {
              setNomDeTravail(evenement.target.value);
            }}
            type="text"
            value={nomDeTravail}
          />
        </label>
        <label className="administration-champ" htmlFor="modele-statut-cible">
          Statut cible
          <select
            id="modele-statut-cible"
            onChange={(evenement) => {
              setStatutCibleDeTravail(evenement.target.value as 'mission' | 'intercontract');
            }}
            value={statutCibleDeTravail}
          >
            <option value="mission">Mission</option>
            <option value="intercontract">Intercontrat</option>
          </select>
        </label>
        <Bouton
          disabled={envoi || nomDeTravail.trim() === ''}
          onClick={() => {
            void creer();
          }}
          type="button"
          variante="primaire"
        >
          {envoi ? 'Envoi…' : 'Créer un modèle (portée : entité)'}
        </Bouton>
      </div>
    </section>
  );
}

interface Chargement {
  readonly catalogue: { readonly statut: number; readonly corps: CatalogueDeTaches | null } | null;
  readonly modeles: {
    readonly statut: number;
    readonly corps: PageDesModelesOnboarding | null;
  } | null;
}

/** Le groupe « Onboarding » — catalogue des tâches et modèles, LOT 7 `T14`. */
export function SectionOnboarding({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const gereOnboarding = peutGererLOnboarding(roles);
  const restaure = peutRestaurerUneVersion(roles);
  const [charge, setCharge] = useState<Chargement | null>(null);
  const [rechargements, setRechargements] = useState(0);

  useEffect(() => {
    const abandon = new AbortController();

    async function charger(): Promise<Chargement> {
      const [modeles, catalogue] = await Promise.all([
        gereOnboarding ? lireLesModelesOnboarding(code, abandon.signal) : Promise.resolve(null),
        gereOnboarding ? lireLeCatalogueDeTaches(code, abandon.signal) : Promise.resolve(null),
      ]);
      return {
        modeles: modeles === null ? null : { statut: modeles.statut, corps: modeles.corps },
        catalogue: catalogue === null ? null : { statut: catalogue.statut, corps: catalogue.corps },
      };
    }

    void charger().then(setCharge, (cause: unknown) => {
      if (!abandon.signal.aborted) {
        setCharge({
          modeles: gereOnboarding ? { statut: 0, corps: null } : null,
          catalogue: gereOnboarding ? { statut: 0, corps: null } : null,
        });
      }
      return cause;
    });
    return () => {
      abandon.abort();
    };
  }, [code, gereOnboarding, rechargements]);

  if (!gereOnboarding) {
    return <p>Votre rôle ne porte aucun droit de gestion sur ce groupe.</p>;
  }

  if (charge === null) {
    return (
      <p className="administration-chargement" role="status">
        Chargement de l’onboarding…
      </p>
    );
  }

  function recharger(): void {
    setRechargements((precedent) => precedent + 1);
  }

  const { catalogue, modeles } = charge;

  return (
    <div className="administration-onboarding">
      {catalogue !== null && catalogue.statut === 200 && catalogue.corps !== null ? (
        <SectionCatalogue catalogue={catalogue.corps} code={code} onCree={recharger} />
      ) : (
        <Alerte ton={catalogue?.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          Le catalogue des tâches n’a pas pu être chargé. Réessayez dans un instant.
        </Alerte>
      )}
      {modeles !== null &&
      modeles.statut === 200 &&
      modeles.corps !== null &&
      catalogue !== null &&
      catalogue.corps !== null ? (
        <SectionModeles
          catalogue={catalogue.corps}
          code={code}
          modeles={modeles.corps}
          onAgi={recharger}
          peutRestaurer={restaure}
        />
      ) : (
        <Alerte ton={modeles?.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          Les modèles d’onboarding n’ont pas pu être chargés. Réessayez dans un instant.
        </Alerte>
      )}
    </div>
  );
}
