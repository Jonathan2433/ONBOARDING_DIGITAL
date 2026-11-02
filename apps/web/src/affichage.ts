/**
 * Ce que DEUX ecrans au moins doivent presenter de la meme facon — LOT 5, `T11`.
 *
 * POURQUOI UN MODULE PLUTOT QU'UNE REEXPORTATION DE PAGE A PAGE
 *
 *   `T10` avait pose `STATUTS` et `COULEURS_DE_CERCLE` dans `PageTrombinoscope`,
 *   ou ils n'avaient qu'un consommateur. La fiche profil est le second, et
 *   l'importer depuis la page du trombinoscope ferait dependre un ecran d'un
 *   autre : le jour ou l'un est supprime ou renomme, l'autre casse pour une
 *   raison qui n'a rien a voir avec lui.
 *
 *   **Les recopier aurait ete pire** : deux tables de libelles divergent au
 *   premier ajout, et la seconde est celle qu'aucun test ne regarde. §7.27.
 *
 * LES DEUX VALEURS DE STATUT SONT DERIVEES DU CONTRAT, PAS REECRITES
 *
 *   `STATUTS_PROFESSIONNELS` vient du §6.5 du modele, par le paquet `contracts`.
 *   Un libelle ecrit ici pour une valeur que l'API ne sert plus resterait
 *   invisible ; un statut servi sans libelle s'afficherait en anglais. Un test
 *   confronte donc les deux listes dans les DEUX sens.
 */
import { STATUTS_PROFESSIONNELS } from '@onboarding/contracts';
import { CERCLES } from '@onboarding/ui';
import type { ClePicto, DefinitionDeCercle, TonBadge } from '@onboarding/ui';

import { dateComplete } from './pages/PageProfil';

/**
 * Le libelle francais de chaque valeur du §6.5.
 *
 * **`intercontract` EST LA VALEUR STOCKEE, « intercontrat » LE MOT FRANCAIS.**
 * Le modele emploie l'anglais pour les valeurs (`DEC-499`) ; l'ecran affiche du
 * francais. La traduction vit ici, en un seul endroit.
 */
const LIBELLES: Readonly<Record<string, string>> = {
  mission: 'En mission',
  intercontract: 'En intercontrat',
};

/** Les statuts proposables, dans l'ordre du contrat. */
export const STATUTS: readonly { readonly valeur: string; readonly libelle: string }[] =
  STATUTS_PROFESSIONNELS.map((valeur) => ({ valeur, libelle: LIBELLES[valeur] ?? valeur }));

/**
 * Le libelle d'un statut, ou `null` quand il n'y en a pas.
 *
 * **UNE VALEUR INCONNUE EST RENDUE TELLE QUELLE, JAMAIS MASQUEE.** Si l'API
 * servait un jour un troisieme statut, l'afficher en anglais est laid mais vrai ;
 * le remplacer par « Non renseigne » affirmerait faux.
 */
export function libelleDuStatut(valeur: string | null): string | null {
  if (valeur === null) {
    return null;
  }
  return STATUTS.find((choix) => choix.valeur === valeur)?.libelle ?? valeur;
}

/** Le ton de badge porte le même sens métier que le statut, jamais une couleur générique. */
export function tonDuStatut(valeur: string): TonBadge {
  if (valeur === 'mission') {
    return 'mission';
  }
  if (valeur === 'intercontract') {
    return 'intercontrat';
  }
  // Une valeur future reste visible par son texte et reçoit le ton informatif.
  return 'info';
}

