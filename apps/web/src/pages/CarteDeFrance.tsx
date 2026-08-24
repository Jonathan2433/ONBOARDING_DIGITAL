/**
 * La carte de France illustrative — LOT 4, `T7`, cahier §8.3.
 *
 * CE QUE LE CORPUS DIT, ET C'EST UN SEUL MOT
 *
 *   Le cahier la nomme trois fois — §4.1 « une liste et une carte des entites »,
 *   §8.3 « une carte de France », et la liste du LOT 4 « carte de France
 *   **illustrative** » — et n'en dit rien de plus. Aucun format, aucune source de
 *   donnees, aucune coordonnee.
 *
 * TROIS MESURES ONT FERME LE CHOIX, ET IL N'EN RESTAIT QU'UN
 *
 *   1. **`entity` ne porte NI latitude NI longitude** — mesure sur le schema
 *      reel. Une carte a marqueurs exigerait donc soit une colonne au modele,
 *      soit des positions inventees ;
 *   2. **le prototype montre l'intention, et ce n'est PAS une carte de donnees** :
 *      sa `FranceMap` est une **image** base64 avec **un seul bouton** pose
 *      dessus — `alt="Carte eXalt"` — sans SVG de carte, sans coordonnee, sans
 *      bibliotheque cartographique. Mesure du 23/08/2026, sans grepper le fichier
 *      entier (§7.13) ;
 *   3. **`DEP-006` est OUVERTE**, echeance ce lot : « charte, logo et typographie
 *      officiels exploitables », Lea / eXalt. Le visuel officiel n'existe pas.
 *
 *   Reutiliser l'image du prototype est **interdit** — regle 4, « aucune ligne de
 *   code du prototype reutilisee » — et ne rien livrer contredirait la roadmap,
 *   qui inclut la carte au LOT 4. D'ou ce qui suit.
 *
 * CE TRACE EST UN PROVISOIRE ASSUME, ET IL FAUT LE LIRE COMME TEL
 *
 *   **Il est dessine a la main, et il est approximatif.** Trois versions ont ete
 *   faites et regardees a l'ecran ; la troisieme montre la Bretagne et la Corse et
 *   se lit « la France, a peu pres » — pas mieux. Je me suis arrete la, et le motif
 *   est de fond : **auteurer une illustration de marque appartient a `DEP-006`**,
 *   « charte, logo et typographie officiels », Lea / eXalt, OUVERTE et d'echeance
 *   CE LOT. Continuer aurait ete inventer un visuel que quelqu'un d'autre doit
 *   fournir — la regle §6.5 appliquee a une image plutot qu'a une valeur.
 *
 *   **Ce qui est livre, et qui est ce que le critere demande** : l'emplacement, sa
 *   place exacte dans le DOM — apres la liste — et son caractere DECORATIF, tous
 *   trois tenus par `make cadre-check`. L'illustration elle-meme est un
 *   remplacement d'une ligne : un `<img>` a la place du `<svg>`, sans toucher au
 *   reste. C'est le parti de `DEC-491` pour les couleurs — des jetons provisoires,
 *   derives et remplacables sans refonte.
 *
 *   **Et il ne pretend rien.** Une forme approximative presentee comme une carte de
 *   reference serait une affirmation que je ne peux pas tenir, et le §7.0 septieme
 *   point l'interdit : ne jamais ecrire une valeur plausible plutot que mesuree.
 *   « Illustrative » est le mot du cahier, et c'est tout ce qu'elle est.
 *
 * ELLE EST DECORATIVE AU SENS DE L'ACCESSIBILITE, PAR CONSTRUCTION
 *
 *   C'est le critere de sortie de `T7` : « la carte est **decorative** au sens de
 *   l'accessibilite : elle n'est pas le seul moyen d'atteindre une entite ».
 *
 *     `aria-hidden="true"`   elle est retiree de l'arbre d'accessibilite ;
 *     `focusable="false"`    Internet Explorer et certains lecteurs rendaient un
 *                            `<svg>` focusable ; l'attribut le ferme ;
 *     aucun element interactif  ni `<a>`, ni `<button>`, ni gestionnaire.
 *
 *   **Le prototype, lui, posait un bouton SUR la carte.** Ne pas le reprendre est
 *   deliberé : un bouton dans une image decorative serait atteignable au clavier
 *   sans etre annonce, ce qui est pire qu'un bouton absent. La liste au-dessus est
 *   le chemin, et elle est complete.
 */
import type { JSX } from 'react';

export function CarteDeFrance(): JSX.Element {
  return (
    <div className="nat-carte">
      <svg
        className="nat-carte-dessin"
        viewBox="0 0 100 100"
        //  **RETIREE DE L'ARBRE D'ACCESSIBILITE.** Pas de `role="img"`, pas de
        //  `<title>` : ce serait annoncer une carte qui n'apporte aucune
        //  information que la liste ne donne deja.
        aria-hidden="true"
        focusable="false"
      >
        {/*
          Silhouette STYLISEE de la France metropolitaine, en coordonnees
          relatives sur une grille de 100 x 100. Elle n'est pas cartographique et
          ne pretend pas l'etre : le cahier demande une carte « illustrative ».

          **MAIS ELLE DOIT ETRE RECONNAISSABLE, ET MA PREMIERE VERSION NE
          L'ETAIT PAS.** Vue a l'ecran, elle se lisait comme une forme ronde
          quelconque -- pas comme l'hexagone. Une carte illustrative qui ne se
          reconnait pas n'est pas une carte : c'est un aplat. Seul le regard
          pouvait l'attraper, et c'est pour cela que le critere dit « mesure ».

          Le trace suit donc les reperes que tout le monde reconnait, dans le sens
          horaire depuis le nord : la cote de la Manche, l'Alsace, les Alpes, la
          Cote d'Azur, la Mediterranee, les Pyrenees plates, la cote atlantique,
          l'estuaire de la Gironde, et la pointe de la Bretagne.
        */}
        <path
          className="nat-carte-terre"
          d="M52 2 L60 6 L66 4 L72 10 L80 18 L84 26 L80 34 L86 44 L84 52
             L78 60 L66 64 L56 62 L46 66 L38 70 L26 70 L18 66 L16 58 L14 50
             L12 44 L14 38 L10 34 L0 30 L10 26 L18 24 L24 18 L22 12 L30 16
             L38 12 L44 8 Z"
        />
        {/*
          La Corse, separee. Sans elle, la silhouette se lit comme une France
          amputee -- et l'omettre serait un choix que rien ne motive.
        */}
        <path className="nat-carte-terre" d="M89 58 L93 62 L92 71 L88 72 L86 64 Z" />
      </svg>
    </div>
  );
}
