/**
 * « Organisation » — créer un collaborateur, le transférer d'entité (seul ou
 * en masse), archiver et restaurer un cercle ou un bureau. LOT 9, `T14`.
 *
 * LES QUATRE RÉFÉRENTIELS SONT RÉSOLUS DEPUIS CE QUI EXISTE DÉJÀ, JAMAIS DEVINÉS
 *
 *   `metier` vient du catalogue des métiers (`T14`, nouvelle lecture posée en
 *   construisant cet écran — voir `app/people/catalogues.py`) ; `cercle_
 *   principal` et `dsm` viennent de `GET …/framework` (les cercles, et les
 *   titulaires de la responsabilité `DSM`) ; `client` vient de
 *   `GET …/clients` (`T8`). Aucun des quatre n'est un identifiant saisi à la
 *   main — la seule exception du lot reste `premier_administrateur`
 *   (Super-administration), faute de toute route listant les personnes
 *   toutes entités confondues.
 *
 * LE CHANGEMENT D'ENTITÉ RÉSOUT SES RÉFÉRENTIELS DANS L'ENTITÉ DE DESTINATION
 *
 *   La nouvelle affectation (métier, cercle, DSM, client) vit dans l'entité
 *   D'ARRIVÉE, pas celle consultée : changer la destination recharge donc
 *   les trois référentiels pour la nouvelle entité, jamais ceux de la
 *   source.
 *
 * LA RESTAURATION D'UN CERCLE OU D'UN BUREAU N'A AUCUNE LISTE À PARCOURIR
 *
 *   `GET …/framework` exclut les ressources archivées (LOT 6), et aucune
 *   route ne liste les cercles/bureaux archivés d'une entité — mesuré,
 *   `T4` du LOT 9 n'a posé que les QUATRE transitions, pas une lecture de
 *   plus. Restaurer exige donc de connaître l'identifiant ; cet écran le
 *   garde en mémoire LE TEMPS DE LA SESSION, juste après un archivage réussi
 *   — un geste plus loin dans le temps reste hors de portée de cet écran,
 *   résidu nommé au compte rendu.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';

import {
  lireLeCatalogueDesMetiers,
  creerUnCollaborateur,
  changerDEntite,
  previsualiserLeTransfertEnMasse,
  executerLeTransfertEnMasse,
} from '../../api/collaborateurs';
import { listerLesClients } from '../../api/imports';
import {
  archiverUnBureau,
  archiverUnCercle,
  lireLeFramework,
  restaurerUnBureau,
  restaurerUnCercle,
} from '../../api/organisation';
import { listerLesEntites } from '../../api/portail';
import { lireLaFiche } from '../../api/profil';
import { listerLeTrombinoscope } from '../../api/trombinoscope';
import {
  peutEcrireSurUnCollaborateur,
  peutGererLeCycleDeVieDeLaStructure,
  TAILLE_PAR_DEFAUT,
  type CatalogueDesMetiers,
  type ElementDeTransfertEnMasse,
  type EntiteDuPortail,
  type PageFramework,
  type ReponseDesClients,
  type ReponseDeTransfertEnMasse,
} from '@onboarding/contracts';
import { Alerte, Bouton } from '@onboarding/ui';

function messageDeRefus(statut: number): string {
  if (statut === 401) {
    return 'Votre session a expiré. Reconnectez-vous, puis recommencez.';
  }
  if (statut === 403) {
    return 'Votre rôle ne permet pas cette action pour cette cible.';
  }
  if (statut === 404) {
    return 'La cible est introuvable, ou hors de votre périmètre.';
  }
  if (statut === 409) {
    return 'Cette ressource a changé d’état depuis votre dernière lecture. Rechargez.';
  }
  if (statut === 422) {
    return 'La demande n’est pas valide. Vérifiez les champs renseignés.';
  }
  return 'L’action n’a pas pu aboutir. Réessayez dans un instant.';
}

/** Les trois référentiels d'UNE entité — métiers, cercles, clients, DSM. */
interface Referentiels {
  readonly metiers: CatalogueDesMetiers;
  readonly framework: PageFramework;
  readonly clients: ReponseDesClients;
}