/**
 * Le cercle que designe le jeton servi par l'API — chantier v2, `E4`.
 *
 * ============================================================================
 *  LA TABLE N'EST PLUS ICI, ET C'EST TOUT LE SENS DE `E4`
 * ============================================================================
 *
 * La charte intitule sa section 4 « Cercles (**donnees, pas en dur**) » et
 * demande une table `{ nom, surface, texte, picto }`. Cette table vit dans
 * `@onboarding/ui` (`CERCLES`), ou elle est confrontee au tableau markdown de
 * la charte elle-meme par `cercles.test.ts`. Ce module ne fait plus que la
 * CONSULTER.
 *
 * Avant `E4`, deux tables vivaient ici — `COULEURS_DE_CERCLE` et
 * `TEXTES_DE_CERCLE` — avec leurs propres cles (`bleu`, `bleu-fonce`, `rose`,
 * `jaune`) et sans pictogramme. Elles portaient QUATRE des huit cercles de la
 * charte, et aucune ne pouvait en porter le dessin : une etiquette de couleur
 * ne designe pas un pictogramme.
 *
 * ============================================================================
 *  CE QUI N'A PAS CHANGE, ET QUI EST LA RAISON D'ETRE DE CE REPLI
 * ============================================================================
 *
 * **UN JETON INCONNU NE DONNE AUCUNE COULEUR, ET SURTOUT PAS UNE INVENTEE.**
 * `circle.color_token` est un texte libre et NULLABLE au schema (modele 8.1) :
 * mesure du 02/11/2026, 112 cercles sur 116 n'en portent aucun. Tout jeton
 * etranger a la table — et `null`, defaut `T10-8` — laisse la bordure neutre.
 * Le NOM du cercle reste du texte dans tous les cas, ce qui est ce que le 10.1
 * du modele protege : « la couleur ne constitue jamais la seule information ».
 *
 * `jetonDeCouleur` N'EST JAMAIS EMPLOYE COMME INDEX : `CERCLES[null]` rendrait
 * `undefined` exactement comme le chemin garde, et aucun test d'ecran ne verrait
 * la difference — c'est le TYPE qui le refuse.
 */
function cercleDuJeton(jeton: string | null): DefinitionDeCercle | undefined {
  if (jeton === null) {
    return undefined;
  }
  return (CERCLES as Readonly<Record<string, DefinitionDeCercle>>)[jeton];
}

/**
 * La surface d'un cercle, en `var(--cercle-…)`, ou `undefined`.
 *
 * **LA VALEUR RENDUE EST UNE VARIABLE CSS, PAS LE `#rrggbb` DE LA TABLE.** Les
 * deux portent la meme couleur — `jetons-css.test.ts` l'exige — mais seule la
 * variable laisse une feuille de style reprendre la main, et surtout seule elle
 * garde les ecrans exempts de toute valeur litterale, ce que `make ecrans-check`
 * verifie. La table reste la source ; la variable est son adresse.
 */
export function couleurDuCercle(jeton: string | null): string | undefined {
  return cercleDuJeton(jeton) === undefined ? undefined : `var(--cercle-${jeton as string})`;
}

/** Le texte apparie a `couleurDuCercle` pour le meme jeton. Jamais l'un sans l'autre. */
export function texteDuCercle(jeton: string | null): string | undefined {
  return cercleDuJeton(jeton) === undefined ? undefined : `var(--cercle-${jeton as string}-texte)`;
}

/**
 * Le pictogramme officiel d'un cercle, ou `undefined` — chantier v2, `E4`.
 *
 * Quatrieme colonne du tableau de la charte 4, et la seule que les deux tables
 * d'avant `E4` ne pouvaient pas porter. Aucun ecran ne la consomme encore : les
 * ecrans sont l'etape `E5`, et c'est la que `Picto` recevra ses premiers
 * emplacements reels (tuile de cercle, carte de trombinoscope, page Framework).
 */
export function pictoDuCercle(jeton: string | null): ClePicto | undefined {
  return cercleDuJeton(jeton)?.picto;
}

/** Le nom que la charte donne au cercle, ou `undefined`. */
export function nomDeCharteDuCercle(jeton: string | null): string | undefined {
  return cercleDuJeton(jeton)?.nom;
}

/**
 * « 14:30 », lu a position fixe dans la chaine ISO — jamais par `Date`.
 *
 * **DEPLACEE ICI DEPUIS `PageEvenements.tsx` (LOT 8, `T9`) A SON `T11`** : la
 * section « evenements a venir » de l'accueil (`PageEntite.tsx`) en devient le
 * second consommateur, et une seconde copie aurait divergee au premier ajout
 * — §7.27, meme motif que `couleurDuCercle` ci-dessus.
 */
export function heureDeLEvenement(iso: string): string {
  return iso.slice(11, 16);
}

/** « 12 octobre 2026, 08:00 - 09:30 », ou la forme etendue si les jours different. */
export function plageDeLEvenement(commenceLe: string, finitLe: string): string {
  const memeJour = commenceLe.slice(0, 10) === finitLe.slice(0, 10);
  return memeJour
    ? `${dateComplete(commenceLe)}, ${heureDeLEvenement(commenceLe)} - ${heureDeLEvenement(finitLe)}`
    : `Du ${dateComplete(commenceLe)} ${heureDeLEvenement(commenceLe)} au ${dateComplete(finitLe)} ${heureDeLEvenement(finitLe)}`;
}
