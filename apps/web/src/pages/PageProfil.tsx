/**
 * La fiche profil a l'ecran — LOT 5, `T11`, stories `MVP-L05-US004` et `US008`.
 *
 * LE CRITERE ECRIT DANS LA FICHE DU LOT ETAIT DEJA SATISFAIT, ET C'EST MESURE
 *
 *   La fiche donne a `T11` : « chaque composant livre est **employe** · contraste
 *   mesure ». Or `make cadre-check` rendait, sur `develop` et avant qu'une ligne
 *   de `T11` ne soit ecrite : « les 6 composants exportes sont TESTES et
 *   EMPLOYES ». Un critere qu'une sous-etape vide satisferait ne borne rien --
 *   §7.39, troisieme fois dans ce lot.
 *
 *   Le perimetre vient donc du **libelle** de la fiche — « la page de profil a
 *   l'ecran » — et du critere du backlog : « Metier, statut, client, DSM,
 *   cercles, responsabilites, presentation et fun fact respectent les regles de
 *   visibilite ».
 *
 * AUCUN CHAMP N'EST MASQUE, ET CE N'EST PAS UN OUBLI
 *
 *   `ECART-051` : « regles de visibilite » ne parait que dans les deux copies du
 *   critere de `US004` lui-meme ; le seul « masquer » de la matrice porte sur les
 *   ACTIONS, et le §5 donne « Fiches collaborateur » en Lecture aux HUIT roles
 *   authentifies. Inventer un masquage par champ aurait ete le §6.5.
 *
 *   **Les champs facultatifs le sont parce que la DONNEE peut manquer**, jamais
 *   parce qu'un role ne la verrait pas. « Non renseigne » dit donc ce qui est
 *   vrai, et l'ecran n'ecrit nulle part « vous n'avez pas acces a ce champ ».
 *
 * L'ENTITE VIENT DU CADRE, PAS DE L'API
 *
 *   Le §10.2 liste « entite » parmi les champs du profil, et la route ne la sert
 *   pas : elle est dans l'ADRESSE, et le cadre l'a deja resolue. L'ajouter a la
 *   charge utile ferait servir deux fois la meme donnee, dont une copie
 *   pourrait vieillir.
 *
 * L'HISTORIQUE EST UN SECOND APPEL, ET SES REFUS SONT NORMAUX
 *
 *   La fiche releve du §5 « Fiches collaborateur », en Lecture pour les huit
 *   roles. L'historique releve de la ligne « Audit » du meme §5, qui REFUSE `EMP`
 *   et `NEW`. **Un employe voit donc la fiche et se voit refuser l'historique**,
 *   et l'ecran doit le dire sans donner l'impression d'une panne.
 *
 *   **`null` N'EST PAS `[]`, ET L'ECRAN NE LES CONFOND PAS** : `null` rend « hors
 *   de votre perimetre », `[]` rend « aucune periode ». Les afficher pareil
 *   ferait croire a un DSM que son consultant n'a jamais porte de responsabilite.
 *
 * LES DATES SONT FORMATEES SANS `Date`, ET C'EST DELIBERE
 *
 *   L'API sert de l'ISO 8601 en **UTC**. `new Date('2026-01-01T00:00:00Z')` lu
 *   avec `getMonth()` rend **decembre** a Paris : une periode close le 1er janvier
 *   deviendrait close en decembre. Les segments sont donc lus dans la CHAINE, ce
 *   qui est exact et ne depend d'aucun ICU -- `toLocaleDateString` varie avec la
 *   version de Node, et un test qui en dependrait mesurerait la machine.
 *
 * CHANTIER FRONT, S6 (`DEC-672`) : `CARTE`/`BADGE`
 *
 *   **Mesure avant tout code** : aucun des cinq blocs (identite, informations
 *   professionnelles, cercles, responsabilites, presentation, historique) ne
 *   vivait dans une `Carte` -- chacun etait une `<section className="profil-bloc">`
 *   ecrite a la main. Le statut de l'en-tete et le type de responsabilite
 *   portaient DEJA un `Badge` (LOT 5 `T11`) ; seul le type d'appartenance d'un
 *   cercle (« Principal »/« Secondaire ») restait un `<span>` de texte simple --
 *   l'exact pendant de ce que `S5` a corrige sur `PageCercle.tsx` pour la meme
 *   notion, et traite ici de la meme facon (`Badge ton="marque"` pour Principal,
 *   `ton="neutre"` pour Secondaire).
 *
 *   **Le niveau de titre est explicite, et ce n'est pas un detail.** L'identite
 *   (le nom de la personne) garde le niveau par defaut de `Carte`, `h2` : c'est
 *   le titre du document. Les cinq blocs qui suivent passent `niveauTitre="h3"`
 *   -- ils etaient deja des `<h3>`, SOUS ce `h2`, et laisser `Carte` imposer son
 *   defaut aurait APLATI une hierarchie correcte en sept `h2` freres. `Carte`
 *   expose `niveauTitre` precisement pour ce cas, documente dans son propre
 *   en-tete (« une carte imbriquee dans une section plus profonde »).
 *
 *   `PanneauDuCycleDeVie` partageait `.profil-bloc` par un commentaire explicite
 *   (« Le bloc reprend `.profil-bloc` ») : il devient lui aussi une `Carte`, pour
 *   la meme raison -- sans quoi la derniere section de la page resterait seule
 *   dans l'ancien habillage, a cote de cinq `Carte`.
 */
