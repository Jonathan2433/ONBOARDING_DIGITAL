/**
 * Un groupe du cahier §10.8/§8.1 SANS AUCUN CONTENU construit par ce lot — LOT 9, `T14`.
 *
 * `CONTENU` ET `CONFIGURATION` N'ONT AUCUNE ROUTE À CONSOMMER, PAS SEULEMENT DANS CE LOT
 *
 *   Mesuré sur les 86 chemins du manifeste : aucune des huit stories du LOT 9
 *   ne nomme ni l'un ni l'autre. La gestion des contenus existe déjà, mais
 *   PAR RESSOURCE (Framework, cercle, bureau — `PanneauEditionDeContenu`,
 *   LOT 6), jamais depuis une liste centralisée ; la configuration d'entité
 *   (matrice §19) n'a AUCUNE route d'écriture nulle part dans ce dépôt.
 *
 * ARBITRAGE DE JONATHAN : LES DEUX GROUPES RESTENT DANS LE MENU, MARQUÉS « À VENIR »
 *
 *   Plutôt que de les omettre — ce qui masquerait la structure à SEPT
 *   groupes que le cahier fixe pour tout le back-office — même parti que
 *   `PageRubrique` (LOT 4, `T4`) pour une rubrique entière pas encore livrée.
 */
import type { JSX } from 'react';

export function SectionAVenir({ groupe }: { readonly groupe: string }): JSX.Element {
  return (
    <p className="administration-a-venir">
      « {groupe} » arrive dans un lot ultérieur. Aucune route de ce lot ne construit cette section.
    </p>
  );
}
