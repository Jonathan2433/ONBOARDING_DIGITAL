/**
 * Les icones des six rubriques — chantier front hors lot, S3 (`DEC-672`),
 * cahier §13.2 (« icones ... maitrisees ») et §5 de la fiche de chantier.
 *
 * UNE SEULE SOURCE, DEUX CONSOMMATEURS
 *
 *   `NavigationPrincipale` et `BarreMobile` affichent les memes six rubriques
 *   et doivent montrer la MEME icone pour chacune : deux correspondances
 *   ecrites separement divergeraient au premier ajout (§7.27, `DEC-466` —
 *   deja la raison qui a fait extraire `rubriqueEstVisible` dans `routes.ts`
 *   au LOT 4, `T9`).
 *
 * DECORATIVES, JAMAIS INFORMATIVES
 *
 *   Chaque rubrique porte deja son libelle textuel ; l'icone est un rappel
 *   visuel du §13.2, pas une seconde source d'information. `aria-hidden`
 *   l'exclut donc de l'arbre d'accessibilite — la retirer ne changerait rien
 *   pour un lecteur d'ecran, et c'est voulu : le libelle seul doit suffire.
 *
 * IMPORTS STATIQUES, PAS `lucide-react/dynamic`
 *
 *   A la difference de `IconeDeLien` (`icones.tsx`), dont le nom vient d'un
 *   champ texte libre tape par un utilisateur — n'importe laquelle des
 *   ~1500 icones de la bibliotheque —, les six rubriques sont une liste
 *   FERMEE et connue a la compilation (`routes.ts`, `RUBRIQUES`) : un import
 *   statique par icone, jamais un chargement a la demande pour un ensemble
 *   qui ne varie pas a l'usage.
 */
import type { JSX } from 'react';
import {
  Calendar,
  ClipboardCheck,
  Home,
  type LucideIcon,
  Network,
  Settings,
  Users,
} from 'lucide-react';

/**
 * **LES CLES SONT CELLES DE `RUBRIQUES` (`routes.ts`), PAS RECOPIEES.** Une
 * cle qui ne correspond a aucune rubrique connue — ou une rubrique future que
 * ce module n'aurait pas encore reçue — rend simplement AUCUNE icone : voir
 * `IconeDeRubrique` ci-dessous. Une icone manquante est un defaut visuel
 * mineur, jamais un ecran casse.
 */
const ICONES_PAR_RUBRIQUE: Record<string, LucideIcon> = {
  accueil: Home,
  framework: Network,
  trombinoscope: Users,
  evenements: Calendar,
  monOnboarding: ClipboardCheck,
  administration: Settings,
};

export interface ProprietesIconeDeRubrique {
  /** La `cle` de la rubrique, telle que `routes.ts` la declare. */
  readonly cle: string;
  readonly taille?: number;
}

export function IconeDeRubrique({
  cle,
  taille = 20,
}: ProprietesIconeDeRubrique): JSX.Element | null {
  const Icone = ICONES_PAR_RUBRIQUE[cle];
  if (Icone === undefined) {
    return null;
  }
  return <Icone aria-hidden="true" size={taille} />;
}
