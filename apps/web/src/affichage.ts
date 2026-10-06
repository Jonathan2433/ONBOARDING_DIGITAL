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

/**
 * Les quatre jetons de couleur que le design system porte — LOT 1, `T10`.
 *
 * **UN JETON INCONNU NE DONNE AUCUNE COULEUR, ET SURTOUT PAS UNE INVENTEE.** Le
 * design system dit : « aucune couleur de cercle : c'est une notion metier du
 * **LOT 6** ». Tout autre jeton — et `null`, `color_token` etant nullable au
 * schema, defaut `T10-8` — laisse la bordure neutre. Le NOM du cercle reste du
 * texte dans les deux cas, ce qui est ce que le §10.1 protege.
 */
const COULEURS_DE_CERCLE: Readonly<Record<string, string>> = {
  bleu: 'var(--marque-bleu)',
  'bleu-fonce': 'var(--marque-bleu-fonce)',
  rose: 'var(--marque-rose)',
  jaune: 'var(--marque-jaune)',
};

/** La couleur d'un jeton, ou `undefined` — `null` et jeton inconnu se valent ici. */
export function couleurDuCercle(jeton: string | null): string | undefined {
  return jeton === null ? undefined : COULEURS_DE_CERCLE[jeton];
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
