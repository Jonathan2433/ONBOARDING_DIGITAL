/**
 * Le client du trombinoscope — LOT 5, `T10`, story `MVP-L05-US003`.
 *
 * IL VALIDE CE QU'IL RECOIT, ET LE VALIDATEUR VIENT DU CONTRAT
 *
 *   Les types TypeScript disparaissent a la compilation. `validerLeTrombinoscope`
 *   vit dans `@onboarding/contracts`, source unique lue par TypeScript **et** par
 *   le test Python qui confronte le manifeste au schema servi (`DEC-492`).
 *
 * IL PORTE UN SIGNAL D'ABANDON, ET LA RECHERCHE LE REND INDISPENSABLE
 *
 *   Le §23.3 l'exige deja pour le changement d'entite. La recherche l'exige une
 *   seconde fois, et plus souvent : chaque frappe lance une requete, et sans
 *   abandon une reponse lente pour « Ada » arriverait APRES celle de « Adam » et
 *   l'ecraserait. **Le defaut ne se voit que sous latence**, donc jamais en
 *   developpement local -- exactement le §7.16.
 *
 * LES PARAMETRES SONT CONSTRUITS PAR `URLSearchParams`, JAMAIS CONCATENES
 *
 *   Un terme de recherche contient des espaces, des apostrophes, parfois un `&`.
 *   Une concatenation manuelle produirait une adresse fausse sur « Jean & Marie »,
 *   et le defaut serait attribue a la recherche plutot qu'a l'encodage.
 */
import {
  cheminTrombinoscope,
  EN_TETE_CORRELATION,
  type ReponseDuTrombinoscope,
  validerLeTrombinoscope,
} from '@onboarding/contracts';

/** Ce qu'un appel du trombinoscope rend, une fois lu. */
export interface ReponseLue {
  readonly statut: number;
  readonly corps: ReponseDuTrombinoscope | null;
  readonly correlation: string | null;
}

/**
 * Les criteres que l'ECRAN sait poser.
 *
 * **DEUX SUR SIX, ET CE N'EST PAS UN OUBLI.** L'API accepte cinq filtres depuis
 * `T3` -- cercle, DSM, metier, client, statut -- mais quatre d'entre eux prennent
 * un **identifiant**, et aucun endpoint ne sert la liste des cercles, des
 * metiers, des clients ni des DSM : mesure du 12/09/2026 sur les vingt-et-un
 * chemins du manifeste, zero. Un ecran ne peut pas offrir un choix dont il ne
 * connait pas les options.
 *
 * `statut` fait exception parce que son domaine est **ferme et derivable** :
 * `mission` ou `intercontract`, §6.5 du modele.
 *
 * Les quatre autres arriveront avec les endpoints de reference -- les cercles au
 * **LOT 6**, les metiers, clients et DSM avec le back-office du **LOT 9**.
 */
export interface CriteresDeRecherche {
  readonly page: number;
  readonly taille: number;
  readonly recherche: string;
  readonly statut: string;
}

/**
 * Une page du trombinoscope — `GET /api/v1/entities/{code}/people`.
 *
 * Les criteres vides ne sont PAS envoyes : une chaine vide n'est pas « aucun
 * filtre » pour l'API, c'est un filtre sur la chaine vide, et le §18.3 la
 * refuserait.
 */
export async function listerLeTrombinoscope(
  code: string,
  criteres: CriteresDeRecherche,
  signal?: AbortSignal,
): Promise<ReponseLue> {
  const parametres = new URLSearchParams({
    page: String(criteres.page),
    taille: String(criteres.taille),
  });
  if (criteres.recherche !== '') {
    parametres.set('recherche', criteres.recherche);
  }
  if (criteres.statut !== '') {
    parametres.set('statut', criteres.statut);
  }

  const requete: RequestInit = { method: 'GET', credentials: 'same-origin' };
  if (signal !== undefined) {
    requete.signal = signal;
  }
  const reponse = await fetch(`${cheminTrombinoscope(code)}?${parametres.toString()}`, requete);
  //  L'en-tete AVANT le corps : le corps peut lever, et la correlation est
  //  justement ce qu'on veut montrer quand quelque chose casse.
  const correlation = reponse.headers.get(EN_TETE_CORRELATION);

  let corps: ReponseDuTrombinoscope | null;
  try {
    corps = validerLeTrombinoscope(await reponse.json());
  } catch {
    corps = null;
  }
  return { statut: reponse.status, corps, correlation };
}
