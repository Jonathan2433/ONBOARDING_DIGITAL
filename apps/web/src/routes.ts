/**
 * Les HUIT ecrans d'authentification — LOT 3, sous-etape `T11`.
 *
 * LE COMPTE EST DERIVE, PAS RECOPIE
 *
 *   Le cahier §17.5 et la roadmap du LOT 3 donnent la meme liste, en **six
 *   puces**, dont la derniere en nomme **trois** :
 *
 *       page de connexion ; confirmation de demande de lien ;
 *       lien expire ou deja consomme ; connexion administrateur ;
 *       deconnexion ; pages `403`, `404` et erreur generale.
 *
 *   Soit 5 + 3 = **huit**. Les deux documents concordent, et le compte est verifie
 *   par un test qui relit le cahier -- §7.27, une liste recopiee vieillit.
 *
 * UN ECRAN N'EST PAS UNE ROUTE, ET LA DISTINCTION COMPTE
 *
 *   « lien expire ou deja consomme » est un **etat** de la route qui consomme le
 *   lien, pas une adresse distincte : le lien de l'e-mail ouvre `/connexion/lien`,
 *   cette page appelle l'API, et **c'est son echec qui est l'ecran**. Le corpus
 *   enumere des ecrans ; les compter en routes en donnerait sept ou neuf selon
 *   l'humeur.
 *
 * LA RACINE N'EST PAS DANS CETTE LISTE
 *
 *   `/` sert la page de statut de `T5` du LOT 1, et `make web-check` l'exige. Elle
 *   n'appartient pas au LOT 3.
 */

/**
 * Les chemins, source unique lue par le routeur, les tests et le controle.
 *
 * **`entite` PORTE UN PARAMETRE, ET C'EST LA DECISION DE `T2`.** L'entite
 * consultee vit dans l'ADRESSE, parce que le cahier fait atterrir sur la page
 * nationale apres connexion (§4.1, §8.1, §9.1, §9.2) : une memoire du dernier
 * choix n'aurait aucun consommateur. Le detail est dans l'en-tete de
 * `apps/api/app/entities/services.py`.
 */
export const CHEMINS = {
  //  **LA RACINE EST LA PAGE NATIONALE DEPUIS `T6`, ET C'EST UN ARBITRAGE.**
  //
  //  Le cahier §4.1 dit « une page nationale APRES AUTHENTIFICATION » et le
  //  diagramme du §8.1 la place juste apres la connexion. Aucun document ne
  //  nomme d'adresse ; `/` servait la page de STATUT depuis `T5` du LOT 1.
  //
  //  Mesure avant de decider : `verifier-page-statut.sh` n'exige de `/` que la
  //  coquille React et le mandatement des endpoints de sante -- il ne verifie
  //  JAMAIS le contenu de la page de statut. Deplacer celle-ci ne cassait donc
  //  rien, et l'arbitrage a pu se prendre sur le sens plutot que sur le cout.
  //
  //  Arbitrage de Jonathan du 23/08/2026 : la racine est la page nationale, la
  //  page de statut passe a `/statut`, meme contenu.
  national: '/',
  statut: '/statut',
  connexion: '/connexion',
  lienEnvoye: '/connexion/lien-envoye',
  lien: '/connexion/lien',
  connexionAdministrateur: '/connexion/administrateur',
  deconnexion: '/deconnexion',
  interdit: '/403',
  introuvable: '/404',
  erreur: '/erreur',
  //  LOT 4, `T2`. Le `:code` est le `code` de l'entite -- `code_unique` n'a
  //  AUCUNE clause partielle, donc un code n'est jamais reattribue, ce qui est
  //  ce qu'on exige d'un identifiant d'adresse. Mesure sur le schema reel.
  entite: '/entites/:code',
} as const;

/**
 * L'adresse d'une entite, pour un code donne.
 *
 * **LE CODE EST ENCODE.** `entity.code` est une chaine libre de 64 caracteres --
 * le modele ne lui impose AUCUN motif, mesure sur le schema. Un code contenant
 * `/` changerait le chemin obtenu, ce qui donnerait une navigation differente de
 * celle qu'on croit declencher.
 */
export function cheminDeLEntite(code: string): string {
  return CHEMINS.entite.replace(':code', encodeURIComponent(code));
}

