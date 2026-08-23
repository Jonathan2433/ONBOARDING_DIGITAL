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
  statut: '/',
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
