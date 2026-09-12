/**
 * Le client de la fiche profil et de son historique — LOT 5, `T11`.
 *
 * DEUX APPELS, ET ILS NE SE COMMANDENT PAS L'UN L'AUTRE
 *
 *   La fiche releve du §5 de la matrice, « Fiches collaborateur », en Lecture
 *   pour les HUIT roles authentifies. L'historique releve de la ligne « Audit »
 *   du meme §5, qui REFUSE `EMP` et `NEW` -- savoir qui a manage qui et chez quel
 *   client est une information de gestion, non une donnee d'annuaire.
 *
 *   **Un employe voit donc la fiche et se voit refuser l'historique**, et c'est
 *   l'etat NORMAL, pas une panne. Les enchainer -- attendre la fiche pour
 *   demander l'historique -- ne servirait a rien ; les lancer ensemble et traiter
 *   leurs refus separement est ce que la matrice decrit.
 *
 * LE 403 ET LE 404 SONT DEUX CHOSES DIFFERENTES, ET L'ECRAN DOIT LE DIRE
 *
 *   `403` : « tu n'as pas le droit de lire d'historique ». `404` couvre QUATRE
 *   causes que `T9` rend indistinguables A DESSEIN, dont « cette cible est hors
 *   de ton perimetre » -- distinguer apprendrait a un DSM de qui il n'est pas
 *   responsable. Le client les rapporte tels quels ; c'est l'ecran qui choisit
 *   son message.
 *
 * IL VALIDE CE QU'IL RECOIT, ET LE VALIDATEUR VIENT DU CONTRAT
 *
 *   Meme montage que `trombinoscope.ts` : les types TypeScript disparaissent a la
 *   compilation, les validateurs vivent dans `@onboarding/contracts`, source
 *   unique lue par TypeScript **et** par le controle Python qui confronte le
 *   manifeste au schema servi (`DEC-492`).
 */
import {
  cheminHistorique,
  cheminProfil,
  EN_TETE_CORRELATION,
  type FicheDuProfil,
  type HistoriqueOrganisationnel,
  validerLaFiche,
  validerLHistorique,
} from '@onboarding/contracts';

/** Ce qu'un appel rend, une fois lu : le code, le corps valide ou `null`, la correlation. */
export interface ReponseLue<T> {
  readonly statut: number;
  readonly corps: T | null;
  readonly correlation: string | null;
}

/**
 * Le montage commun aux deux appels.
 *
 * **`credentials: 'same-origin'` PLUTOT QUE RIEN** : la page et l'API partagent
 * une origine depuis `DEC-470`, et le cookie de session est `SameSite=lax`. Le
 * declarer rend la dependance visible dans le code plutot que dans un reglage.
 */
async function appeler<T>(
  chemin: string,
  valider: (valeur: unknown) => T,
  signal?: AbortSignal,
): Promise<ReponseLue<T>> {
  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(chemin, requete);
  //  L'en-tete AVANT le corps : le corps peut lever, et la correlation est
  //  justement ce qu'on veut montrer quand quelque chose casse.
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: T | null;
  try {
    corps = valider(await reponse.json());
  } catch {
    //  **UN CORPS ILLISIBLE N'EST PAS UN ECHEC RESEAU.** Le statut est conserve :
    //  un `404` porte un corps d'erreur au format du §18.3, que le validateur de
    //  la fiche refuse a juste titre -- et l'ecran a besoin du `404`, pas d'une
    //  exception.
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}

/** La fiche d'une appartenance — `GET /api/v1/entities/{code}/people/{appartenance}`. */
export function lireLaFiche(
  code: string,
  appartenance: string,
  signal?: AbortSignal,
): Promise<ReponseLue<FicheDuProfil>> {
  return appeler(cheminProfil(code, appartenance), validerLaFiche, signal);
}

/** L'historique organisationnel — `GET …/people/{appartenance}/historique`. */
export function lireLHistorique(
  code: string,
  appartenance: string,
  signal?: AbortSignal,
): Promise<ReponseLue<HistoriqueOrganisationnel>> {
  return appeler(cheminHistorique(code, appartenance), validerLHistorique, signal);
}
