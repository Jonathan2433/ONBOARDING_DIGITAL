/**
 * La page Framework a l'ecran — LOT 6, `T9`, story `MVP-L06-US001`.
 *
 * LE CRITERE, ET CE QUE CETTE PAGE EN FAIT
 *
 *   « Les categories et responsabilites sont comprehensibles ; les cartes menent
 *   aux pages detaillees. » Le cahier §10.3 nomme TROIS familles — responsabilites,
 *   cercles, bureaux — et l'API les rend TOUJOURS TOUTES LES TROIS, meme vides
 *   (§7.0, quatrieme proposition). Les trois sections sont donc rendues
 *   inconditionnellement, chacune disant « aucun » quand elle est vide plutot que
 *   de disparaitre — une section absente et une section vide donneraient la meme
 *   observation alors qu'elles ne disent pas la meme chose.
 *
 * SEULES LES CARTES DE CERCLE ET DE BUREAU SONT DES LIENS, ET C'EST UN CHOIX MESURE
 *
 *   `carte.cheminDetaille` n'est jamais `null` pour un cercle ou un bureau : `T9`
 *   leur construit une page, ci-dessous et dans `PageCercle`/`PageBureau`.
 *
 *   Pour `DSM` et `ESM`, `chemin_detaille` n'est PAS `null` non plus — l'annexe A
 *   §10.1 leur donne une page propre. **Mais aucune route ne la sert.**
 *   `ECART-062` est ouvert et attend Léa : le §10.1 donne au DSM « Modifier la
 *   page DSM », et aucun `page_type` du §15.1 ne porte cette page — personne ne
 *   sait aujourd'hui quel contenu elle afficherait. Construire un lien vers une
 *   adresse qu'aucune route ne sert serait le defaut que `PageRubrique` existe
 *   pour eviter : « un lien qui aboutit au fourre-tout 404 est atteignable et
 *   INUTILE ». Les cartes de responsabilite restent donc de l'INFORMATION, pas
 *   des liens, jusqu'a ce que Léa tranche.
 *
 * LES LABELS SONT LOCAUX, ET C'EST DELIBERE
 *
 *   `affichage.ts` existe pour ce que DEUX ecrans au moins doivent presenter de
 *   la meme facon (§7.27). Cette page est la SEULE a afficher les quatre types de
 *   responsabilite Framework : les y ajouter serait une abstraction sans second
 *   consommateur.
 *
 * CHANTIER FRONT, S5 (`DEC-672`) : `CARTE`/`BADGE`, ICONE DE BUREAU
 *
 *   **Mesure avant tout code** : ni `Carte` ni `Badge` n'etaient employes ici —
 *   les trois sections etaient de simples `<section>` manuelles, et les
 *   compteurs (membres actifs, responsables) de la prose dans un
 *   `<span className="framework-carte-detail">`, cahier §13.2. Les trois
 *   sections deviennent des `<Carte titre="…">` (la region nommee et le `<h2>`
 *   que `Carte` fournit dejà remplacent le `<section aria-labelledby>`/`<h2 id>`
 *   ecrits a la main) ; les deux compteurs deviennent des `Badge`. Un bureau
 *   porte desormais une icone decorative (`Building2`, `lucide-react`,
 *   `aria-hidden`) — un cercle garde sa bordure de couleur, deja sa propre
 *   marque visuelle distinctive, jamais une icone de plus pour la meme
 *   information.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import { Link } from 'react-router';

import { couleurDuCercle } from '../affichage';
import { lireLeFramework } from '../api/organisation';
import { useEntiteConsultee } from './CadreApplicatif';

import type {
  CarteDeBureau,
  CarteDeCercle,
  PageFramework,
  TitulaireFramework,
} from '@onboarding/contracts';
import { Alerte, Badge, Carte } from '@onboarding/ui';

/**
 * Le libelle francais des deux categories qui en ont un — cahier §6.2.
 *
 * **NI `DSM` NI `ESM` N'Y FIGURENT, ET C'EST DELIBERE.** Les deux se lisent tels
 * quels, donc rien a traduire — mais `ESM` est AUSSI un code de la matrice §20,
 * `rolesAdministration` du manifeste, et `make cadre-check` refuse tout code de
 * ce genre ecrit en litteral dans le frontend, source unique de TS et Python
 * (`DEC-492`). L'ecran affiche donc `carte.typeDeResponsabilite` TEL QUEL pour
 * ces deux-la, jamais une chaine posee ici.
 */
const LIBELLES_DE_RESPONSABILITE: Readonly<Record<string, string>> = {
  BOOSTER: 'Booster',
  OFFICE_MANAGER: 'Responsable de bureau',
};