function useReferentiels(code: string): {
  readonly statut: number;
  readonly corps: Referentiels | null;
} {
  const [etat, setEtat] = useState<{
    readonly statut: number;
    readonly corps: Referentiels | null;
  }>({
    statut: 0,
    corps: null,
  });

  useEffect(() => {
    const abandon = new AbortController();

    async function charger(): Promise<{
      readonly statut: number;
      readonly corps: Referentiels | null;
    }> {
      if (code === '') {
        return { statut: 0, corps: null };
      }
      const [metiers, framework, clients] = await Promise.all([
        lireLeCatalogueDesMetiers(code, abandon.signal),
        lireLeFramework(code, abandon.signal),
        listerLesClients(code, abandon.signal),
      ]);
      if (
        metiers.statut === 200 &&
        metiers.corps !== null &&
        framework.statut === 200 &&
        framework.corps !== null &&
        clients.statut === 200 &&
        clients.corps !== null
      ) {
        return {
          statut: 200,
          corps: { metiers: metiers.corps, framework: framework.corps, clients: clients.corps },
        };
      }
      return { statut: metiers.statut || framework.statut || clients.statut || 0, corps: null };
    }

    void charger().then(setEtat, (cause: unknown) => {
      if (!abandon.signal.aborted) {
        setEtat({ statut: 0, corps: null });
      }
      return cause;
    });
    return () => {
      abandon.abort();
    };
  }, [code]);

  return etat;
}

/** Les champs organisationnels communs à la création ET au changement d'entité. */
interface ChampsOrganisationnels {
  readonly dateDArrivee: string;
  readonly metier: string;
  readonly statut: 'mission' | 'intercontract';
  readonly client: string;
  readonly dsm: string;
  readonly cerclePrincipal: string;
}

function champsVides(): ChampsOrganisationnels {
  return {
    dateDArrivee: '',
    metier: '',
    statut: 'mission',
    client: '',
    dsm: '',
    cerclePrincipal: '',
  };
}

