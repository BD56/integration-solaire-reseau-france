# Journal du projet

Fichier de suivi des décisions et des constats, tenu par ordre chronologique inverse (le plus récent en haut).

Objectif : garder une trace lisible par toute personne ou assistant qui reprend le projet, y compris sans accès à l'historique des conversations. Chaque entrée précise les faits établis, les décisions actées, et ce qui reste ouvert.

---

## 2026-07-26 (suite) : nettoyage revu, TCO reconstruit, puissance installée déduite

Séance consacrée à la compréhension des données plutôt qu'à la production de résultats. Plusieurs affirmations de la séance précédente ont été corrigées après vérification.

### 1. Changements d'heure : mécanisme établi, traitement changé

La cause des doublons d'horodatage était juste, mais le mécanisme décrit était faux. Cinq contrôles convergents : les 14 dates concernées sont toutes un **dernier dimanche de mars**, toutes à **01:00 et 01:30 UTC**, avec **56 lignes par région pour les 12 régions**, **zéro doublon** si l'on regarde la colonne `heure` de la source, et **zéro doublon en octobre**.

Le mécanisme réel : deux **créneaux locaux différents** (02:00 et 03:00) tombent sur le **même instant UTC**, puisque 02:00 CET et 03:00 CEST désignent la même seconde. Ce ne sont pas deux fois la même ligne.

La source publie **toujours 48 créneaux de 30 minutes par jour**, y compris les jours de bascule, ce qui produit deux anomalies opposées :

| | Mars | Octobre |
|---|---|---|
| Horloge locale | saute 02:00 vers 03:00 | recule 03:00 vers 02:00 |
| L'heure 02:00 à 02:59 | n'existe pas | a lieu deux fois |
| Effet | 2 créneaux **fictifs** publiés | 1 occurrence réelle **non publiée** |
| Résultat | **doublon** en UTC | **trou** en UTC (saut de 1 h 30) |

**Décision** : on ne déduplique plus sur l'ordre du fichier (`keep="first"`, arbitraire), on supprime explicitement les créneaux locaux 02:00 et 02:30 du dimanche de mars. Règle appliquée : parmi deux lignes partageant le même instant UTC, retirer celle dont l'étiquette locale est la plus petite. Résultat vérifié : 336 lignes retirées, le jour de bascule retrouve ses **46 créneaux** (durée réelle de 23 heures), zéro doublon restant.

Rien n'est comblé en mars : **aucune donnée ne manque**, le jour compte bien 46 horodatages UTC distincts. Combler reviendrait à inventer des observations pour un moment qui n'a pas existé.

Sur les 336 lignes en cause, **29,2 % portaient des valeurs différentes** (écart médian de 128 MW sur la consommation, soit 3,25 %, jusqu'à 13,7 %). Le choix précédent n'était donc pas anodin, seulement négligeable en volume (0,0035 % du jeu).

⚠️ **À reprendre pour un futur volet de prévision** : à cause du trou d'octobre, la série UTC **n'est pas une grille régulière** (un saut de 1 h 30 par an et par région). Tout traitement supposant un pas constant (décalages, autocorrélation, modèle de série temporelle) butera dessus. Sans effet sur les profils descriptifs, et sans effet sur le solaire (0,07 MW en moyenne à cette heure, il fait nuit). Si une grille régulière devient nécessaire, l'interpolation est acceptable (erreur médiane mesurée à 65 MW, soit 3,2 % du niveau nocturne) **à condition de marquer les lignes imputées**.

### 2. `ND` et `-` sont deux choses différentes

| Marqueur | Lignes | Régions | Reste de la ligne |
|---|---|---|---|
| `ND` | 12 | les 12 | `consommation` et `solaire` **vides** |
| `-` | 96 | 2 (Centre-Val de Loire, Île-de-France) | `consommation` et `solaire` **renseignés** |

`ND` désigne une ligne entièrement vide, supprimée de toute façon par le filtre sur `consommation`. `-` désigne une ligne valide où seul l'éolien manque : ce sont exactement les 96 lignes où `demande_nette` reste indéfinie. **Point ouvert** : s'agit-il de « non mesuré » (valeur manquante correcte) ou de « pas de parc éolien » (auquel cas zéro serait plus juste) ? Non tranché.

### 3. Deux définitions de la demande nette

`demande_nette = consommation − solaire − eolien` suivait la convention du secteur, mais mélange deux phénomènes alors que le projet porte sur le solaire. Effet constaté : les bandes très larges des Hauts-de-France dans les profils saisonniers viennent de l'éolien, pas du solaire (1,8 % de couverture), ce qui faussait partiellement la comparaison entre régions.

**Décision** : calculer les deux côte à côte plutôt que d'en imposer une. `demande_nette` (convention) et `demande_nette_solaire = consommation − solaire` (objet d'étude). L'écart entre les deux mesure exactement l'apport de l'éolien, au lieu de le dissoudre.

