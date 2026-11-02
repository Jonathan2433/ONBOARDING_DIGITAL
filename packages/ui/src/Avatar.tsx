/**
 * Avatar — portrait d'une personne, ou son repli en initiales.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-681`), charte 5.
 *
 * ROND, ET C'EST UN RETOUR EN ARRIERE ASSUME
 *
 *   `S11` du chantier precedent avait pose des cadres HEXAGONAUX (`DECOUPES`,
 *   `clip-path`). La capture de la charte v2 montre des portraits ronds, et
 *   Jonathan a tranche en ce sens : `E1` a retire `DECOUPES`, et ce composant
 *   emploie `--rayon-pastille`. Ce n'est pas un oubli de `S11`, c'est sa
 *   revision — consignee a `DEC-681`.
 *
 * DECORATIF PAR DEFAUT, COMME `Picto`
 *
 *   La charte 1.3 veut que « le mot porte le sens ». Partout ou la charte 6
 *   place un avatar — carte de trombinoscope, encart Booster, liste de membres,
 *   fiche d'arrivee — le nom de la personne est ECRIT a cote. Annoncer la photo
 *   ferait entendre deux fois le meme nom.
 *
 *   L'image porte donc `alt=""` et les initiales `aria-hidden`. `decoratif={false}`
 *   est l'echappatoire pour un avatar SEUL, sans nom visible a cote : l'image
 *   recoit alors `alt={nom}` et le repli devient une image nommee.
 *
 * LES INITIALES SONT UN REPLI, PAS UNE IDENTITE
 *
 *   Elles viennent des deux premiers MOTS du nom, jamais des deux premieres
 *   lettres : « Ada Lovelace » rend « AL », pas « AD ». Un nom d'un seul mot
 *   rend une seule lettre, un nom vide ne rend rien et laisse le cercle nu
 *   plutot que d'afficher un caractere arbitraire.
 *
 *   Le couple est `TEINTES.bleu` — fond lavande, texte `--titre`, 8,8:1, deja
 *   prouve. Les deux valeurs sont les LITTERAUX apparies : cette surface ne
 *   bascule pas avec le theme, donc son texte ne le doit pas non plus.
 *
 * L'ANNEAU, ET CE QU'IL NE PEUT PAS PORTER
 *
 *   « Anneau optionnel 2px couleur du cercle » (charte 5). Il est DECORATIF :
 *   la charte 1.3 impose que le cercle soit aussi ecrit en toutes lettres, donc
 *   l'anneau ne porte jamais seul une information. C'est ce qui l'exempte du
 *   contraste non textuel (WCAG 1.4.11), au meme titre que le souligne ondule
 *   de `S13`.
 *
 *   **ET C'EST HEUREUX, PARCE QUE LA MESURE EST SEVERE.** Sur une surface
 *   claire, cinq des huit couleurs de cercle rendent moins de 1,4:1 — Change
 *   1,37, Data 1,17, Shield 1,19, Forge 1,08, IT 1,09. L'anneau y est donc
 *   quasiment invisible. Il reste offert parce que la charte le demande, mais
 *   aucun ecran ne doit s'y fier pour dire a quel cercle appartient quelqu'un.
 *   Mesure du 02/11/2026, a reprendre a `E5`.
 */

import type { CSSProperties, ReactNode } from 'react';

/** Les cinq tailles de la charte 5, en pixels. */
export type TailleAvatar = 32 | 40 | 56 | 72 | 84;

export interface ProprietesAvatar {
  /** Le nom de la personne. Sert aux initiales, et au texte alternatif si nomme. */
  readonly nom: string;
  /** L'adresse de la miniature. Absente, les initiales prennent la place. */
  readonly photo?: string;
  /** 40 par defaut. */
  readonly taille?: TailleAvatar;
  /** La couleur de l'anneau. Absente, aucun anneau. Decoratif : voir l'en-tete. */
  readonly anneau?: string;
  /** `true` par defaut : le nom est deja ecrit a cote. Voir l'en-tete. */
  readonly decoratif?: boolean;
}

/** Les initiales des deux premiers MOTS du nom. Jamais ses deux premieres lettres. */
export function initiales(nom: string): string {
  return nom
    .split(/\s+/)
    .filter((mot) => mot.length > 0)
    .slice(0, 2)
    .map((mot) => mot[0]?.toLocaleUpperCase('fr-FR') ?? '')
    .join('');
}

export function Avatar({
  nom,
  photo,
  taille = 40,
  anneau,
  decoratif = true,
}: ProprietesAvatar): ReactNode {
  //  L'anneau voyage par une propriete personnalisee plutot que par `border`
  //  directement : la feuille garde la main sur l'epaisseur, et une carte sans
  //  cercle retombe sur le repli declare au `:root`. Meme montage que
  //  `--carte-cercle` (`CarteRetournable`), que `cadre-check` avait exige.
  const style = anneau === undefined ? undefined : ({ '--avatar-anneau': anneau } as CSSProperties);

  if (photo !== undefined) {
    return (
      <img
        className="ex-avatar"
        data-taille={taille}
        data-anneau={anneau === undefined ? 'non' : 'oui'}
        style={style}
        src={photo}
        alt={decoratif ? '' : nom}
        width={taille}
        height={taille}
      />
    );
  }

  const lettres = initiales(nom);
  return (
    <span
      className="ex-avatar ex-avatar--initiales"
      data-taille={taille}
      data-anneau={anneau === undefined ? 'non' : 'oui'}
      style={style}
      {...(decoratif ? { 'aria-hidden': true } : { role: 'img', 'aria-label': nom })}
    >
      {lettres}
    </span>
  );
}
