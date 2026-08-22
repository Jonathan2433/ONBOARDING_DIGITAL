# Compte rendu — LOT 3, sous-étape `T11`

**Les huit écrans d'authentification**
**Story :** aucune — le périmètre est la liste d'interfaces du LOT 3
**Réalisée le :** 22 août 2026
**Décision produite :** `DEC-537`
**Migration produite :** **aucune**

---

## 1. Le compte est dérivé, et il fallait le dériver

Le cahier §17.5 et la roadmap donnent **la même liste**, en **six puces** dont la dernière nomme
**trois** pages :

```text
page de connexion ; confirmation de demande de lien ;
lien expire ou deja consomme ; connexion administrateur ;
deconnexion ; pages `403`, `404` et erreur generale.
```

**5 + 3 = huit.** Le contrôle relit le document, compte les puces, et exige que **chaque libellé
déclaré y figure mot pour mot** — une reformulation « qui veut dire la même chose » ne serait pas
vérifiable. C'est le §7.27, sixième occurrence dans ce lot.

**Et un écran n'est pas une route.** « Lien expiré ou déjà consommé » est **l'état d'échec** de la
route qui consomme le lien : le courriel ouvre `/connexion/lien`, la page appelle l'API, et c'est son
refus qui est l'écran. Les compter en routes en donnerait sept ou neuf selon l'humeur ; `routes.ts`
déclare donc cet écran avec `etatDeRoute: true`.

---

## 2. Le routeur : `DEC-456` tranchait déjà, dans l'autre sens que mon instinct

Mon premier réflexe a été d'écrire un routeur minimal — huit routes plates, pas de dépendance. **Le
corpus dit le contraire, et il faut le lire avant de décider :**

- le cahier **§17.1 nomme React Router** dans sa pile technique ;
- **`DEC-456` ne l'installait pas « faute d'usage avant le LOT 4 »**, et son motif était explicite :
  « installer cinq bibliothèques sans usage ajouterait une surface d'audit sans contrepartie ».

**`T11` crée cet usage une étape plus tôt que `DEC-456` ne l'anticipait**, les huit écrans
appartenant au LOT 3. La condition est remplie ; écrire un routeur maison aurait été **ignorer ce qui
est décidé**, c'est-à-dire le §6.5 à l'envers.

**Les quatre autres bibliothèques restent dehors**, et c'est le même raisonnement appliqué
honnêtement : deux formulaires de deux champs n'ont pas d'usage pour **React Hook Form** ni **Zod** —
l'API est de toute façon « l'autorité finale » sur la validation, règle 5 — trois mutations
ponctuelles n'ont pas d'usage pour **TanStack Query**, et aucun composant complexe n'appelle **Radix
UI**. `make audit` reste à **zéro avis, zéro tolérance**.

**`BrowserRouter` et non `HashRouter`** : les liens de magic link sont des URL réelles envoyées par
courriel, et une ancre `#` n'atteindrait jamais le serveur.

---

## 3. Le contrôle exerce pour la première fois un repli posé il y a quatre sous-étapes

`Caddyfile.execution` porte `try_files {path} /index.html` **depuis `T7` du LOT 1**, avec un
commentaire qui l'anticipait : « le routeur du LOT 4 introduira des chemins qui ne correspondent à
aucun fichier ».

**Il n'avait jamais eu un seul chemin à replier.** C'est le §7.16 — *ce qui n'a jamais tourné n'est
pas éprouvé* — et `make ecrans-check` est la première chose qui l'exerce : huit chemins, plus un lien
profond avec chaîne de requête.

**Le type MIME fait foi, jamais le code.** Vite rend **200 + `index.html`** pour tout chemin inconnu
(§7.10) : un 200 seul ne prouverait rien, et c'est exactement le défaut `T5-6` du LOT 1. Le contrôle
exige `text/html` **et** la présence du point de montage.

**Et il vérifie l'inverse aussi** : `/api/*` ne doit **pas** recevoir l'artefact statique. Un repli
qui déborderait sur l'API répondrait 200 à sa place, ce que `DEC-470` interdit — mesuré à **404,
`application/json`**.

