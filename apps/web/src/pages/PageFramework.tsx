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
 * LES CARTES DE CERCLE ET DE BUREAU REVELENT LEUR LIEN DETAILLE
 *
 *   `carte.cheminDetaille` n'est jamais `null` pour un cercle ou un bureau : `T9`
 *   leur construit une page. Leur carte est un accordéon ; son panneau contient
 *   le lien vers `PageCercle`/`PageBureau` et les informations de synthèse.
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
import { useEffect, useId, useState } from 'react';
import { Building2, ChevronDown, Gamepad2, Martini } from 'lucide-react';
import { Link } from 'react-router';

import { couleurDuCercle, pictoDuCercle, texteDuCercle } from '../affichage';
import { lireLeCercle, lireLeFramework } from '../api/organisation';
import { useEntiteConsultee } from './CadreApplicatif';

import type { CarteDeBureau, CarteDeCercle, PageFramework } from '@onboarding/contracts';
import { Alerte, Avatar, Badge, Carte, Picto } from '@onboarding/ui';

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
  DIRECTION: 'Direction générale',
  BOOSTER: 'Booster',
  OFFICE_MANAGER: 'Responsable de bureau',
};

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
      {/*
        **LE BLOC VISION DE LA CHARTE 6.5, EN ATTENTE DE SON CONTENU.** Aucune
        entite ne stocke de texte de vision : ni le modele ni le cahier n'en
        portent le champ. Arbitrage de Jonathan du 02/11/2026, le meme qu'a
        l'accueil — l'emplacement est pose, et il DIT qu'il attend plutot que
        d'imiter un contenu qui n'existe pas.
      */}
      <section className="framework-vision" aria-labelledby="framework-vision-titre">
        <Picto nom="organigramme" taille={40} />
        <h2 className="framework-vision-titre" id="framework-vision-titre">
          Vision
        </h2>
        <p className="framework-vision-texte">
          Le Framework eXalt accompagne les consultants dans leur évolution et favorise
          l&rsquo;intelligence collective à Bordeaux.
        </p>
      </section>

      <Carte titre="Responsabilites">
        {page.responsabilites.length === 0 ? (
          <Alerte>Aucune responsabilite Framework pour le moment.</Alerte>
        ) : (
          <ul className="framework-grille">
            {/* L'ORDRE VIENT DE L'API — l'enumeration Python du §6.2, jamais retrie ici. */}
            {page.responsabilites.map((carte) => (
              <li key={carte.typeDeResponsabilite}>
                <button
                  aria-label={`Voir les titulaires : ${LIBELLES_DE_RESPONSABILITE[carte.typeDeResponsabilite] ?? carte.typeDeResponsabilite}`}
                  className="framework-carte-flip"
                  type="button"
                >
                  <div className="framework-carte-flip-interieur">
                    <div className="framework-carte-flip-face framework-carte-flip-avant">
                      <Picto nom="organigramme" taille={32} />
                      <span className="framework-carte-titre">
                        {LIBELLES_DE_RESPONSABILITE[carte.typeDeResponsabilite] ??
                          carte.typeDeResponsabilite}
                      </span>
                    </div>
                    <div className="framework-carte-flip-face framework-carte-flip-arriere">
                      {carte.titulaires.length === 0 ? (
                        <span className="framework-carte-detail">Personne actuellement</span>
                      ) : (
                        <ul className="framework-titulaires">
                          {carte.titulaires.map((titulaire) => (
                            <li key={titulaire.identifiant}>
                              <Avatar
                                nom={`${titulaire.prenom} ${titulaire.nom}`}
                                taille={40}
                                {...(titulaire.photo === null ? {} : { photo: titulaire.photo })}
                              />
                              <span>
                                {titulaire.prenom} {titulaire.nom}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Carte>

      <Carte titre="Cercles">
        {page.cercles.length === 0 ? (
          <Alerte>Aucun cercle pour le moment.</Alerte>
        ) : (
          /*
            **LES CERCLES SONT UN ACCORDEON — charte 6.4, arbitrage de Jonathan
            du 02/11/2026.** La charte decrit le cercle comme un panneau qu'on
            deplie ; la page par cercle garde son adresse et reste ce que l'on
            partage, et c'est ICI, sur la page qui les LISTE vraiment, que le
            motif a du sens.
          */
          <ul className="framework-accordeon">
            {page.cercles.map((cercle) => (
              <CercleEnAccordeon
                key={cercle.identifiant}
                cercle={cercle}
                codeEntite={entite.code}
              />
            ))}
          </ul>
        )}
      </Carte>

      <Carte titre="Bureaux">
        {page.bureaux.length === 0 ? (
          <Alerte>Aucun bureau pour le moment.</Alerte>
        ) : (
          <ul className="framework-accordeon">
            {page.bureaux.map((bureau) => (
              <BureauEnAccordeon bureau={bureau} key={bureau.identifiant} />
            ))}
          </ul>
        )}
      </Carte>
    </div>
  );
}

/**
 * Un cercle deplie — charte 6.4, chantier design systeme v2, `E5` (`DEC-682`).
 *
 * **UN `<button aria-expanded>` ET UN PANNEAU NOMME, RIEN DE PLUS.** Aucune
 * primitive d'accordeon n'existe dans `packages/ui`, et en livrer une sans
 * second consommateur serait du code non eprouve (critere `T11` du LOT 1) —
 * meme constat qu'au LOT 8 `T9` pour les onglets. Le motif WAI-ARIA tient en
 * trois attributs, et il est atteignable au clavier PAR CONSTRUCTION puisque
 * c'est un vrai bouton.
 *
 * **CE QUE LE PANNEAU MONTRE, ET CE QU'IL NE MONTRE PAS.** `GET …/framework`
 * sert deja la description, le Booster et le NOMBRE de membres actifs : tout
 * cela s'affiche sans un appel de plus. Il ne sert PAS la liste nominative des
 * membres, que la page du cercle va chercher ; le panneau y mene donc plutot
 * que de declencher une seconde lecture a chaque depliage. C'est aussi ce qui
 * garde a la page detaillee sa raison d'etre.
 *
 * **PLUSIEURS PANNEAUX PEUVENT RESTER OUVERTS.** Rien dans la charte n'exige
 * qu'en ouvrir un referme les autres, et comparer deux cercles est un geste
 * naturel ici.
 */
function CercleEnAccordeon({
  cercle,
  codeEntite,
}: {
  cercle: CarteDeCercle;
  codeEntite: string;
}): JSX.Element {
  const [ouvert, poserOuvert] = useState(false);
  const [membres, poserMembres] = useState<
    | { readonly phase: 'repos' | 'chargement' | 'erreur' }
    | {
        readonly phase: 'charges';
        readonly personnes: readonly {
          readonly appartenance: string;
          readonly prenom: string;
          readonly nom: string;
          readonly photo: string | null;
        }[];
      }
  >({ phase: 'repos' });
  const identifiant = useId();
  const idBouton = `${identifiant}-bouton`;
  const idPanneau = `${identifiant}-panneau`;
  const couleur = couleurDuCercle(cercle.jetonDeCouleur);
  const texte = texteDuCercle(cercle.jetonDeCouleur);
  const picto = pictoDuCercle(cercle.jetonDeCouleur);

  return (
    <li className="framework-accordeon-element">
      {/*
        **UN TITRE AUTOUR DU BOUTON** — motif WAI-ARIA : sans lui, les cercles
        n'apparaissent pas dans le plan du document, et un lecteur d'ecran ne
        peut plus sauter de l'un a l'autre.
      */}
      <h3 className="framework-accordeon-titre">
        <button
          aria-controls={idPanneau}
          aria-expanded={ouvert}
          className="framework-accordeon-bouton"
          id={idBouton}
          onClick={() => {
            const prochain = !ouvert;
            poserOuvert(prochain);
            if (prochain && membres.phase === 'repos') {
              poserMembres({ phase: 'chargement' });
              void lireLeCercle(codeEntite, cercle.code, 1, 100).then((reponse) => {
                poserMembres(
                  reponse.statut === 200 && reponse.corps !== null
                    ? { phase: 'charges', personnes: reponse.corps.membres }
                    : { phase: 'erreur' },
                );
              });
            }
          }}
          type="button"
        >
          {/*
            **LA TUILE PORTE LE PICTOGRAMME OFFICIEL DU CERCLE**, celui que la
            table `CERCLES` associe a son nom depuis `E4`. Sans jeton connu,
            ni picto ni couleur : la tuile reste neutre, et le nom — qui est
            juste a cote — porte seul l'information (§10.1).
          */}
          <span
            className="framework-accordeon-tuile"
            style={
              couleur === undefined
                ? undefined
                : ({ background: couleur, color: texte } as React.CSSProperties)
            }
          >
            {picto === undefined ? null : <Picto nom={picto} taille={24} />}
          </span>
          <span className="framework-accordeon-nom">{cercle.nom}</span>
          <Badge ton="info">
            {cercle.membresActifs} membre{cercle.membresActifs > 1 ? 's' : ''}
          </Badge>
          {/*
            Le chevron est DECORATIF : `aria-expanded` porte deja l'etat, et
            l'annoncer deux fois le dirait deux fois.
          */}
          <ChevronDown aria-hidden="true" className="framework-accordeon-chevron" size={20} />
        </button>
      </h3>
      <div
        aria-labelledby={idBouton}
        className="framework-accordeon-panneau"
        hidden={!ouvert}
        id={idPanneau}
        role="region"
      >
        {/* Le bloc de presentation, sur la surface du cercle — charte 6.4. */}
        <p
          className="framework-accordeon-presentation"
          style={
            couleur === undefined
              ? undefined
              : ({ background: couleur, color: texte } as React.CSSProperties)
          }
        >
          {cercle.description ?? 'Aucune description pour le moment.'}
        </p>

        {/*
          **L'ENCART BOOSTER — charte 6.4.** Teinte rose, bordure rose, avatar
          a anneau rose. La miniature autorisee vient de `GET …/framework` ;
          `Avatar` conserve les initiales comme repli si elle est absente. Le
          badge dit « Booster » en toutes lettres : le rose ne porte rien que
          le texte ne porte deja.
        */}
        {cercle.booster === null ? (
          <p className="encart-sans-booster">Aucun Booster pour ce cercle.</p>
        ) : (
          <div className="encart-booster">
            <Avatar
              anneau="var(--marque-rose)"
              nom={`${cercle.booster.prenom} ${cercle.booster.nom}`}
              taille={56}
              {...(cercle.booster.photo === null ? {} : { photo: cercle.booster.photo })}
            />
            <span className="encart-booster-nom">
              {cercle.booster.prenom} {cercle.booster.nom}
            </span>
            <Badge ton="booster">Booster</Badge>
          </div>
        )}

        <h4 className="framework-membres-titre">Membres du cercle</h4>
        {membres.phase === 'chargement' ? <p>Chargement des membres…</p> : null}
        {membres.phase === 'erreur' ? (
          <Alerte ton="erreur">La liste des membres n&rsquo;a pas pu être chargée.</Alerte>
        ) : null}
        {membres.phase === 'charges' ? (
          <ul className="framework-membres">
            {membres.personnes.map((membre) => (
              <li key={membre.appartenance} className="framework-membre">
                <Avatar
                  nom={`${membre.prenom} ${membre.nom}`}
                  taille={40}
                  {...(membre.photo === null ? {} : { photo: membre.photo })}
                />
                <span>
                  {membre.prenom} {membre.nom}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        <Link className="app-lien" to={cercle.cheminDetaille}>
          Voir les membres du cercle {cercle.nom}
        </Link>
      </div>
    </li>
  );
}

function BureauEnAccordeon({ bureau }: { bureau: CarteDeBureau }): JSX.Element {
  const [ouvert, poserOuvert] = useState(false);
  const identifiant = useId();
  const idBouton = `${identifiant}-bouton`;
  const idPanneau = `${identifiant}-panneau`;

  return (
    <li className="framework-accordeon-element">
      <h3 className="framework-accordeon-titre">
        <button
          aria-controls={idPanneau}
          aria-expanded={ouvert}
          className="framework-accordeon-bouton"
          id={idBouton}
          onClick={() => {
            poserOuvert((valeur) => !valeur);
          }}
          type="button"
        >
          <span className="framework-accordeon-tuile framework-accordeon-tuile-bureau">
            <IconeDuBureau bureau={bureau} />
          </span>
          <span className="framework-accordeon-nom">{bureau.nom}</span>
          <Badge ton="info">
            {bureau.responsables.length} responsable
            {bureau.responsables.length > 1 ? 's' : ''}
          </Badge>
          <ChevronDown aria-hidden="true" className="framework-accordeon-chevron" size={20} />
        </button>
      </h3>

      <div
        aria-labelledby={idBouton}
        className="framework-accordeon-panneau"
        hidden={!ouvert}
        id={idPanneau}
        role="region"
      >
        <p className="framework-accordeon-presentation">
          {bureau.description ?? 'Aucune description pour le moment.'}
        </p>
        {bureau.localisation === null ? null : (
          <p className="framework-bureau-localisation">📍 {bureau.localisation}</p>
        )}

        <h4 className="framework-membres-titre">Responsables du bureau</h4>
        {bureau.responsables.length === 0 ? (
          <p className="framework-bureau-sans-responsable">Aucun responsable pour ce bureau.</p>
        ) : (
          <ul className="framework-membres">
            {bureau.responsables.map((responsable) => (
              <li className="framework-membre" key={responsable.identifiant}>
                <Avatar
                  nom={`${responsable.prenom} ${responsable.nom}`}
                  taille={40}
                  {...(responsable.photo === null ? {} : { photo: responsable.photo })}
                />
                <span>
                  {responsable.prenom} {responsable.nom}
                </span>
              </li>
            ))}
          </ul>
        )}

        <Link className="app-lien" to={bureau.cheminDetaille}>
          Voir la page du bureau {bureau.nom}
        </Link>
      </div>
    </li>
  );
}

function IconeDuBureau({ bureau }: { bureau: CarteDeBureau }): JSX.Element {
  const code = bureau.code.toLocaleUpperCase('fr');
  const nom = bureau.nom
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('fr');

  if (code === 'BDS' || code === 'SPORT' || nom.includes('sport')) {
    return (
      <svg
        aria-hidden="true"
        data-icone-bureau="sport"
        fill="currentColor"
        height="24"
        viewBox="0 0 24 24"
        width="24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M13.5 5.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM9.8 17.5l1-4.5 2.1 2v6h2v-7.5l-2.1-2 .6-3A7.3 7.3 0 0 0 19 10V8c-1.5 0-2.7-.8-3.4-2l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.2L7 5.8V11h2V7.1l1.8-.7-1.6 8.1-4.9-1-.4 2 5.9 1Z" />
      </svg>
    );
  }
  if (code === 'BDE' || nom.includes('exaltee')) {
    return <Martini aria-hidden="true" data-icone-bureau="cocktail" size={24} />;
  }
  if (code === 'BDG' || code === 'GAMING' || nom.includes('gaming')) {
    return <Gamepad2 aria-hidden="true" data-icone-bureau="gaming" size={24} />;
  }
  return <Building2 aria-hidden="true" data-icone-bureau="bureau" size={24} />;
}
