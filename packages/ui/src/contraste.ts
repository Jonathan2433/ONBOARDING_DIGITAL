/**
 * Contraste WCAG 2.2 — le calcul, et rien d'autre.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007.
 *
 * POURQUOI CE MODULE EXISTE, ET POURQUOI IL EST SEPARE DES JETONS
 *
 *   Le cahier des charges 14 impose WCAG 2.2 niveau AA. Une palette qui se
 *   contente d'etre jolie ne satisfait pas cette exigence : il faut que chaque
 *   couple fond/texte reellement employe atteigne son seuil.
 *
 *   Ce module ne declare aucune couleur. Il calcule. Les jetons declarent leurs
 *   couples, et `jetons.test.ts` RECALCULE chaque couple avec ce module et
 *   ECHOUE si l'un descend sous son seuil. Un jeton mal apparie casse donc
 *   `make check` — c'est la seule facon de rendre la palette non arbitraire
 *   autrement qu'en l'affirmant.
 *
 * CE QU'IL NE FAIT PAS
 *   Il ne juge que le contraste. L'accessibilite ne s'y reduit pas : nom
 *   accessible, ordre de tabulation, role, focus visible sont verifies ailleurs —
 *   `eslint-plugin-jsx-a11y` a la construction, et les tests de composant a
 *   l'execution.
 *
 * La formule est celle de WCAG 2.x, section « relative luminance » et
 * « contrast ratio ». Elle est reproduite ici plutot qu'importee : ajouter une
 * dependance pour vingt lignes de calcul augmenterait la surface d'audit sans
 * necessite, et ce calcul ne changera jamais.
 */

/** Les deux seuils de WCAG 2.2 niveau AA. */
export const SEUIL_AA_TEXTE_NORMAL = 4.5;
export const SEUIL_AA_GRAND_TEXTE = 3;

const MOTIF_HEXA = /^#[0-9a-fA-F]{6}$/;

/**
 * Luminance relative d'une couleur `#rrggbb`.
 *
 * Rejette toute valeur qui n'est pas exactement six hexadecimaux : une notation
 * courte ou une couleur nommee passerait silencieusement a `parseInt` en
 * produisant `NaN`, et un contraste `NaN` ne comparerait rien du tout — le
 * controle serait muet au lieu d'echouer.
 */
export function luminance(couleur: string): number {
  if (!MOTIF_HEXA.test(couleur)) {
    throw new Error(
      `couleur invalide : ${JSON.stringify(couleur)} — attendu #rrggbb sur six hexadecimaux`,
    );
  }
  const canal = (position: number): number => {
    const brut = Number.parseInt(couleur.slice(position, position + 2), 16) / 255;
    return brut <= 0.03928 ? brut / 12.92 : Math.pow((brut + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * canal(1) + 0.7152 * canal(3) + 0.0722 * canal(5);
}

/**
 * Rapport de contraste entre deux couleurs, de 1 a 21.
 *
 * L'ordre des arguments est indifferent : le rapport est symetrique, et c'est
 * voulu — un appelant qui inverserait fond et texte obtiendrait la meme valeur,
 * donc le controle ne peut pas passer par accident a cause d'un ordre inverse.
 */
export function contraste(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Le contraste atteint-il le seuil demande ? */
export function atteintSeuil(fond: string, texte: string, seuil: number): boolean {
  return contraste(fond, texte) >= seuil;
}