---

## 4. Trois invariants de sécurité que l'interface pouvait défaire

**La réponse générique.** L'API rend le même 202, le même corps et les mêmes en-têtes que l'adresse
existe ou non — critère central du lot. **Un écran qui afficherait deux messages différents rouvrirait
l'oracle côté interface.** Le message affiché **vient donc de la réponse**, la page n'en fabrique
aucun, et un test soumet **deux adresses différentes** et exige un rendu identique.

Corollaire : **aucune validation de forme sur l'adresse**. Une adresse jugée mal formée produirait un
message différent, et un attaquant y lirait « cette adresse a une forme acceptable » puis « cette
adresse existe ». Même motif que l'API en `T3`.

**Le jeton de magic link quitte la barre d'adresse.** Le courriel le porte en chaîne de requête — seul
moyen de le transmettre — mais la page l'efface par `history.replaceState` dès sa lecture, et
l'envoie **dans le corps**. Sans cela il resterait dans l'historique du navigateur et partirait dans
l'en-tête `Referer` de toute ressource chargée ensuite. **`replaceState` et non `pushState`** :
`pushState` laisserait l'URL avec le jeton dans l'historique, ce qu'on retire précisément.

**Aucun stockage navigateur.** Interdit absolu du §9.5, vérifié sur les **sept sources d'écran**,
commentaires retirés — et la liste des fichiers est **dérivée du répertoire**, pas recopiée.

---

## 5. Le linter a imposé un découpage, et il avait raison

`react-hooks/set-state-in-effect` refusait un `setState` synchrone dans l'effet qui consomme le lien.
La correction n'a pas été de désactiver la règle mais de **dériver l'état initial pendant le rendu** —
ce qui n'est possible qu'à partir d'une lecture **pure**.

`extraireLeJeton`, qui lisait **et** effaçait, s'est donc scindée en `lireLeJeton` (pure) et
`effacerLeJetonDeLUrl` (effet). **Le découpage imposé est meilleur que celui que j'avais écrit** : une
lecture pure et un effet de bord ne devaient pas être la même fonction, et chacune s'éprouve
maintenant seule.

**Et un garde-fou que `StrictMode` a rendu nécessaire.** React monte deux fois en développement : sans
un `useRef`, le second appel consommerait un jeton **déjà utilisé** et l'écran de refus s'afficherait
sur un lien parfaitement valide. Un test le vérifie sous `StrictMode`, et il exige **un seul** appel.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **661 tests, 0 échec** |
| Vitest | **133 tests** — 1 `contracts`, 90 `ui`, **42 `web`** (25 avant `T11`) |
| `make check` · `make audit` | **0** · **0** — l'audit reste à **zéro avis** après l'ajout du routeur |
| **`make ecrans-check`** | **0 — 7 contrôles**, à travers Caddy en HTTPS |
| `web-check` · `sessions-check` · `sessions-temoin` | **0** · **0** · **0** — le routeur n'a pas cassé la page de statut |
| `images-check` | **0** — la cible `execution` est toujours nommée |

