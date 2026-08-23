/**
 * Les primitives de validation de forme, en UN seul exemplaire.
 *
 * LOT 4, sous-etape T1.
 *
 * POURQUOI CE MODULE EXISTE
 *
 *   `estObjet` et `exigerChaine` etaient prives a `sante.ts`. Le LOT 4 en a
 *   besoin pour valider la liste des entites. Les recopier dans un second module
 *   aurait produit DEUX exemplaires d'une meme regle, qui divergent en silence le
 *   jour ou l'un des deux se durcit -- c'est ce que `DEC-466` interdit pour le
 *   masquage et `ECART-022` pour les modeles de configuration.
 *
 *   Ils sont extraits, pas dupliques. Ils restent INTERNES au paquet : `index.ts`
 *   ne les reexporte pas, parce qu'un consommateur qui validerait lui-meme ne
 *   passerait plus par les validateurs du contrat.
 *
 * POURQUOI TOUJOURS PAS DE ZOD, ET LA QUESTION A ETE REOUVERTE
 *
 *   Le commentaire de `sante.ts` disait « `DEC-456` n'installe pas Zod AVANT LE
 *   LOT 4, faute d'usage, et deux formes de reponse ne le justifient pas ». Nous
 *   y sommes, et la question a donc ete reexaminee plutot qu'archivee (§7.22).
 *
 *   Reponse : trois formes ne le justifient pas davantage. `make audit` est a
 *   ZERO avis et ZERO tolerance depuis `DEC-493` ; chaque dependance ajoutee est
 *   une surface de plus a tenir a ce niveau, et l'installer releverait d'un
 *   arbitrage de Jonathan, non d'un choix de sous-etape.
 */

/** Vrai pour un objet JSON — ni `null`, ni tableau. */
export function estObjet(valeur: unknown): valeur is Record<string, unknown> {
  return typeof valeur === 'object' && valeur !== null && !Array.isArray(valeur);
}

/** Lire un champ textuel obligatoire. Leve si le champ manque ou n'est pas une chaine. */
export function exigerChaine(source: Record<string, unknown>, cle: string): string {
  const valeur = source[cle];
  if (typeof valeur !== 'string') {
    throw new TypeError(`champ « ${cle} » absent ou non textuel`);
  }
  return valeur;
}