import type { JSX, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { couleurDuCercle, libelleDuStatut } from '../affichage';
import { lireLaFicheArchivee } from '../api/cycleDeVie';
import { lireLaFiche, lireLHistorique } from '../api/profil';
import { cheminDeRubrique } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { PanneauDuCycleDeVie } from './PanneauDuCycleDeVie';
import { PanneauPhoto } from './PanneauPhoto';

import {
  AXES_DE_L_HISTORIQUE,
  type AxeDeLHistorique,
  type CercleDuProfil,
  type FicheDuProfil,
  type HistoriqueOrganisationnel,
  peutGererLeCycleDeVie,
} from '@onboarding/contracts';
import { Alerte, Badge, Carte } from '@onboarding/ui';

/** Les douze mois, en toutes lettres. Aucune dependance a l'ICU de la machine. */
const MOIS: readonly string[] = [
  'janvier',
  'fevrier',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'aout',
  'septembre',
  'octobre',
  'novembre',
  'decembre',
];

/**
 * « juin 2025 » a partir d'une chaine ISO, SANS passer par `Date`.
 *
 * Une periode se lit au mois : le jour exact d'un changement de cercle n'apporte
 * rien, et l'afficher ferait croire a une precision que la saisie n'a pas.
 */
export function moisAnnee(iso: string): string {
  const annee = iso.slice(0, 4);
  const mois = Number(iso.slice(5, 7));
  const libelle = MOIS[mois - 1];
  //  Une chaine que l'API ne devrait jamais servir : mieux vaut la montrer que
  //  rendre « undefined 2025 », qui ferait chercher un defaut d'affichage.
  return libelle === undefined ? iso : `${libelle} ${annee}`;
}

/** « 8 septembre 2025 » — la date d'arrivee, elle, se lit au jour. §10.2. */
export function dateComplete(iso: string): string {
  const jour = Number(iso.slice(8, 10));
  const mois = MOIS[Number(iso.slice(5, 7)) - 1];
  return mois === undefined ? iso : `${String(jour)} ${mois} ${iso.slice(0, 4)}`;
}

/** Le nom affiche : le nom prefere quand il existe, sinon le prenom. §10.2. */
export function nomDeLaFiche(fiche: FicheDuProfil): string {
  return `${fiche.nomPrefere ?? fiche.prenom} ${fiche.nom}`;
}

/** Une periode : « juin 2025 → aujourd'hui » quand elle est courante. */
function intervalle(debut: string, fin: string | null): string {
  return `${moisAnnee(debut)} → ${fin === null ? 'aujourd’hui' : moisAnnee(fin)}`;
}

/** Ce que la page a pu charger. `null` tant qu'aucune reponse n'est arrivee. */
interface Chargement {
  readonly appartenance: string;
  readonly fiche: { readonly statut: number; readonly corps: FicheDuProfil | null };
  readonly histoire: { readonly statut: number; readonly corps: HistoriqueOrganisationnel | null };
  /** Vrai quand la fiche vient de `fiche-archivee` — voir l'effet de chargement. */
  readonly archive: boolean;
}

/** Une ligne de definition, avec son repli « Non renseigne ». */
function Champ({ nom, children }: { nom: string; children: ReactNode }): JSX.Element {
  return (
    <>
      <dt>{nom}</dt>
      <dd>{children ?? 'Non renseigne'}</dd>
    </>
  );
}

/**
 * Un cercle : le NOM en toutes lettres, la couleur en bordure seule.
 *
 * §10.1 : « jamais comme seul moyen de transmettre une information ». Un jeton
 * inconnu — ou nul, `color_token` etant nullable au schema, defaut `T10-8` —
 * laisse la bordure neutre, et le nom reste lisible.
 *
 * **LA PROPRIETE S'APPELLE `nature`, ET `jsx-a11y` L'A IMPOSE.** Je l'avais
 * nommee `role` : la regle `aria-role` s'en est plainte, et elle a raison -- le
 * jour ou ce composant diffuserait ses proprietes sur un noeud DOM,
 * `role="Principal"` deviendrait un role ARIA invalide. C'est exactement le
 * garde-fou qui a motive `DEC-451`, et le desactiver aurait ete le mauvais
 * remede.
 */
function Cercle({ cercle, nature }: { cercle: CercleDuProfil; nature: string }): JSX.Element {
  const couleur = couleurDuCercle(cercle.jetonDeCouleur);
  return (
    <li
      className="profil-cercle"
      style={couleur === undefined ? undefined : ({ '--profil-cercle': couleur } as never)}
    >
      <span className="profil-cercle-nom">{cercle.nom}</span>
      <Badge ton={nature === 'Principal' ? 'marque' : 'neutre'}>{nature}</Badge>
    </li>
  );
}

/** Le titre francais de chaque axe, et l'ordre de la route. */
const TITRES_D_AXE: Readonly<Record<AxeDeLHistorique, string>> = {
  metier: 'Metiers',
  statut: 'Situations',
  cercle: 'Cercles',
  dsm: 'DSM',
  responsabilites: 'Responsabilites',
};

/** Le libelle d'une periode, par axe. Une seule fonction : les cinq formes y sont visibles. */
function libelleDePeriode(axe: AxeDeLHistorique, periode: Record<string, unknown>): string {
  switch (axe) {
    case 'metier':
      return String(periode['metier']);
    case 'statut': {
      const client = periode['client'];
      const statut = libelleDuStatut(String(periode['statut'])) ?? '';
      return client === null ? statut : `${statut} — ${String(client)}`;
    }
    case 'cercle':
      return `${String(periode['nom'])} (${String(periode['type'])})`;
    case 'dsm':
      return String(periode['dsm']);
    case 'responsabilites': {
      const portee = periode['cercle'] ?? periode['bureau'];
      return portee === null || portee === undefined
        ? String(periode['type'])
        : `${String(periode['type'])} — ${String(portee)}`;
    }
  }
}

/**
 * Un axe de l'historique.
 *
 * **TROIS ETATS, ET LES TROIS SONT DISTINCTS** : des periodes · `[]`, « aucune
 * periode enregistree » · `null`, « hors de votre perimetre ». Le troisieme est
 * le §20 de la matrice, que le §23.2 fait prevaloir sur le cumul des roles.
 */
function AxeDeLHistoire({
  axe,
  periodes,
}: {
  axe: AxeDeLHistorique;
  periodes: readonly Record<string, unknown>[] | null;
}): JSX.Element {
  return (
    <section className="profil-axe">
      <h3>{TITRES_D_AXE[axe]}</h3>
      {periodes === null ? (
        <p className="profil-hors-perimetre">
          Hors de votre perimetre : votre role ne donne pas acces a cet historique.
        </p>
      ) : periodes.length === 0 ? (
        <p className="profil-vide">Aucune periode enregistree.</p>
      ) : (
        <ul className="profil-periodes">
          {periodes.map((periode, rang) => (
            <li key={`${axe}-${String(rang)}`}>
              <span className="profil-periode-libelle">{libelleDePeriode(axe, periode)}</span>
              <span className="profil-periode-bornes">
                {intervalle(String(periode['debut']), (periode['fin'] as string | null) ?? null)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function PageProfil(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const { appartenance } = useParams<{ appartenance: string }>();
  const [charge, setCharge] = useState<Chargement | null>(null);
  //  **UN COMPTEUR, ET NON UN BOOLEEN.** Apres une action du cycle de vie, la
  //  page doit RECHARGER : un booleen ne pourrait le faire qu'une fois, et
  //  archiver puis restaurer dans la meme visite est exactement ce qu'on veut
  //  pouvoir faire.
  const [rechargements, setRechargements] = useState(0);

  //  `roles` est `null` tant que les permissions ne sont pas arrivees, et le
  //  panneau ne montre alors RIEN -- plutot qu'un bouton qui apparaitrait puis
  //  disparaitrait selon la reponse.
  const roles = permissions?.roles ?? null;
  const gereLeCycleDeVie = roles !== null && peutGererLeCycleDeVie(roles);

  useEffect(() => {
    if (appartenance === undefined) {
      return undefined;
    }
    //  **UNE LIAISON LOCALE PLUTOT QU'UNE ASSERTION.** TypeScript ne propage pas
    //  le retrecissement de `appartenance` dans la fonction imbriquee ; un
    //  `as string` le ferait taire sans rien prouver, une constante le lui
    //  DEMONTRE.
    const cible = appartenance;
    const abandon = new AbortController();

    async function charger(): Promise<Chargement> {
      //  **LES DEUX APPELS PARTENT ENSEMBLE.** Enchainer ferait attendre
      //  l'historique pour rien : ses refus ne dependent pas de la fiche, et un
      //  employe recoit legitimement un 200 puis un 403.
      const [fiche, histoire] = await Promise.all([
        lireLaFiche(entite.code, cible, abandon.signal),
        lireLHistorique(entite.code, cible, abandon.signal),
      ]);
      //  **UN 404 PEUT VOULOIR DIRE « ARCHIVE », ET SEUL UN TROISIEME APPEL LE
      //  DIT.** Le §6.1 donne « consulter un profil ACTIF » aux huit roles et
      //  « consulter un profil ARCHIVE » a trois : la route de la fiche exclut
      //  donc les archives, et rend le MEME 404 que pour une cible inexistante.
      //
      //  Le tenter n'apprend rien a qui n'y a pas droit -- `fiche-archivee`
      //  porte sa propre grille et rend 403 ou 404 -- et on ne le tente que
      //  lorsque le role le permet, pour ne pas faire un appel dont la reponse
      //  est connue d'avance.
      if (fiche.statut === 404 && gereLeCycleDeVie) {
        const archivee = await lireLaFicheArchivee(entite.code, cible, abandon.signal);
        if (archivee.statut === 200 && archivee.corps !== null) {
          return {
            appartenance: cible,
            fiche: { statut: 200, corps: archivee.corps },
            histoire: { statut: histoire.statut, corps: histoire.corps },
            archive: true,
          };
        }
      }
      return {
        appartenance: cible,
        fiche: { statut: fiche.statut, corps: fiche.corps },
        histoire: { statut: histoire.statut, corps: histoire.corps },
        archive: false,
      };
    }

    void charger().then(setCharge, (cause: unknown) => {
      if (!abandon.signal.aborted) {
        setCharge({
          appartenance: cible,
          fiche: { statut: 0, corps: null },
          histoire: { statut: 0, corps: null },
          archive: false,
        });
      }
      return cause;
    });
    return () => {
      abandon.abort();
    };
  }, [entite.code, appartenance, gereLeCycleDeVie, rechargements]);

  const retour = (
    <p className="profil-retour">
      <Link className="app-lien" to={cheminDeRubrique(entite.code, 'trombinoscope')}>
        Retour au trombinoscope
      </Link>
    </p>
  );

  //  **LE CHARGEMENT EST DERIVE, IL N'EST PAS UN ETAT POSE** -- defaut `T10-1`,
  //  ou un `setState` synchrone dans un effet declenchait des rendus en cascade.
  if (charge === null || charge.appartenance !== appartenance) {
    return (
      <section className="profil">
        <p className="profil-chargement" role="status">
          Chargement du profil…
        </p>
      </section>
    );
  }

  const { fiche, histoire } = charge;
  if (fiche.statut !== 200 || fiche.corps === null) {
    return (
      <section className="profil">
        {/*
          **`ton` ET `urgence` SONT DEUX AXES, ET JE LES AVAIS CONFONDUS** : le
          premier donne la couleur, le second le `role` ARIA. Un echec de
          chargement doit s'ANNONCER — `urgence="alerte"` pose `role="alert"` —
          la ou le refus d'historique plus bas est une information normale.
        */}
        <Alerte ton={fiche.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {fiche.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour consulter ce profil.'
            : fiche.statut === 404
              ? //  **QUATRE CAUSES, UN SEUL MESSAGE, ET C'EST VOULU.** Distinguer
                //  « ce profil n'existe pas » de « il est hors de votre
                //  perimetre » apprendrait a un DSM de qui il n'est pas
                //  responsable.
                'Ce profil est introuvable, ou il n’est pas dans votre perimetre.'
              : 'Le profil n’a pas pu etre charge. Reessayez dans un instant.'}
        </Alerte>
        {retour}
      </section>
    );
  }

  const p = fiche.corps;
  const nom = nomDeLaFiche(p);
  const statut = libelleDuStatut(p.statut);

  return (
    <article className="profil">
      <Carte titre={nom}>
        <div className="profil-identite">
          {/*
            **L'AVATAR NEUTRE EST UN `<img>` ABSENT, PAS UNE IMAGE CASSEE** — §21.2,
            et les cinq causes d'absence sont indistinguables a dessein. L'alternative
            textuelle est vide : le nom est juste a cote, et un `alt` qui le
            repeterait le ferait annoncer deux fois.
          */}
          {p.photo === null ? (
            <span aria-hidden="true" className="profil-avatar">
              {(p.nomPrefere ?? p.prenom).slice(0, 1)}
              {p.nom.slice(0, 1)}
            </span>
          ) : (
            <img alt="" className="profil-photo" src={p.photo} />
          )}
          <div className="profil-titre">
            <p className="profil-metier">{p.metier ?? 'Metier non renseigne'}</p>
            {statut === null ? null : <Badge ton="marque">{statut}</Badge>}
          </div>
        </div>
        {charge.archive ? null : (
          //  **AUCUN DEPOT SUR UN PROFIL ARCHIVE** : la fiche archivee (`lire_
          //  la_fiche_archivee`) n'a pas de fiche d'arrivee a interroger, et le
          //  depot d'une photo pour un profil clos n'a aucun sens — LOT 11, `T2`.
          <PanneauPhoto
            appartenance={p.id}
            codeEntite={entite.code}
            surSucces={() => {
              setRechargements((n) => n + 1);
            }}
          />
        )}
      </Carte>

      {charge.archive ? (
        //  **DIRE QU'IL EST ARCHIVE AVANT TOUT LE RESTE.** Sans ce bandeau, la
        //  fiche d'un archive est indistinguable de celle d'un actif : les memes
        //  dix-sept champs, les memes cercles -- et l'affectation qu'on y lit a
        //  ete CLOTUREE. C'est le §7.21 applique a un ecran : une information
        //  juste hier peut etre trompeuse aujourd'hui.
        <Alerte ton="avertissement" urgence="information">
          Ce profil est <strong>archive</strong>. Il ne parait plus dans le trombinoscope, et ses
          affectations ont ete cloturees.
        </Alerte>
      ) : null}

      <Carte niveauTitre="h3" titre="Informations professionnelles">
        {/*
          **NI LE METIER NI LE STATUT NE SONT REPETES ICI**, et c'est un test qui
          l'a dit : il en comptait TROIS occurrences a l'ecran -- l'en-tete, ce
          bloc, et l'axe de l'historique. L'en-tete les porte, sous le nom, ou ils
          identifient la personne d'un coup d'oeil ; les redire trois lignes plus
          bas n'ajoute rien et fait douter qu'il s'agisse de la meme donnee.
        */}
        <dl className="profil-champs">
          <Champ nom="Entite">{entite.nom}</Champ>
          <Champ nom="Client">{p.client}</Champ>
          <Champ nom="DSM">{p.dsm}</Champ>
          <Champ nom="Date d’arrivee">{dateComplete(p.dateArrivee)}</Champ>
        </dl>
      </Carte>

      <Carte niveauTitre="h3" titre="Cercles">
        {p.cerclePrincipal === null && p.cerclesSecondaires.length === 0 ? (
          <p className="profil-vide">Aucun cercle.</p>
        ) : (
          <ul className="profil-cercles">
            {p.cerclePrincipal === null ? null : (
              <Cercle cercle={p.cerclePrincipal} nature="Principal" />
            )}
            {p.cerclesSecondaires.map((cercle) => (
              <Cercle cercle={cercle} key={cercle.code} nature="Secondaire" />
            ))}
          </ul>
        )}
      </Carte>

      <Carte niveauTitre="h3" titre="Responsabilites Framework">
        {p.responsabilites.length === 0 ? (
          <p className="profil-vide">Aucune responsabilite.</p>
        ) : (
          <ul className="profil-responsabilites">
            {p.responsabilites.map((r) => (
              <li key={`${r.type}-${r.cercle ?? r.bureau ?? ''}`}>
                <Badge ton="neutre">{r.type}</Badge>
                {/*
                  §8.4 : `cercle` et `bureau` s'excluent — un BOOSTER porte sur un
                  cercle, un OFFICE_MANAGER sur un bureau. La base l'impose.
                */}
                {r.cercle ?? r.bureau ?? null}
              </li>
            ))}
          </ul>
        )}
      </Carte>

      <Carte niveauTitre="h3" titre="Presentation">
        <dl className="profil-champs">
          <Champ nom="Presentation courte">{p.presentation}</Champ>
          <Champ nom="Fun fact">{p.funFact}</Champ>
        </dl>
      </Carte>

      <Carte niveauTitre="h3" titre="Historique organisationnel">
        {histoire.statut === 200 && histoire.corps !== null ? (
          //  **LES AXES SONT DERIVES DU CONTRAT, PAS ECRITS ICI** : un sixieme axe
          //  ajoute cote API apparaitrait sans qu'on y pense -- §7.27.
          AXES_DE_L_HISTORIQUE.map((axe) => (
            <AxeDeLHistoire
              axe={axe}
              key={axe}
              periodes={
                (histoire.corps?.[axe] as readonly Record<string, unknown>[] | null | undefined) ??
                null
              }
            />
          ))
        ) : (
          <Alerte ton="neutre" urgence="information">
            {histoire.statut === 403
              ? 'Votre role ne donne pas acces a l’historique organisationnel.'
              : histoire.statut === 404
                ? 'L’historique de ce profil n’est pas dans votre perimetre.'
                : 'L’historique n’a pas pu etre charge.'}
          </Alerte>
        )}
      </Carte>

      <PanneauDuCycleDeVie
        appartenance={p.id}
        archive={charge.archive}
        codeEntite={entite.code}
        roles={roles}
        version={p.version}
        surSucces={() => {
          setRechargements((n) => n + 1);
        }}
      />

      {retour}
    </article>
  );
}