```text
6 puces au cahier -> 8 ecrans, 8 declares
les 8 libelles figurent LITTERALEMENT dans le cahier
0 couleur litterale, 40 references aux jetons — temoin OK
7 sources examinees, aucun stockage navigateur
8 chemins servis en `text/html` avec le point de montage — le repli SPA est EXERCE
le lien de l'e-mail est servi, chaine de requete comprise
`/api/*` reste a l'API (404, application/json)
```

**Le témoin du contrôle de couleur est explicite** : le motif doit **savoir trouver** une couleur.
Sans lui, un motif cassé rendrait toujours une liste vide, et l'absence prouverait l'absence de
contrôle plutôt que l'absence de couleur.

---

## 7. Deux défauts, tous deux dans mes propres contrôles

| № | Défaut | Comment |
|:--:|---|---|
| `T11-1` | **Mon extraction des chemins lisait trop large.** Le motif `^\s+\w+: '(…)',$` attrapait aussi les `libelleCorpus` de `ECRANS`, si bien que « page de connexion » devenait un chemin d'URL. Bornée au bloc `CHEMINS` | première exécution |
| `T11-2` | **Le contrôle plantait au lieu de nommer le chemin fautif.** Vingt lignes de trace `urllib` disant « nodename nor servname provided », sans dire **quel** chemin — or c'était tout le diagnostic | la même exécution |

`T11-2` est le §7.18 : *la première correction à écrire est celle qui te dira pourquoi.* Une erreur de
transport rend désormais un statut `0` et le motif, et le contrôle **rapporte** au lieu de s'arrêter.

**Et un troisième, dans mon propre test** : `vi.stubGlobal('history', …)` remplace l'objet **entier**,
donc `pushState` disparaît avec lui. J'appelais `pushState` **après** avoir posé le double. Deux
échecs, ordre inversé.

---

## 8. Ce qui n'est PAS couvert

- **le portail.** `LOT 4`. La consommation réussie d'un lien ouvre la session et le dit, sans promettre
  une destination qui n'existe pas ;
- **`axe` et Playwright**, nommés au §17.1 : ils appartiennent au **LOT 12**, qualité transversale.
  `jsx-a11y` examine les huit écrans neufs — c'est le premier vrai volume qu'il voit depuis son
  installation — et les jetons sont mesurés contre WCAG 2.2 AA, mais **aucun audit automatisé de page
  rendue** n'est fait ici ;
- **le rendu dans un vrai navigateur.** Le contrôle prouve que les huit chemins sont **servis** ;
  ce sont les tests Vitest qui prouvent que chaque écran **se rend** avec son `<h1>` unique et son
  `<main>`. Les deux ensemble sont la preuve ; ni l'un ni l'autre ne suffit ;
- **les cinq largeurs de recette.** `LARGEURS_RECETTE` existe dans `packages/ui` depuis `T10` du
  LOT 1 ; aucune mesure de débordement n'est faite ici. **LOT 12** ;
- **React Hook Form, Zod, TanStack Query, Radix UI** — sans usage, `DEC-537` ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 9. Ce que `T12` devra savoir

1. **`T12` est la dernière** : audit des **sept** événements du §10.6, recette, et checklist `G3`.
   `auth_event` porte désormais **deux acteurs** — `person_id` et `service_account_id` depuis la
   migration `0013` — et **un contrôle qui ne compterait que le premier déclarerait l'audit acquis en
   ignorant les comptes de service.**
2. **Trois contrôles du §30 restent à classer pour ce lot**, et `make recette-modele-check` échoue si
   l'un cesse de l'être. `§30.22` est acquis depuis `T9`, `§30.11` depuis `T3`.
3. **Le contrôle de résidu que je recommande depuis `T10-2`.** Six occurrences de la même leçon dans
   ce lot — *la trace d'un refus sans acteur échappe à tout nettoyage par identité* — dont une commise
   une sous-étape après l'avoir écrite. **Un contrôle qui mesure le résidu après chaque suite** vaut
   mieux qu'une septième promesse de vigilance. C'est le §7.2 : quand une classe d'erreur résiste, on
   change d'outil.
4. **Le test de performance du LOT 2 (§30.25) a échoué une fois** en `T10`, non reproduit sur deux
   suites complètes. Il mesure des durées inférieures à la milliseconde ; `T12` porte la performance.
5. **La recette n'est pas éprouvée sous le régime actuel.** Elle exécute l'artefact **publié et
   épinglé par empreinte** (`DEC-486`), de révision antérieure à `T1` : son API se connecte encore en
   **superutilisateur**, mesuré. Il faut republier puis `make images-pin`, **avant `G3`**, avec
   `make separations-check`.
6. **Deux écarts sont à annoncer à la porte** : `ECART-032` — le backlog interdit plus large que ses
   trois sources — et `ECART-035`, les invitations qui n'existent pas. Plus un constat de méthode : le
   **§8 de `fiche-lot-3.md` a été faux trois fois sur quatre**, et un relecteur ne devrait pas s'y
   fier sans relire le cahier.