function nomsDesTitulaires(titulaires: readonly TitulaireFramework[]): string {
  return titulaires.map((t) => `${t.prenom} ${t.nom}`).join(', ');
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'page'; readonly page: PageFramework }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageFramework(): JSX.Element {
  const { entite } = useEntiteConsultee();
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    const abandon = new AbortController();
    void lireLeFramework(entite.code, abandon.signal).then(
      (reponse) => {
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'page', page: reponse.corps }
            : { phase: 'erreur', statut: reponse.statut },
        );
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setEtat({ phase: 'erreur', statut: 0 });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [entite.code]);

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement du Framework…</Alerte>;
  }

  if (etat.phase === 'erreur') {
    return (
      <Alerte ton="erreur" urgence="alerte">
        {etat.statut === 401
          ? 'Votre session a expire. Reconnectez-vous pour consulter le Framework.'
          : "Le Framework n'a pas pu etre charge. Cela ne dit rien de son contenu : verifiez votre connexion, puis reessayez."}
      </Alerte>
    );
  }

  const { page } = etat;

  return (
    <div className="framework">
      <Carte titre="Responsabilites">
        {page.responsabilites.length === 0 ? (
          <Alerte>Aucune responsabilite Framework pour le moment.</Alerte>
        ) : (
          <ul className="framework-grille">
            {/* L'ORDRE VIENT DE L'API — l'enumeration Python du §6.2, jamais retrie ici. */}
            {page.responsabilites.map((carte) => (
              <li key={carte.typeDeResponsabilite}>
                <div className="framework-carte framework-carte-information">
                  <span className="framework-carte-titre">
                    {LIBELLES_DE_RESPONSABILITE[carte.typeDeResponsabilite] ??
                      carte.typeDeResponsabilite}
                  </span>
                  <span className="framework-carte-detail">
                    {carte.titulaires.length === 0
                      ? 'Personne actuellement'
                      : nomsDesTitulaires(carte.titulaires)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Carte>

      <Carte titre="Cercles">
        {page.cercles.length === 0 ? (
          <Alerte>Aucun cercle pour le moment.</Alerte>
        ) : (
          <ul className="framework-grille">
            {page.cercles.map((cercle) => (
              <li key={cercle.identifiant}>
                <CarteDeCercleAFramework cercle={cercle} />
              </li>
            ))}
          </ul>
        )}
      </Carte>

      <Carte titre="Bureaux">
        {page.bureaux.length === 0 ? (
          <Alerte>Aucun bureau pour le moment.</Alerte>
        ) : (
          <ul className="framework-grille">
            {page.bureaux.map((bureau) => (
              <li key={bureau.identifiant}>
                <CarteDeBureauAFramework bureau={bureau} />
              </li>
            ))}
          </ul>
        )}
      </Carte>
    </div>
  );
}

function CarteDeCercleAFramework({ cercle }: { cercle: CarteDeCercle }): JSX.Element {
  //  **LA COULEUR N'EST JAMAIS LA SEULE INFORMATION — §8.1 du modele, §7.42.**
  //  `cercle.nom` est un champ obligatoire du contrat ; `jetonDeCouleur` est
  //  nullable, et un jeton inconnu ou absent laisse la bordure neutre. Le nom
  //  reste du texte dans les deux cas.
  const couleur = couleurDuCercle(cercle.jetonDeCouleur);
  return (
    <Link
      className="framework-carte framework-carte-cercle"
      style={
        couleur === undefined ? undefined : ({ '--framework-cercle-couleur': couleur } as never)
      }
      to={cercle.cheminDetaille}
    >
      <span className="framework-carte-titre">{cercle.nom}</span>
      <Badge ton="marque">
        {cercle.membresActifs} membre{cercle.membresActifs > 1 ? 's' : ''}
      </Badge>
      <span className="framework-carte-detail">
        {cercle.booster === null
          ? 'Aucun Booster'
          : `Booster : ${cercle.booster.prenom} ${cercle.booster.nom}`}
      </span>
    </Link>
  );
}

function CarteDeBureauAFramework({ bureau }: { bureau: CarteDeBureau }): JSX.Element {
  return (
    <Link className="framework-carte" to={bureau.cheminDetaille}>
      <span className="framework-carte-entete">
        <Building2 className="icone-bureau" aria-hidden="true" size={18} />
        <span className="framework-carte-titre">{bureau.nom}</span>
      </span>
      <Badge ton="marque">
        {bureau.responsables.length} responsable{bureau.responsables.length > 1 ? 's' : ''}
      </Badge>
    </Link>
  );
}
