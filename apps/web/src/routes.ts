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

/** Les chemins, source unique lue par le routeur, les tests et le controle. */
export const CHEMINS = {
  statut: '/',
  connexion: '/connexion',
  lienEnvoye: '/connexion/lien-envoye',
  lien: '/connexion/lien',
  connexionAdministrateur: '/connexion/administrateur',
  deconnexion: '/deconnexion',
  interdit: '/403',
  introuvable: '/404',
  erreur: '/erreur',
} as const;

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