function ChampsOrganisationnelsFormulaire({
  referentiels,
  valeurs,
  onChange,
}: {
  readonly referentiels: Referentiels | null;
  readonly valeurs: ChampsOrganisationnels;
  readonly onChange: (valeurs: ChampsOrganisationnels) => void;
}): JSX.Element {
  const dsmTitulaires =
    referentiels?.framework.responsabilites.find((r) => r.typeDeResponsabilite === 'DSM')
      ?.titulaires ?? [];

  return (
    <>
      <label className="administration-champ">
        Date d’arrivée
        <input
          onChange={(e) => {
            onChange({ ...valeurs, dateDArrivee: e.target.value });
          }}
          type="date"
          value={valeurs.dateDArrivee}
        />
      </label>
      <label className="administration-champ">
        Métier
        <select
          disabled={referentiels === null}
          onChange={(e) => {
            onChange({ ...valeurs, metier: e.target.value });
          }}
          value={valeurs.metier}
        >
          <option value="">— choisir —</option>
          {referentiels?.metiers.metiers.map((m) => (
            <option key={m.identifiant} value={m.identifiant}>
              {m.label}
            </option>
          ))}
        </select>
      </label>
      <label className="administration-champ">
        Statut
        <select
          onChange={(e) => {
            const statut = e.target.value as 'mission' | 'intercontract';
            onChange({
              ...valeurs,
              statut,
              client: statut === 'intercontract' ? '' : valeurs.client,
            });
          }}
          value={valeurs.statut}
        >
          <option value="mission">Mission</option>
          <option value="intercontract">Intercontrat</option>
        </select>
      </label>
      {valeurs.statut === 'intercontract' ? null : (
        <label className="administration-champ">
          Client
          <select
            disabled={referentiels === null}
            onChange={(e) => {
              onChange({ ...valeurs, client: e.target.value });
            }}
            value={valeurs.client}
          >
            <option value="">— choisir —</option>
            {referentiels?.clients.clients.map((c) => (
              <option key={c.identifiant} value={c.identifiant}>
                {c.nomAffiche}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="administration-champ">
        DSM (facultatif)
        <select
          disabled={referentiels === null}
          onChange={(e) => {
            onChange({ ...valeurs, dsm: e.target.value });
          }}
          value={valeurs.dsm}
        >
          <option value="">— aucun —</option>
          {dsmTitulaires.map((t) => (
            <option key={t.identifiant} value={t.identifiant}>
              {t.prenom} {t.nom}
            </option>
          ))}
        </select>
      </label>
      <label className="administration-champ">
        Cercle principal
        <select
          disabled={referentiels === null}
          onChange={(e) => {
            onChange({ ...valeurs, cerclePrincipal: e.target.value });
          }}
          value={valeurs.cerclePrincipal}
        >
          <option value="">— choisir —</option>
          {referentiels?.framework.cercles.map((c) => (
            <option key={c.identifiant} value={c.identifiant}>
              {c.nom}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

function champsCompletes(v: ChampsOrganisationnels): boolean {
  return (
    v.dateDArrivee !== '' &&
    v.metier !== '' &&
    v.cerclePrincipal !== '' &&
    (v.statut === 'intercontract' || v.client !== '')
  );
}

/** Créer un collaborateur — `T2`, `US002` (1/2). */
function FormulaireCreationDeCollaborateur({ code }: { readonly code: string }): JSX.Element {
  const referentiels = useReferentiels(code);
  const [email, setEmail] = useState('');
  const [prenom, setPrenom] = useState('');
  const [nom, setNom] = useState('');
  const [champs, setChamps] = useState<ChampsOrganisationnels>(champsVides());
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  async function creer(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    setSucces(null);
    const resultat = await creerUnCollaborateur(code, {
      email,
      prenom,
      nom,
      date_d_arrivee: champs.dateDArrivee,
      metier: champs.metier,
      statut: champs.statut,
      client: champs.statut === 'intercontract' ? null : champs.client,
      dsm: champs.dsm === '' ? null : champs.dsm,
      cercle_principal: champs.cerclePrincipal,
    });
    setEnvoi(false);
    if (resultat.statut === 201 && resultat.corps !== null) {
      setSucces(`Collaborateur créé (appartenance ${resultat.corps.appartenance}).`);
      setEmail('');
      setPrenom('');
      setNom('');
      setChamps(champsVides());
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  const pretAEnvoyer =
    email.trim() !== '' && prenom.trim() !== '' && nom.trim() !== '' && champsCompletes(champs);

  return (
    <section
      className="administration-creation-collaborateur"
      aria-labelledby="administration-creation-collaborateur-titre"
    >
      <h4 id="administration-creation-collaborateur-titre">Créer un collaborateur</h4>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {succes === null ? null : (
        <Alerte ton="succes" urgence="information">
          {succes}
        </Alerte>
      )}
      <div className="administration-champs">
        <label className="administration-champ">
          E-mail professionnel
          <input
            onChange={(e) => {
              setEmail(e.target.value);
            }}
            type="email"
            value={email}
          />
        </label>
        <label className="administration-champ">
          Prénom
          <input
            onChange={(e) => {
              setPrenom(e.target.value);
            }}
            type="text"
            value={prenom}
          />
        </label>
        <label className="administration-champ">
          Nom
          <input
            onChange={(e) => {
              setNom(e.target.value);
            }}
            type="text"
            value={nom}
          />
        </label>
        <ChampsOrganisationnelsFormulaire
          onChange={setChamps}
          referentiels={referentiels.corps}
          valeurs={champs}
        />
        <Bouton
          disabled={envoi || !pretAEnvoyer}
          onClick={() => {
            void creer();
          }}
          type="button"
          variante="primaire"
        >
          {envoi ? 'Envoi…' : 'Créer le collaborateur'}
        </Bouton>
      </div>
    </section>
  );
}

/** Changer un collaborateur d'entité — `T3`, ferme `US002` (2/2). */
function FormulaireChangementDEntite({ code }: { readonly code: string }): JSX.Element {
  const [recherche, setRecherche] = useState('');
  const [resultats, setResultats] = useState<
    readonly { readonly id: string; readonly prenom: string; readonly nom: string }[]
  >([]);
  const [cible, setCible] = useState<{
    readonly appartenance: string;
    readonly version: number;
    readonly libelle: string;
  } | null>(null);
  const [entiteDestination, setEntiteDestination] = useState('');
  const [entites, setEntites] = useState<readonly EntiteDuPortail[]>([]);
  const champsRef = useReferentiels(entiteDestination);
  const [champs, setChamps] = useState<ChampsOrganisationnels>(champsVides());
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  useEffect(() => {
    const abandon = new AbortController();
    void listerLesEntites(abandon.signal).then((reponse) => {
      if (reponse.statut === 200 && reponse.corps !== null) {
        setEntites(reponse.corps.entites.filter((e) => e.code !== code));
      }
    });
    return () => {
      abandon.abort();
    };
  }, [code]);

  async function rechercher(): Promise<void> {
    const reponse = await listerLeTrombinoscope(code, {
      page: 1,
      taille: TAILLE_PAR_DEFAUT,
      recherche,
      statut: '',
    });
    if (reponse.statut === 200 && reponse.corps !== null) {
      setResultats(
        reponse.corps.collaborateurs.map((c) => ({ id: c.id, prenom: c.prenom, nom: c.nom })),
      );
    }
  }

  async function choisir(appartenance: string, libelle: string): Promise<void> {
    const fiche = await lireLaFiche(code, appartenance);
    if (fiche.statut === 200 && fiche.corps !== null) {
      setCible({ appartenance, version: fiche.corps.version, libelle });
      setErreur(null);
      setSucces(null);
    } else {
      setErreur(messageDeRefus(fiche.statut));
    }
  }

  async function changer(): Promise<void> {
    if (cible === null) {
      return;
    }
    setEnvoi(true);
    setErreur(null);
    setSucces(null);
    const resultat = await changerDEntite(code, cible.appartenance, {
      version: cible.version,
      entite_destination: entiteDestination,
      date_d_arrivee: champs.dateDArrivee,
      metier: champs.metier,
      statut: champs.statut,
      client: champs.statut === 'intercontract' ? null : champs.client,
      dsm: champs.dsm === '' ? null : champs.dsm,
      cercle_principal: champs.cerclePrincipal,
    });
    setEnvoi(false);
    if (resultat.statut === 200 && resultat.corps !== null) {
      setSucces(`${cible.libelle} transféré vers « ${entiteDestination} ».`);
      setCible(null);
      setChamps(champsVides());
      setResultats([]);
      setRecherche('');
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  const pretAEnvoyer = cible !== null && entiteDestination !== '' && champsCompletes(champs);

  return (
    <section
      className="administration-changement-d-entite"
      aria-labelledby="administration-changement-d-entite-titre"
    >
      <h4 id="administration-changement-d-entite-titre">Changer un collaborateur d’entité</h4>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {succes === null ? null : (
        <Alerte ton="succes" urgence="information">
          {succes}
        </Alerte>
      )}
      {cible !== null ? (
        <p>
          Cible choisie : <strong>{cible.libelle}</strong>{' '}
          <Bouton
            onClick={() => {
              setCible(null);
            }}
            type="button"
            variante="secondaire"
          >
            Changer de cible
          </Bouton>
        </p>
      ) : (
        <div className="administration-champs">
          <label className="administration-champ">
            Rechercher un collaborateur de cette entité
            <input
              onChange={(e) => {
                setRecherche(e.target.value);
              }}
              type="text"
              value={recherche}
            />
          </label>
          <Bouton
            onClick={() => {
              void rechercher();
            }}
            type="button"
            variante="secondaire"
          >
            Rechercher
          </Bouton>
          {resultats.length === 0 ? null : (
            <ul>
              {resultats.map((r) => (
                <li key={r.id}>
                  {r.prenom} {r.nom}{' '}
                  <Bouton
                    onClick={() => {
                      void choisir(r.id, `${r.prenom} ${r.nom}`);
                    }}
                    type="button"
                    variante="primaire"
                  >
                    Choisir
                  </Bouton>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {cible === null ? null : (
        <div className="administration-champs">
          <label className="administration-champ">
            Entité de destination
            <select
              onChange={(e) => {
                setEntiteDestination(e.target.value);
                setChamps(champsVides());
              }}
              value={entiteDestination}
            >
              <option value="">— choisir —</option>
              {entites.map((e) => (
                <option key={e.code} value={e.code}>
                  {e.nom}
                </option>
              ))}
            </select>
          </label>
          {entiteDestination === '' ? null : (
            <ChampsOrganisationnelsFormulaire
              onChange={setChamps}
              referentiels={champsRef.corps}
              valeurs={champs}
            />
          )}
          <Bouton
            disabled={envoi || !pretAEnvoyer}
            onClick={() => {
              void changer();
            }}
            type="button"
            variante="primaire"
          >
            {envoi ? 'Envoi…' : 'Changer d’entité'}
          </Bouton>
        </div>
      )}
    </section>
  );
}

interface LigneDeTransfert {
  readonly cle: string;
  readonly appartenance: string;
  readonly version: number;
  readonly libelle: string;
  readonly entiteDestination: string;
  readonly champs: ChampsOrganisationnels;
}

/** Le transfert en masse — `T11`, ferme `US003`. */
function SectionTransfertEnMasse({ code }: { readonly code: string }): JSX.Element {
  const [recherche, setRecherche] = useState('');
  const [resultats, setResultats] = useState<
    readonly { readonly id: string; readonly prenom: string; readonly nom: string }[]
  >([]);
  const [lignes, setLignes] = useState<readonly LigneDeTransfert[]>([]);
  const [entites, setEntites] = useState<readonly EntiteDuPortail[]>([]);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [resultat, setResultat] = useState<ReponseDeTransfertEnMasse | null>(null);

  useEffect(() => {
    const abandon = new AbortController();
    void listerLesEntites(abandon.signal).then((reponse) => {
      if (reponse.statut === 200 && reponse.corps !== null) {
        setEntites(reponse.corps.entites.filter((e) => e.code !== code));
      }
    });
    return () => {
      abandon.abort();
    };
  }, [code]);

  async function rechercher(): Promise<void> {
    const reponse = await listerLeTrombinoscope(code, {
      page: 1,
      taille: TAILLE_PAR_DEFAUT,
      recherche,
      statut: '',
    });
    if (reponse.statut === 200 && reponse.corps !== null) {
      setResultats(
        reponse.corps.collaborateurs.map((c) => ({ id: c.id, prenom: c.prenom, nom: c.nom })),
      );
    }
  }

  async function ajouter(appartenance: string, libelle: string): Promise<void> {
    const fiche = await lireLaFiche(code, appartenance);
    if (fiche.statut === 200 && fiche.corps !== null) {
      setLignes([
        ...lignes,
        {
          cle: appartenance,
          appartenance,
          version: fiche.corps.version,
          libelle,
          entiteDestination: '',
          champs: champsVides(),
        },
      ]);
    }
  }

  function retirer(cle: string): void {
    setLignes(lignes.filter((l) => l.cle !== cle));
  }

  function modifier(cle: string, patch: Partial<LigneDeTransfert>): void {
    setLignes(lignes.map((l) => (l.cle === cle ? { ...l, ...patch } : l)));
  }

  function corps(): { readonly elements: readonly ElementDeTransfertEnMasse[] } {
    return {
      elements: lignes.map((l) => ({
        appartenance: l.appartenance,
        version: l.version,
        entite_destination: l.entiteDestination,
        date_d_arrivee: l.champs.dateDArrivee,
        metier: l.champs.metier,
        statut: l.champs.statut,
        client: l.champs.statut === 'intercontract' ? null : l.champs.client,
        dsm: l.champs.dsm === '' ? null : l.champs.dsm,
        cercle_principal: l.champs.cerclePrincipal,
      })),
    };
  }

  async function previsualiser(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const reponse = await previsualiserLeTransfertEnMasse(code, corps());
    setEnvoi(false);
    if (reponse.statut === 200 && reponse.corps !== null) {
      setResultat(reponse.corps);
    } else {
      setErreur(messageDeRefus(reponse.statut));
    }
  }

  async function executer(): Promise<void> {
    setEnvoi(true);
    setErreur(null);
    const reponse = await executerLeTransfertEnMasse(code, corps());
    setEnvoi(false);
    if (reponse.statut === 200 && reponse.corps !== null) {
      setResultat(reponse.corps);
      setLignes([]);
    } else {
      setErreur(messageDeRefus(reponse.statut));
    }
  }

  const pretAEnvoyer =
    lignes.length > 0 &&
    lignes.every((l) => l.entiteDestination !== '' && champsCompletes(l.champs));

  return (
    <section
      className="administration-transfert-en-masse"
      aria-labelledby="administration-transfert-en-masse-titre"
    >
      <h4 id="administration-transfert-en-masse-titre">Transfert en masse</h4>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      <div className="administration-champs">
        <label className="administration-champ">
          Rechercher un collaborateur à ajouter au lot
          <input
            onChange={(e) => {
              setRecherche(e.target.value);
            }}
            type="text"
            value={recherche}
          />
        </label>
        <Bouton
          onClick={() => {
            void rechercher();
          }}
          type="button"
          variante="secondaire"
        >
          Rechercher
        </Bouton>
        {resultats.length === 0 ? null : (
          <ul>
            {resultats.map((r) => (
              <li key={r.id}>
                {r.prenom} {r.nom}{' '}
                <Bouton
                  disabled={lignes.some((l) => l.appartenance === r.id)}
                  onClick={() => {
                    void ajouter(r.id, `${r.prenom} ${r.nom}`);
                  }}
                  type="button"
                  variante="primaire"
                >
                  Ajouter au lot
                </Bouton>
              </li>
            ))}
          </ul>
        )}
      </div>
      {lignes.length === 0 ? (
        <p>Aucun élément dans le lot.</p>
      ) : (
        <ul className="administration-lot-de-transfert">
          {lignes.map((ligne) => (
            <LigneDeTransfertFormulaire
              code={code}
              entites={entites}
              key={ligne.cle}
              ligne={ligne}
              onModifier={(patch) => {
                modifier(ligne.cle, patch);
              }}
              onRetirer={() => {
                retirer(ligne.cle);
              }}
            />
          ))}
        </ul>
      )}
      <div className="administration-actions">
        <Bouton
          disabled={envoi || !pretAEnvoyer}
          onClick={() => {
            void previsualiser();
          }}
          type="button"
          variante="secondaire"
        >
          {envoi ? 'Envoi…' : 'Aperçu de l’impact'}
        </Bouton>
        <Bouton
          disabled={envoi || !pretAEnvoyer}
          onClick={() => {
            void executer();
          }}
          type="button"
          variante="primaire"
        >
          {envoi ? 'Envoi…' : 'Exécuter le transfert'}
        </Bouton>
      </div>
      {resultat === null ? null : (
        <table className="administration-resultat-du-transfert">
          <thead>
            <tr>
              <th scope="col">Appartenance</th>
              <th scope="col">Résultat</th>
            </tr>
          </thead>
          <tbody>
            {resultat.resultats.map((r) => (
              <tr key={r.appartenance}>
                <td>{r.appartenance}</td>
                <td>{r.succes ? 'Réussi' : (r.messageErreur ?? r.codeErreur ?? 'Échec')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function LigneDeTransfertFormulaire({
  code,
  ligne,
  entites,
  onModifier,
  onRetirer,
}: {
  readonly code: string;
  readonly ligne: LigneDeTransfert;
  readonly entites: readonly EntiteDuPortail[];
  readonly onModifier: (patch: Partial<LigneDeTransfert>) => void;
  readonly onRetirer: () => void;
}): JSX.Element {
  void code;
  const referentiels = useReferentiels(ligne.entiteDestination);
  return (
    <li>
      <strong>{ligne.libelle}</strong>{' '}
      <Bouton onClick={onRetirer} type="button" variante="secondaire">
        Retirer du lot
      </Bouton>
      <label className="administration-champ">
        Entité de destination
        <select
          onChange={(e) => {
            onModifier({ entiteDestination: e.target.value, champs: champsVides() });
          }}
          value={ligne.entiteDestination}
        >
          <option value="">— choisir —</option>
          {entites.map((e) => (
            <option key={e.code} value={e.code}>
              {e.nom}
            </option>
          ))}
        </select>
      </label>
      {ligne.entiteDestination === '' ? null : (
        <ChampsOrganisationnelsFormulaire
          onChange={(champs) => {
            onModifier({ champs });
          }}
          referentiels={referentiels.corps}
          valeurs={ligne.champs}
        />
      )}
    </li>
  );
}

/** Archiver et restaurer un cercle ou un bureau — `T4`, `US008`. */
function SectionCerclesEtBureaux({ code }: { readonly code: string }): JSX.Element {
  const [framework, setFramework] = useState<PageFramework | null>(null);
  const [rechargements, setRechargements] = useState(0);
  const [erreur, setErreur] = useState<string | null>(null);
  const [recemmentArchives, setRecemmentArchives] = useState<
    readonly {
      readonly nature: 'cercle' | 'bureau';
      readonly identifiant: string;
      readonly version: number;
      readonly nom: string;
    }[]
  >([]);

  useEffect(() => {
    const abandon = new AbortController();
    void lireLeFramework(code, abandon.signal).then((reponse) => {
      if (!abandon.signal.aborted && reponse.statut === 200 && reponse.corps !== null) {
        setFramework(reponse.corps);
      }
    });
    return () => {
      abandon.abort();
    };
  }, [code, rechargements]);

  async function archiver(
    nature: 'cercle' | 'bureau',
    id: string,
    version: number,
    nom: string,
  ): Promise<void> {
    setErreur(null);
    const resultat =
      nature === 'cercle'
        ? await archiverUnCercle(code, id, version)
        : await archiverUnBureau(code, id, version);
    if (resultat.statut === 200 && resultat.corps !== null) {
      setRecemmentArchives([
        ...recemmentArchives,
        { nature, identifiant: id, version: resultat.corps.version, nom },
      ]);
      setRechargements((p) => p + 1);
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  async function restaurer(
    nature: 'cercle' | 'bureau',
    id: string,
    version: number,
  ): Promise<void> {
    setErreur(null);
    const resultat =
      nature === 'cercle'
        ? await restaurerUnCercle(code, id, version)
        : await restaurerUnBureau(code, id, version);
    if (resultat.statut === 200 && resultat.corps !== null) {
      setRecemmentArchives(recemmentArchives.filter((r) => r.identifiant !== id));
      setRechargements((p) => p + 1);
    } else {
      setErreur(messageDeRefus(resultat.statut));
    }
  }

  return (
    <section
      className="administration-cercles-et-bureaux"
      aria-labelledby="administration-cercles-et-bureaux-titre"
    >
      <h4 id="administration-cercles-et-bureaux-titre">Cercles et bureaux</h4>
      {erreur === null ? null : (
        <Alerte ton="erreur" urgence="alerte">
          {erreur}
        </Alerte>
      )}
      {framework === null ? (
        <p>Chargement…</p>
      ) : (
        <>
          <h5>Cercles</h5>
          <ul>
            {framework.cercles.map((c) => (
              <li key={c.identifiant}>
                {c.nom} ({c.membresActifs} membre(s) actif(s))
                <Bouton
                  disabled={c.membresActifs > 0}
                  onClick={() => {
                    //  La version n'est pas servie par le Framework : `T4` exige
                    //  un `version` qu'on ne connaît pas ici. Un cercle sans
                    //  écrivain n'en a connu aucune — `1` est la version initiale
                    //  de toute ressource jamais modifiée (modele §25.1).
                    void archiver('cercle', c.identifiant, 1, c.nom);
                  }}
                  type="button"
                  variante="secondaire"
                >
                  Archiver
                </Bouton>
              </li>
            ))}
          </ul>
          <h5>Bureaux</h5>
          <ul>
            {framework.bureaux.map((b) => (
              <li key={b.identifiant}>
                {b.nom}
                <Bouton
                  onClick={() => {
                    void archiver('bureau', b.identifiant, 1, b.nom);
                  }}
                  type="button"
                  variante="secondaire"
                >
                  Archiver
                </Bouton>
              </li>
            ))}
          </ul>
        </>
      )}
      {recemmentArchives.length === 0 ? null : (
        <>
          <h5>Récemment archivés (cette session)</h5>
          <ul>
            {recemmentArchives.map((r) => (
              <li key={r.identifiant}>
                {r.nom} ({r.nature})
                <Bouton
                  onClick={() => {
                    void restaurer(r.nature, r.identifiant, r.version);
                  }}
                  type="button"
                  variante="primaire"
                >
                  Restaurer
                </Bouton>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export function SectionOrganisation({
  code,
  roles,
}: {
  readonly code: string;
  readonly roles: readonly string[] | null;
}): JSX.Element {
  const peutEcrire = peutEcrireSurUnCollaborateur(roles);
  const peutGererLaStructure = peutGererLeCycleDeVieDeLaStructure(roles);

  if (!peutEcrire && !peutGererLaStructure) {
    return <p>Votre rôle ne porte aucun droit d’écriture sur ce groupe.</p>;
  }

  return (
    <div className="administration-organisation">
      {!peutEcrire ? null : <FormulaireCreationDeCollaborateur code={code} />}
      {!peutEcrire ? null : <FormulaireChangementDEntite code={code} />}
      {!peutEcrire ? null : <SectionTransfertEnMasse code={code} />}
      {!peutGererLaStructure ? null : <SectionCerclesEtBureaux code={code} />}
    </div>
  );
}