### 4. TCO reconstruit, puissance installée déduite

Les colonnes `tco_` et `tch_` sont absentes de **2013 à 2019** (0 % renseigné) et présentes à 100 % de **2020 à 2026**. RTE a commencé à les publier en 2020.

- **TCO reconstructible exactement.** `tco_filiere = 100 × filiere / consommation`, vérifié sur toutes les filières : écart absolu médian de 0,003 point, maximum 0,01, soit de l'arrondi. Reconstruit pour 2013-2019 par `completer_tco()` : **1 472 076 lignes**, complétude de 47 % à **100 %**. Les valeurs publiées ne sont jamais écrasées, et les lignes recalculées sont marquées par la colonne **`tco_reconstruit`**. ⚠️ N'apporte **aucune information nouvelle** : c'est une fonction déterministe de colonnes déjà présentes.
- **TCH non reconstructible** (la puissance installée n'est pas fournie), mais **inversible** : `puissance installée = 100 × filiere / tch`. Contrairement au TCO, c'est une information réellement nouvelle. Fonction `capacite_installee()`, disponible sur **2020-2026 seulement**.

Puissance solaire installée déduite (MW, médiane annuelle) :

| Année | Nouvelle-Aquitaine | Occitanie | Hauts-de-France | Île-de-France |
|---|---|---|---|---|
| 2020 | 2 546 | 2 057 | 167 | 125 |
| 2022 | 3 444 | 2 758 | 350 | 185 |
| 2024 | 4 488 | 3 629 | 554 | 322 |
| 2026 | 6 596 | 5 087 | 1 036 | 510 |

Piste à confirmer : la croissance la plus rapide en **relatif** est dans les régions les **moins** ensoleillées (Hauts-de-France ×6,2, Île-de-France ×4,1 contre ×2,5 au Sud), alors que les niveaux absolus restent dominés par le Sud. Utile pour la sous-question 2 et pour la phase 2.

### 5. Complétude du jeu

Par ligne : moyenne **67,4 %**, médiane **46,9 %**. Par colonne : 13 colonnes à 100 %, `nucleaire` à 75,0 %, `pompage` à 73,7 %, les `tco_`/`tch_` autour de 47,5 % (avant reconstruction), `eolien_terrestre`/`offshore` et les batteries à 40,0 %, `tch_nucleaire` à 27,7 %, `column_30` à 0 %.

⚠️ `eolien` affiche 100 % alors qu'elle contient `ND` et `-` : ce sont des valeurs manquantes déguisées en texte, que `notna()` ne voit pas. Complétude réelle 99,996 %.

### 6. Deux affirmations corrigées

- **« Le pic solaire est à 13 h locale en juin comme en décembre » était faux.** Mesure au pas de 30 minutes (barycentre de la courbe, Nouvelle-Aquitaine, 2023-2025) : environ **13 h en décembre** contre **14 h en juin**. La bascule se produit entre mars et avril puis entre octobre et novembre, c'est-à-dire **exactement aux dates de changement d'heure**. Ce n'est donc pas un effet de saison mais l'heure légale qui bouge. L'erreur venait d'un arrondi à l'heure entière sur un échantillon trop agrégé.
- **« La sous-question 1 est traitée » était trop fort.** Le matériel existe (profils, figures, indicateurs) mais ne porte que sur 2 régions sur 12 et sur 2023-2025, n'utilise qu'une des deux définitions de la demande nette, a été produit avant la correction du nettoyage, et n'a pas été validé par Bryan. Non close.

### 7. Fichier de contrôles : reporté

Un fichier `src/controles.py` renvoyant un tableau de verdicts avait été décidé, puis **reporté**. Raison : un fichier de contrôles fige ce qu'on croit savoir des données ; l'erreur sur le pic solaire montre que la compréhension n'est pas encore stable, et graver des croyances fausses est pire que pas de contrôles (fausse assurance ou fausses alertes). Son utilité est de plus nulle tant qu'on ne retélécharge pas régulièrement.

Deux enseignements conservés pour le jour où il sera écrit :

- **préférer les invariants aux comptages figés.** « Tous les doublons tombent un dernier dimanche de mars à 01:00 ou 01:30 UTC » reste vrai quand le jeu grandit et teste réellement l'hypothèse ; « il y a exactement 336 doublons » deviendra faux en mars 2027 et déclenchera une fausse alerte.
- **un tableau de verdicts plutôt que des `assert`**, pour lister tous les problèmes au lieu de s'arrêter au premier.

### 8. Documentation

`docs/dictionnaire_donnees.md` enrichi d'une colonne **« En clair »** dans chaque tableau (explication en langage courant), d'une section décrivant les **9 colonnes calculées** par `preparation.py`, et de deux précisions qui prêtaient à confusion : les filières sont des **puissances instantanées en MW** et non des quantités d'énergie, et le **seul stockage observable** du jeu est le pompage, les colonnes de batterie étant vides.

### 9. Points ouverts

- Nature des 96 lignes `-` de l'éolien : non mesuré ou parc absent (section 2).
- Sous-question 1 à clore réellement : étendre au-delà de 2 régions et de 2023-2025, exploiter `demande_nette_solaire`, régénérer les figures après correction du nettoyage, et faire valider les résultats par Bryan.
- Sous-questions 2 (évolution pluriannuelle) et 3 (équilibrage) non commencées.
- Le code de faisabilité de l'entrée précédente n'est toujours pas porté dans le dépôt.
- Puissance installée avant 2020 : nécessiterait une source externe (registre des installations d'ODRE) plutôt qu'une extrapolation à rebours sur sept ans.

---

## 2026-07-26 : sous-question 1 traitée, profils saisonniers de demande nette

Première sous-question descriptive traitée. Le dépôt passe de « aucun graphique produit » à trois figures et un module de préparation partagé.

### 1. Décisions de cadrage actées

- **Nettoyage centralisé.** Création de `src/preparation.py`, source unique du chargement et du nettoyage. `notebooks/01_exploration.py` est réécrit pour l'appeler et se limite désormais au contrôle qualité ; il ne redéfinit plus ses propres corrections. Tout script d'analyse doit passer par `charger_donnees()`.
- **Pas d'agrégat national.** L'écart entre régions est l'objet d'intérêt, l'agrégat le dilue. Comparaison sur deux régions contrastées : **Nouvelle-Aquitaine** (couverture solaire moyenne 16,3 % sur 2024-2025) contre **Hauts-de-France** (1,8 %), dont les consommations moyennes sont proches (4 681 contre 5 305 MW), ce qui rend la comparaison honnête.
- **Profils par saison, pas journée isolée.** La sous-question 1 porte sur la déformation saisonnière. Une journée réelle est conservée en complément illustratif.
- **Moyenne, médiane et éventail de quantiles tracés ensemble.** Justification retenue : un réseau se dimensionne sur le jour le plus contraignant, pas sur le jour moyen. Les déciles d10 et d90 portent donc l'information utile ; l'écart moyenne contre médiane sert d'indicateur d'asymétrie (en mi-journée le solaire a un plafond de ciel clair et les nuages ne tirent que vers le bas).
- **Années récentes uniquement** pour les profils (2023 à 2025, paramétrable). Agréger 2013 à 2026 mélangerait une époque quasi sans solaire et une époque très équipée, ce qui diluerait le creux recherché. L'évolution dans le temps relève de la sous-question 2.

### 2. Constat nouveau : le fuseau horaire est un piège actif

`date_heure` est en **UTC**, alors que les colonnes `date` et `heure` sont en **heure locale**. Raisonner sur l'heure UTC fabrique une fausse déformation saisonnière, exactement ce que la sous-question 1 cherche à mesurer :

| Mois | Pic solaire moyen en UTC | Pic solaire moyen en heure locale |
|---|---|---|
| Juin | 11 h | 13 h |
| Décembre | 12 h | 13 h |

Le décalage d'une heure est un pur artefact du changement d'heure. `src/preparation.py` ajoute donc `date_heure_locale` (Europe/Paris) et `heure_decimale`, à utiliser pour tout profil journalier. À reporter dans le dictionnaire de données.

### 3. Doublons : cause confirmée, `nature` mise hors de cause

Les 336 lignes en doublon sur (région, horodatage) tombent toutes sur les **14 dates de passage à l'heure d'été** (dernier dimanche de mars, 2013 à 2026). La colonne `nature` n'y est pour rien : c'est un découpage temporel (définitives jusqu'à 2024, consolidées pour 2025 et 2026), sans recouvrement. Les deux modalités sont conservées, les filtrer supprimerait les deux années les plus riches en solaire.

### 4. Résultats chiffrés (creux de mi-journée et remontée du soir, 2023 à 2025)

Creux mesuré entre 10 h et 16 h, pic du soir entre 18 h et 21 h, en MW. « Jour le plus creusé » correspond au décile d10.

| Région | Saison | Cas | Creux | Pic du soir | Remontée |
|---|---|---|---|---|---|
| Nouvelle-Aquitaine | Été | jour médian | 1 505 | 3 726 | 2 221 |
| Nouvelle-Aquitaine | Été | jour le plus creusé | 563 | 3 147 | **2 584** |
| Nouvelle-Aquitaine | Automne | jour le plus creusé | 602 | 3 379 | **2 778** |
| Nouvelle-Aquitaine | Hiver | jour médian | 4 019 | 5 689 | 1 670 |
| Hauts-de-France | Été | jour médian | 3 469 | 3 773 | 304 |
| Hauts-de-France | Hiver | jour médian | 4 480 | 5 010 | 530 |

### 5. Livrables

- `src/preparation.py` : chargement, nettoyage, heure locale, saisons, demande nette.
- `notebooks/01_exploration.py` : réécrit, contrôle qualité uniquement.
- `notebooks/02_profils_saisonniers.py` : profils, figures et indicateurs chiffrés.
- `figures/01_profils_saisonniers.png`, `02_saisons_superposees.png`, `03_journee_illustration.png`.

Palette catégorielle validée par outil (séparation en vision normale 27,6 ; en vision déficiente 9,2) plutôt que choisie à l'œil.

### 6. Points ouverts

- Reporter au dictionnaire de données le constat sur le fuseau horaire (section 2).
- Sous-question 2 (évolution pluriannuelle du creux) et sous-question 3 (équilibrage) restent à traiter.
- Le code de faisabilité de l'entrée du 2026-07-25 n'est toujours pas porté dans le dépôt.
- La piste prévision reste en attente, tributaire d'une source météo exogène.

---

## 2026-07-25 : étude de faisabilité d'un volet prévision

Entrée rédigée depuis une conversation généraliste (hors session projet). Contexte, constats et décisions à reprendre ici.

### 1. Contexte personnel utile au cadrage

- Recherche en cours : un **stage de fin d'études de M2**, second semestre, environ janvier à fin août 2027. Ce n'est pas une alternance (la mention « alternance » du CV daté du 13/04/2026 est périmée).
- Fenêtre de travail sur ce projet : le **mois d'août 2026**, avant la rentrée de M2.
- Objectif affiché : renforcer le portfolio sur un axe plus technique (modélisation, prédiction, contenu de recherche).

### 2. Contrôles qualité découverts sur les données

Deux constats à intégrer au [dictionnaire de données](dictionnaire_donnees.md) :

- **Doublons d'horodatage** : environ 56 lignes en doublon par région, toutes situées à 01:00 UTC le dernier dimanche de mars. C'est un artefact du changement d'heure. Sur l'Occitanie : 233 663 lignes pour 233 635 horodatages uniques. Traitement retenu dans les tests : `drop_duplicates(subset="date_heure", keep="first")`.
- **Colonne `nature`** : deux modalités, `Données définitives` (2 524 608 lignes) et `Données consolidées` (279 360 lignes). La distinction n'était pas documentée.

### 3. Étude de faisabilité : la prévision a-t-elle un sens sur éCO2mix seul ?

Question posée : peut-on construire un volet prédictif crédible **sans source météo externe** ?

**Protocole** : découpage temporel strict, apprentissage sur les années jusqu'à 2023 incluses, test sur 2024 et après. Deux baselines volontairement naïves, car si une baseline naïve capture presque tout, il n'y a pas de projet de modélisation.

**Résultat 1 : forte non-stationnarité.** Production solaire moyenne en Occitanie sur la plage 11h-14h UTC :

| Année | 2013 | 2016 | 2019 | 2022 | 2024 | 2026 |
|---|---|---|---|---|---|---|
| Production (MW) | 359 | 664 | 920 | 1 349 | 1 792 | 2 099 |

Soit un facteur 5,8 en treize ans. Conséquence directe : un modèle climatologique appris sur le passé sous-estime systématiquement le présent. Ce n'est pas du bruit, c'est un biais.

**Résultat 2 : performance des baselines.**

| Région | Cible | Climatologie (mois x moment du jour) | Persistance J-1 |
|---|---|---|---|
| Occitanie | solaire | R2 = 0,425 | R2 = 0,817 |
| Occitanie | demande nette | R2 = 0,391 | R2 = 0,741 |
| Nouvelle-Aquitaine | solaire | R2 = 0,403 | R2 = 0,793 |
| Nouvelle-Aquitaine | demande nette | R2 = 0,140 | R2 = 0,731 |
| Bretagne | solaire | R2 = 0,164 | R2 = 0,775 |
| Bretagne | demande nette | R2 = 0,130 | R2 = 0,430 |

La persistance J-1 bat largement la climatologie, précisément parce qu'elle s'adapte au niveau courant du parc installé.

**Résultat 3 : prévisibilité de l'état nuageux.** Construction d'un indice de ciel clair (production rapportée à une enveloppe glissante, quantile 0,95 sur 30 jours à moment du jour fixé), puis autocorrélation de sa moyenne journalière :

| Décalage | J-1 | J-2 | J-3 | J-7 |
|---|---|---|---|---|
| Corrélation | 0,430 | 0,249 | 0,193 | 0,120 |
| Variance expliquée | 18,5 % | 6,2 % | 3,7 % | 1,4 % |

Écart-type de l'indice journalier : 0,226 pour une moyenne de 0,717.

**Résultat 4 : signature de la thermosensibilité.** Erreur absolue moyenne de la persistance J-1 sur la demande nette en Occitanie, par mois : environ 533 MW en janvier contre 367 MW en juin. Ratio hiver (décembre à février) sur été (juin à août) : **1,36**. Cohérent avec l'effet du chauffage électrique, variable absente du jeu de données.

**Conclusion factuelle** : connaître l'état nuageux d'aujourd'hui n'informe que sur 18,5 % de celui de demain. Or c'est exactement la part de variance qui subsiste une fois retirée la composante déterministe (cycle jour et nuit, saison, capacité installée). Un modèle de prévision entraîné sur éCO2mix seul plafonnerait donc à peine au-dessus de la persistance.

**Conclusion pour le cadrage** : un volet prévision n'est crédible **qu'avec une source météo exogène** (irradiance et température). Sans elle, l'exercice est creux et ne résisterait pas à la première question d'un recruteur du secteur énergie.

### 4. Piste de problématique prédictive, envisagée puis mise de côté

Non retenue pour l'instant, conservée ici pour mémoire.

Fil rouge candidat : *peut-on prévoir la demande nette à J+1 avec des intervalles de prédiction dont la couverture reste valide malgré la croissance rapide du parc solaire ?* L'objet d'étude serait l'incertitude calibrée sous dérive, pas la performance ponctuelle.

Sous-questions envisagées :

1. Quelle part de la variance est prévisible sans météo, et qu'apporte réellement l'ajout de l'irradiance et de la température ? Les baselines sont déjà mesurées (section 3), il manque le terme exogène.
2. Comment la croissance du parc dégrade-t-elle un modèle appris sur le passé, et quelles stratégies la corrigent (normalisation par capacité installée, ré-apprentissage glissant, validation temporelle) ?
3. Les intervalles de prédiction restent-ils calibrés sous dérive ? Comparaison entre prédiction conforme classique (qui suppose l'échangeabilité, hypothèse fausse ici) et inférence conforme adaptative.

Deux pièges méthodologiques identifiés, à trancher si la piste est reprise :

- **Connaissance du futur** : utiliser une réanalyse météo (irradiance réellement observée le jour cible) comme entrée d'une prévision à J+1 revient à connaître les nuages de demain. Une prévision honnête utilise une **archive de prévisions météo**, avec sa propre erreur. Open-Meteo expose ce type d'archive.
- **Agrégation spatiale** : éCO2mix est régional, la météo est ponctuelle. Le mode d'agrégation (points représentatifs, pondération par capacité solaire installée, pondération par population pour la température) est un choix à justifier.

Réserve exprimée : ce volet représente un projet entier à lui seul. Il n'est pas compatible avec le mois d'août si la partie descriptive n'est pas d'abord traitée.

### 5. Décisions actées

- **La partie descriptive reste prioritaire.** Le volet prévision est mis de côté, pas abandonné.
- **Pas de deux branches permanentes** (une descriptive, une prédictive). Une branche Git sert à du travail temporaire destiné à être fusionné. Deux branches qui ne fusionnent jamais rendraient la moitié du travail invisible sur la branche par défaut, et obligeraient à dupliquer toute correction du chargement et du nettoyage. Structure retenue : tout sur `main`, séparation par dossiers et numérotation de scripts. Une branche de travail dédiée reste légitime pendant le développement, à condition qu'elle fusionne.

### 6. État réel du dépôt au 2026-07-25

Quatre commits, dernier `fd6141e`. Fichiers suivis : `README.md`, `docs/dictionnaire_donnees.md`, `notebooks/01_exploration.py`, `src/download.py`, `pyproject.toml`, `uv.lock`, `.gitignore`, `.python-version`, `data/.gitkeep`.

Autrement dit : le pipeline de données, le dictionnaire et le script d'exploration existent. **Aucune sous-question descriptive n'est traitée, aucun graphique n'est produit.**

Prochaine étape prévue : `notebooks/02_visualisation.py`, tracer la demande nette sur une journée type pour observer le creux de mi-journée et la remontée du soir.

### 7. Code non versionné à récupérer

Les tests de faisabilité de la section 3 ont été écrits dans un répertoire temporaire, hors dépôt. Ils ne sont donc pas rejouables en l'état et les chiffres ci-dessus ne sont pas encore vérifiables par exécution. Deux scripts concernés : un pour les baselines (résultat 2), un pour le diagnostic (résultats 1, 3 et 4). À porter dans `notebooks/` sous forme propre si l'on veut conserver ces résultats.

### 8. Points ouverts

- Le dépôt n'a ni `AGENTS.md` ni `CLAUDE.md`. Un assistant qui n'a accès qu'au dépôt distant ne dispose donc d'aucune consigne sur les conventions du projet (langue, typographie, format des scripts, outillage).
- La piste prévision est à reprendre ou à écarter explicitement une fois la partie descriptive avancée.