/**
 * LES SIX RUBRIQUES DU MENU PRINCIPAL — LOT 4, `T4`, cahier §8.2.
 *
 * **UNE SEULE SOURCE, TROIS CONSOMMATEURS.** Le menu se rend d'ici, le `<h1>` de
 * chaque page interne s'en derive, et `make cadre-check` confronte cette liste
 * aux routes de `App.tsx`. Trois copies auraient divergé -- c'est `DEC-466` pour
 * le masquage et `ECART-022` pour les modèles de configuration.
 *
 * `libelleCorpus` est la formulation **exacte** du §8.2 : c'est elle que le
 * contrôle confronte au document, et non une reformulation qui « veut dire la
 * même chose ». Même parti que `ECRANS` en `T11` du LOT 3.
 *
 * DEUX RUBRIQUES SONT CONDITIONNELLES, ET LEUR CONDITION N'A PAS ENCORE DE SOURCE
 *
 *   Le §8.2 les écrit : « Mon onboarding, **uniquement lorsqu'un parcours actif
 *   existe** » et « Administration, **uniquement selon les permissions** ».
 *
 *   Ni l'une ni l'autre n'est calculable au `T4` :
 *
 *     le parcours actif    **aucune table de parcours n'existe** dans le schéma --
 *                          mesuré sur les 26 tables réelles. C'est le LOT 7.
 *     les permissions      la matrice §5 tranche QUI voit l'Administration -- elle
 *                          est à `—` pour `ANON`, `EMP` et `NEW`, et porte un
 *                          périmètre pour les six rôles responsables -- mais
 *                          **aucune route ne rend les rôles de l'appelant**. C'est
 *                          `T9`.
 *
 *   **Elles sont donc ABSENTES par défaut**, et c'est le « refus par défaut » du
 *   §20.1 : une rubrique montrée à tort suggère un droit qu'on n'a pas. `T9`
 *   branchera la source, et les tests éprouvent déjà **les deux** états.
 *
 * LES CHEMINS NE SONT NOMMÉS PAR AUCUN DOCUMENT
 *
 *   Le §8.1 donne l'arbre, le §8.2 les libellés ; aucun des deux ne donne d'URL.
 *   Les suffixes sont donc dérivés des libellés, sans accent ni espace -- la seule
 *   convention que le dépôt applique déjà, `/connexion/lien-envoye` en témoigne.
 */
export interface Rubrique {
  readonly cle: string;
  /** La formulation EXACTE du cahier §8.2. */
  readonly libelleCorpus: string;
  /** Le libellé affiché, sans la clause conditionnelle. */
  readonly libelle: string;
  /** Le suffixe sous `/entites/:code`. Vide pour l'accueil, qui est la route index. */
  readonly suffixe: string;
  /** Le titre de la page, porté par le cadre. */
  readonly titre: string;
  /** La condition du §8.2, mot pour mot, ou `undefined` si la rubrique est toujours visible. */
  readonly condition?: string;
  /** Le lot qui apportera son contenu. */
  readonly lot: string;
}

export const RUBRIQUES: readonly Rubrique[] = [
  {
    cle: 'accueil',
    libelleCorpus: 'Accueil',
    libelle: 'Accueil',
    suffixe: '',
    titre: "Accueil de l'entite",
    lot: 'LOT 4',
  },
  {
    cle: 'framework',
    libelleCorpus: 'Framework',
    libelle: 'Framework',
    suffixe: 'framework',
    titre: 'Framework',
    lot: 'LOT 6',
  },
  {
    cle: 'trombinoscope',
    libelleCorpus: 'Trombinoscope',
    libelle: 'Trombinoscope',
    suffixe: 'trombinoscope',
    titre: 'Trombinoscope',
    lot: 'LOT 5',
  },
  {
    cle: 'evenements',
    libelleCorpus: 'Événements',
    libelle: 'Evenements',
    suffixe: 'evenements',
    titre: 'Evenements',
    lot: 'LOT 8',
  },
  {
    cle: 'monOnboarding',
    libelleCorpus: 'Mon onboarding, uniquement lorsqu’un parcours actif existe',
    libelle: 'Mon onboarding',
    suffixe: 'mon-onboarding',
    titre: 'Mon onboarding',
    condition: 'uniquement lorsqu’un parcours actif existe',
    lot: 'LOT 7',
  },
  {
    cle: 'administration',
    libelleCorpus: 'Administration, uniquement selon les permissions',
    libelle: 'Administration',
    suffixe: 'administration',
    titre: 'Administration',
    condition: 'uniquement selon les permissions',
    lot: 'LOT 9',
  },
] as const;

/**
 * L'adresse d'une rubrique, pour un code d'entité donné.
 *
 * Le code est **encodé**, pour la raison écrite au-dessus de `cheminDeLEntite`.
 */
export function cheminDeRubrique(code: string, suffixe: string): string {
  const base = cheminDeLEntite(code);
  return suffixe === '' ? base : `${base}/${suffixe}`;
}

/**
 * Les huit ecrans, avec le libelle du corpus qui les produit.
 *
 * `libelleCorpus` est la formulation **exacte** du cahier : c'est elle que le test
 * confronte au document, et non une reformulation qui « veut dire la meme chose ».
 */
export interface Ecran {
  readonly cle: string;
  readonly libelleCorpus: string;
  readonly chemin: string;
  /** Vrai quand l'ecran est un ETAT d'une route et non une adresse a lui. */
  readonly etatDeRoute?: boolean;
}

export const ECRANS: readonly Ecran[] = [
  { cle: 'connexion', libelleCorpus: 'page de connexion', chemin: CHEMINS.connexion },
  {
    cle: 'lienEnvoye',
    libelleCorpus: 'confirmation de demande de lien',
    chemin: CHEMINS.lienEnvoye,
  },
  {
    cle: 'lienRefuse',
    libelleCorpus: 'lien expiré ou déjà consommé',
    chemin: CHEMINS.lien,
    etatDeRoute: true,
  },
  {
    cle: 'connexionAdministrateur',
    libelleCorpus: 'connexion administrateur',
    chemin: CHEMINS.connexionAdministrateur,
  },
  { cle: 'deconnexion', libelleCorpus: 'déconnexion', chemin: CHEMINS.deconnexion },
  { cle: 'interdit', libelleCorpus: '403', chemin: CHEMINS.interdit },
  { cle: 'introuvable', libelleCorpus: '404', chemin: CHEMINS.introuvable },
  { cle: 'erreur', libelleCorpus: 'erreur générale', chemin: CHEMINS.erreur },
] as const;
