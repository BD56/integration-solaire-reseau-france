# Journal du projet

Fichier de suivi des décisions et des constats, tenu par ordre chronologique inverse (le plus récent en haut).

Objectif : garder une trace lisible par toute personne ou assistant qui reprend le projet, y compris sans accès à l'historique des conversations. Chaque entrée précise les faits établis, les décisions actées, et ce qui reste ouvert.

---

## 2026-07-28 (suite 4) : indice construit, deux tests réussis, un test invalidé et deux diagnostics ratés

Suite du protocole. Code dans `src/analyses.py` (`indice_ciel_clair`, `indice_journalier`, `hauteur_solaire`, `ciel_clair_theorique`) et `notebooks/06_indice_ciel_clair.py`. **Travail en cours, conclusion non atteinte.**

### 1. Construction

Réglages appliqués tels que figés la veille : fenêtre de 30 jours, quantile 0,95, maille créneau horaire × région, exclusion sous 10 MW d'enveloppe.

**1 304 610 créneaux exploitables** sur 2 734 524, soit 47,7 %. **56 808 journées** couvertes. Indice journalier : moyenne 0,616, écart-type 0,265.

⚠️ **Écart non expliqué** avec l'étude de faisabilité du 2026-07-25 : autocorrélation à J-1 de **0,533** ici contre **0,430** alors, et moyenne de 0,616 contre 0,717. Les deux constructions diffèrent sans qu'on sache encore en quoi. À élucider.

### 2. Les trois tests

**Test 2, cohérence spatiale : RÉUSSI, et nettement.** Corrélation entre distance et corrélation des indices : **r = −0,945** sur 66 paires. Hauts-de-France et Île-de-France (134 km) corrèlent à 0,831 ; Bretagne et Provence-Alpes-Côte d'Azur (853 km) à 0,281. L'indice suit donc un phénomène de grande échelle, spatialement cohérent, ce qui est la signature du ciel.

**Test 3, journées extrêmes : RÉUSSI.** Journées les plus sombres entre 0,078 et 0,113, toutes en novembre ou décembre.

**Test 1, neutralité saisonnière : ÉCHOUÉ.** Indice médian de 0,371 en décembre contre 0,795 en juin, soit un écart de **0,424** pour un seuil fixé à 0,15.

### 3. Le test 1 était mal conçu, avec un défaut prouvé et un contesté

**Défaut prouvé, et il n'excuse rien** : l'indice journalier moyenne un **nombre de créneaux qui dépend de la saison**, de **15,6 par jour en janvier à 28,4 en juillet**, soit un rapport de 1,8. Le test comparait donc des grandeurs différentes selon le mois, indépendamment de toute question d'enveloppe. Ce défaut aurait dû être vu à l'écriture du test, pas après.

**Défaut contesté** : la prémisse. Le test attendait un indice sans cycle saisonnier, alors que la nébulosité est elle-même saisonnière et qu'un indice correct devrait donc en montrer un. Cette objection a été formulée **après avoir vu le résultat**, ce qui est exactement la rationalisation que le protocole devait empêcher. Elle reste donc **non tranchée**.

### 4. Deux diagnostics ratés, dont un circulaire

**Premier diagnostic proposé** : vérifier que les meilleures journées de chaque mois atteignent le plafond, l'indice devant alors approcher 1. Résultat obtenu : quantile 99 supérieur à 1 tous les mois, minimum 1,022 en novembre. Conclusion tirée sur le moment : enveloppe saine.

⚠️ **Ce diagnostic était CIRCULAIRE**, et Bryan l'a fait tomber en demandant simplement sur quoi reposait le « plafond ». L'enveloppe étant définie comme le quantile 0,95 d'une fenêtre **contenant la journée évaluée**, environ 5 % des journées la dépassent **par construction**. Le résultat était donc garanti d'avance, quelle que soit la qualité de l'enveloppe. Le test vérifiait une propriété de sa propre définition.

**Conclusions retirées** : « enveloppe saine » et « le cycle saisonnier est météorologique ». Toutes deux reposaient sur ce raisonnement circulaire.

**Restent debout** : le défaut d'agrégation (mesuré indépendamment) et les tests 2 et 3.

### 5. Le test astronomique, valide mais non concluant

Pour sortir de la circularité, il faut confronter l'enveloppe à une référence **extérieure aux données de production**. L'astronomie convient, et n'est pas une source météorologique : la position du soleil se calcule exactement depuis la date, l'heure UTC et la latitude.

Ajout de `hauteur_solaire()` et `ciel_clair_theorique()` (modèle de Haurwitz) dans `src/analyses.py`, avec le calcul mené **en heure UTC**, ce qui écarte d'emblée le piège du changement d'heure.

**Contrôle du calcul** : la hauteur au midi solaire est retrouvée avec un **écart nul aux deux solstices** et de 0,41° à l'équinoxe, pour deux latitudes.

**Résultat.** Le rapport entre l'enveloppe et le ciel clair théorique **n'est pas constant** dans l'année. Normalisé, en 2024 :

| Mois | Nouvelle-Aquitaine | Hauts-de-France | Provence-Alpes-Côte d'Azur |
|---|---|---|---|
| Juin | 0,81 | 0,84 | 0,78 |
| Décembre | **1,69** | **2,22** | **1,49** |

L'enveloppe est donc relativement bien plus haute en hiver que ne le prévoit un modèle **horizontal**.

**Interprétation proposée, non démontrée** : les panneaux sont **inclinés**, en général vers 30° au sud, et captent bien mieux le soleil bas d'hiver qu'une surface plate. Trois indices vont dans ce sens : la variation est lisse et monotone, son signe est celui attendu, et surtout son **amplitude est ordonnée par la latitude** (1,39 pour les Hauts-de-France à 49,9° N, 0,88 pour la Nouvelle-Aquitaine à 45,2° N, 0,74 pour la Provence à 43,9° N). Cet ordre est une signature physique qu'une défaillance aléatoire ne produirait pas.

**Mais rien n'est prouvé** : on a montré que l'enveloppe ne suit pas le ciel clair **horizontal**, pas qu'elle suit le ciel clair **sur plan incliné**, qui est la vraie référence.

### 6. Nouvelle limite constatée

En janvier, l'indice atteint **3,751** au maximum, et son quantile 99 monte à 1,306. Une valeur de 3,75 est absurde. C'est le défaut **inverse** de celui redouté : dans un mois durablement couvert, l'enveloppe se cale sur la moins mauvaise des mauvaises journées, donc trop bas, et une éclaircie exceptionnelle fait exploser le rapport. L'enveloppe est donc **instable en hiver**, ce qui interdit de lire ses valeurs hivernales extrêmes au pied de la lettre.

### 7. Prochaine étape

Recalculer le ciel clair théorique **sur plan incliné à 30°** et refaire la comparaison. Si le rapport devient plat, l'enveloppe est saine et le cycle saisonnier de l'indice est météorologique. S'il reste déformé, l'enveloppe est mauvaise et l'indice inadapté.

C'est le seul test proposé jusqu'ici qui puisse réellement invalider l'indice.

### 8. Enseignement de méthode

Deux tests successifs se sont révélés sans valeur : le test de saisonnalité, dont la prémisse confondait saisonnalité géométrique et météorologique, et le diagnostic d'enveloppe, circulaire par construction. Dans les deux cas la faute est la même : **une mesure improvisée au lieu d'une méthode établie**, déjà constatée avec les fenêtres horaires du basculement.

Le protocole a néanmoins joué son rôle en forçant l'échec à être constaté et consigné plutôt que contourné.

**Deux réflexes à appliquer avant d'écrire une mesure maison.**

*Chercher la méthode établie.* Pour tester une saisonnalité, il existe la **décomposition STL** (tendance, composante saisonnière, résidu), la **force de saisonnalité de Hyndman** (nombre entre 0 et 1, comparable d'une série à l'autre), l'**analyse spectrale** (pic à la fréquence annuelle, sans fenêtre à choisir) et le **test de Kruskal-Wallis** sur les mois (non paramétrique, avec une valeur-p au lieu d'un seuil inventé). Aucune n'avait été envisagée avant d'improviser une comparaison entre deux mois choisis à la main.

⚠️ Réserve sur Kruskal-Wallis dans ce cas précis : avec 56 808 observations et un écart déjà visible à l'œil, la valeur-p serait écrasante et ne ferait que confirmer ce que personne ne conteste. Il ne distingue pas non plus une saisonnalité **légitime** d'un artefact. Sa place utile viendra plus tard, pour comparer la structure saisonnière de l'indice à celle d'une source météo externe.

*Vérifier que le test peut échouer.* Question à se poser systématiquement : **le résultat découle-t-il de la définition des grandeurs comparées ?** Si oui, le test ne prouve rien. Une validation doit confronter à une référence **extérieure** à ce qu'elle valide. C'est cette question, posée par Bryan sous la forme « le plafond, sur quoi tu te bases ? », qui a fait tomber le diagnostic circulaire.

---

## 2026-07-28 (suite 3) : protocole de l'indice de ciel clair, écrit avant construction

Aucun code écrit. Cette entrée fige les choix de construction **et** les critères de validation avant tout calcul, à la demande de Bryan.

### 1. Pourquoi figer avant, et pas après

Regarder la source de validation **pendant** la construction conduirait à ajuster les réglages (longueur de fenêtre, quantile, traitement des nuits) jusqu'à obtenir une bonne corrélation. L'indice se validerait alors trivialement, et la validation ne vaudrait rien.

C'est la discipline déjà appliquée aux prédictions enregistrées avant mesure, étendue cette fois à la **construction de l'outil lui-même**. Chaque réglage est une manette, et chaque manette est une occasion de tricher.

### 2. Ce que l'indice doit mesurer

La **nébulosité**, déduite de la production solaire seule, sans aucune source météorologique.

Principe : la production dépend de la course du soleil (déterministe), de la taille du parc (lente) et de la couverture nuageuse (seule vraiment variable au jour le jour). En estimant ce que le parc produirait par ciel clair, le rapport `production observée / production par ciel clair` isole la nébulosité.

### 3. Choix de construction, figés

| Réglage | Valeur | Justification |
|---|---|---|
| Fenêtre glissante | **30 jours** | assez longue pour contenir quelques journées dégagées, assez courte pour suivre la course saisonnière du soleil |
| Quantile de l'enveloppe | **0,95** | approche le maximum atteignable sans se caler sur une valeur aberrante isolée |
| Maille de calcul | **créneau horaire × région** | la course du soleil et le parc diffèrent selon l'heure et la région |
| Exclusion | créneaux où l'enveloppe est **quasi nulle** | la nuit, le rapport n'a pas de sens et diverge |

Ces valeurs reprennent celles de l'étude de faisabilité du 2026-07-25, qui avait mesuré sur l'indice journalier : moyenne 0,717, écart-type 0,226, autocorrélation à J-1 de 0,430.

Elles sont **figées avant toute vérification** et ne seront pas ajustées au vu des résultats de validation. Si l'indice échoue aux tests, c'est l'indice qui sera déclaré inadapté, pas les réglages qui seront retouchés.

### 4. Trois tests internes, sans aucune donnée externe

Critères écrits avant construction.

**Neutralité saisonnière.** Un indice bien construit ne devrait presque pas avoir de cycle saisonnier, l'enveloppe glissante absorbant déjà la course du soleil.
→ *Échec* si l'indice médian de décembre s'écarte de plus de 0,15 de celui de juin. Ce serait le signe que l'enveloppe manque de journées dégagées en hiver, défaut redouté dès la conception.

**Cohérence spatiale.** Les nuages sont des phénomènes de grande échelle : deux régions voisines devraient avoir des indices journaliers corrélés, deux régions éloignées beaucoup moins.
→ *Échec* si la corrélation entre régions ne décroît pas avec la distance. L'indice mesurerait alors autre chose que le ciel.

**Comportement sur journées identifiables.** Une journée d'été très productive partout devrait donner un indice proche de 1, une journée de tempête un indice très bas.
→ *Échec* si les extrêmes ne se comportent pas ainsi.

Ces trois tests peuvent invalider l'indice à eux seuls, avant toute source externe.

### 5. Validation externe, et le piège de circularité

L'indice sert à **départager des agrégations spatiales de la météo**. Le valider **avec** de la météo, puis choisir l'agrégation **avec** l'indice, serait circulaire.

Séparation retenue :

1. **valider** l'indice contre une météo **grossière** (point unique ou moyenne simple), ce qui suffit à établir qu'il suit la nébulosité, sans dépendre du choix à arbitrer ensuite ;
2. **puis** l'employer pour arbitrer entre agrégations fines.

**Réserve supplémentaire** : il restera à vérifier qu'il **discrimine**. Si toutes les agrégations candidates corrèlent aussi bien avec lui, il ne servira à rien pour les départager.

### 6. Limites connues d'avance

- L'indice capte **tout ce qui réduit la production**, pas seulement les nuages : écrêtement, neige sur les panneaux, pannes, maintenance.
- Il est **circulaire pour l'explication** : dérivé de la production, il ne peut pas servir à l'expliquer. C'est un instrument de validation, jamais une variable explicative.

---

## 2026-07-28 (suite 2) : ressource ou parc ? La prédiction est validée

Étape 1 de la phase 2. Code rejouable dans `notebooks/05_ressource_ou_parc.py`. Période 2020-2025, le taux de charge n'existant pas avant.

### 1. Le résultat

| | Écart entre la région la plus forte et la plus faible |
|---|---|
| Production | facteur **19,2** (de 31 à 586 MW) |
| Parc installé | facteur **15,3** (de 254 à 3 877 MW) |
| Facteur de charge | facteur **1,38** (de 12,0 % à 16,5 %) |

Décomposition logarithmique de l'écart de production : **90 % le parc installé, 10 % la ressource**.

**Prédiction enregistrée la veille** : production autour de 10, facteur de charge autour de 1,5. **Mesuré** : 19,2 et 1,38. L'écart de production était sous-estimé, mais le point central est **validé**.

### 2. Correctif de méthode

La première version décomposait l'écart additivement, `(1,38 − 1) / (19,2 − 1)`, et annonçait 2 % pour la ressource. C'était **faux** : la relation `production = parc × facteur de charge` est multiplicative, la décomposition doit donc passer par les logarithmes, où les facteurs s'additionnent. La bonne valeur est **10 %**, cinq fois plus que l'estimation erronée.

### 3. Les deux classements

| Rang | Par facteur de charge | Par production |
|---|---|---|
| 1 | Provence-Alpes-Côte d'Azur (16,5 %) | Nouvelle-Aquitaine (586 MW) |
| 2 | Occitanie (15,3 %) | Occitanie (476 MW) |
| 3 | Nouvelle-Aquitaine (15,2 %) | Provence-Alpes-Côte d'Azur (318 MW) |
| 4 | Centre-Val de Loire (14,6 %) | Auvergne-Rhône-Alpes (271 MW) |
| 5 | Bourgogne-Franche-Comté (14,5 %) | Grand Est (164 MW) |
| 6 | Auvergne-Rhône-Alpes (14,2 %) | Pays de la Loire (141 MW) |
| 7 | Pays de la Loire (13,8 %) | Centre-Val de Loire (116 MW) |
| 8 | Grand Est (13,7 %) | Bourgogne-Franche-Comté (97 MW) |
| 9 | Bretagne (13,2 %) | Bretagne (60 MW) |
| 10 | Hauts-de-France (13,2 %) | Hauts-de-France (59 MW) |
| 11 | Normandie (12,9 %) | Normandie (37 MW) |
| 12 | Île-de-France (12,0 %) | Île-de-France (31 MW) |

Écarts de rang notables : **Centre-Val de Loire** et **Bourgogne-Franche-Comté** perdent 3 places entre ressource et production (sous-équipées) ; le **Grand Est** en gagne 3 (sur-équipé) ; la **Provence-Alpes-Côte d'Azur**, la mieux ensoleillée du pays, n'est que 3ᵉ en production.

### 4. Retour sur l'erreur du 2026-07-26

Le classement donné alors « par ensoleillement », déduit de la production, était **moins faux que craint mais réel**. Les trois premières places du vrai classement sont bien Provence-Alpes-Côte d'Azur, Occitanie et Nouvelle-Aquitaine, aucun écart de rang ne dépasse 3, et les quatre dernières régions sont identiques dans les deux classements.

Ce qui était faux, c'est l'**ampleur** : parler des « régions les moins ensoleillées » laissait entendre un écart considérable, alors que l'écart réel d'ensoleillement est de **1,38**, contre 19 pour la production.

### 5. Réserves

Le facteur de charge **approche** l'ensoleillement, il ne le mesure pas : écrêtement, orientation et inclinaison des panneaux, technologie et âge du parc (détail dans le [dictionnaire](dictionnaire_donnees.md)). L'écrêtement reste la réserve la plus gênante, son biais jouant dans le sens même qu'on cherche à mesurer.

### 6. Croisement avec une source externe : confirmé

ODRE publie un jeu officiel de facteurs de charge régionaux, `fc-tc-regionaux-annuels-enr` (2014 à 2024, avec la Corse en plus). Comparaison sur 2020-2025 :

| Rang | Région | Officiel | Calculé ici |
|---|---|---|---|
| 1 | Provence-Alpes-Côte d'Azur | **16,08 %** | 16,51 % |
| 2 | Occitanie | 14,56 % | 15,27 % |
| 3 | Nouvelle-Aquitaine | 14,50 % | 15,16 % |
| 4 | Centre-Val de Loire | 13,54 % | 14,64 % |
| 5 | Auvergne-Rhône-Alpes | 13,38 % | 14,21 % |
| 5 | Bourgogne-Franche-Comté | 13,38 % | 14,55 % |
| 7 | Pays de la Loire | 13,02 % | 13,84 % |
| 8 | Grand Est | 12,60 % | 13,74 % |
| 9 | Normandie | 12,16 % | 12,88 % |
| 10 | Bretagne | 12,07 % | 13,24 % |
| 11 | Hauts-de-France | 11,90 % | 13,22 % |
| 12 | Île-de-France | **11,02 %** | 11,99 % |

**Corrélation des valeurs : r = 0,987.** Corrélation des rangs : 0,976. Écart de rang maximal : **2 places**, et seulement entre Normandie, Bretagne et Hauts-de-France, que la source officielle sépare de 0,26 point, soit une quasi-égalité.

**Ce que le croisement confirme :**

- le **classement**, notamment que la Provence-Alpes-Côte d'Azur est la mieux ensoleillée alors qu'elle n'est que 3ᵉ en production ;
- l'**ampleur de l'écart** : rapport max sur min de **1,46** officiellement, contre 1,38 ici. Avec le chiffre officiel, la décomposition devient **88 % le parc, 12 % la ressource**, au lieu de 90 et 10. La conclusion est inchangée ;
- l'**écrêtement**, signalé comme réserve théorique, est un phénomène **documenté** : RTE l'invoque explicitement, aux côtés du mauvais ensoleillement, pour expliquer le facteur de charge historiquement bas de 2024 (13 %, contre 14,5 % en 2023 et en moyenne sur 2014-2023).

**Biais systématique identifié.** Les valeurs calculées ici dépassent l'officiel de 0,6 à 0,8 point, régulièrement. Cause : une différence de définition. Le calcul local fait la **moyenne des taux de charge instantanés**, quand l'indicateur officiel rapporte l'**énergie annuelle à la puissance installée**. Le parc grandissant en cours d'année, la production des premiers mois est divisée par une capacité plus faible, ce qui gonfle la moyenne des ratios. Ce biais n'affecte ni le classement ni les rapports entre régions.

Sources : [ODRE, facteurs de charge régionaux annuels](https://odre.opendatasoft.com/explore/dataset/fc-tc-regionaux-annuels-enr/), [RTE, bilan électrique 2024](https://analysesetdonnees.rte-france.com/bilan-electrique-2024/production).

**Conséquence pour la suite** : ce jeu officiel constitue un **étalon** disponible pour valider d'autres calculs, et il couvre 2014 à 2024, donc au-delà de la limite de 2020 du taux de charge d'éCO2mix.

---

## 2026-07-28 (suite) : plan de la phase 2, et prédiction enregistrée avant mesure

Aucun calcul lancé. Cette entrée fixe le plan et **enregistre une attente avant de la vérifier**, pour qu'elle ne puisse pas être réécrite après coup.

### 1. Ordre des travaux, dicté par la note précédente

Puisqu'une agrégation spatiale **se valide** par sa corrélation avec l'indice de ciel clair, il faut construire l'instrument de mesure avant la chose à mesurer.

| Étape | Dépendance externe |
|---|---|
| **1.** Séparer ressource et parc avec `tch_solaire` | aucune |
| **2.** Construire l'indice de ciel clair dans `src/` | aucune |
| **3.** Récupérer la météo et départager les pondérations candidates | Open-Meteo |
| **4.** Répondre à la phase 2, puis envisager la modélisation | dépend de 3 |

Les étapes 1 et 2 peuvent démarrer immédiatement. L'indice de ciel clair n'existe aujourd'hui que dans les tests non versionnés du 2026-07-25.

### 2. Pourquoi commencer par le TCH

La production en MW mélange **ressource** et **parc installé**. Le TCH divise par le parc, ce qui approche la ressource. C'est le seul indicateur interne au jeu permettant cette séparation, et son emploi répare directement l'erreur du 2026-07-26, où les régions avaient été classées « par ensoleillement » sur la foi de leur production.

Les limites de cet usage (écrêtement, orientation, technologie, absence avant 2020, formule non vérifiable) sont détaillées dans le [dictionnaire](dictionnaire_donnees.md).

L'**écrêtement** est la plus gênante : il abaisse le TCH sans baisse d'ensoleillement, et frappe d'abord les régions les plus solaires. Le biais joue donc dans le sens même qu'on cherche à mesurer.

### 3. Prédiction enregistrée avant mesure

> **Le parc installé expliquera l'essentiel des écarts régionaux, la ressource assez peu.** Attendu : des productions variant d'un facteur proche de 10 entre régions, pour un taux de charge ne variant que d'un facteur 1,5 environ.

Cette attente est consignée **avant** tout calcul. Si la mesure la contredit, c'est la prédiction qui a tort, et elle restera écrite ici.

---

## 2026-07-28 : note de réflexion sur l'agrégation spatiale de la météo (phase 2)

Note rédigée par Bryan, consignée avant tout début de travaux. Elle répond à l'objection soulevée en préparant la phase 2 : *peut-on résumer l'ensoleillement d'une région entière par un seul chiffre ?*

### 1. Le moyennage spatial n'est pas un défaut à subir

La production solaire régionale est **déjà une somme sur des milliers d'installations dispersées**. Une irradiance moyennée reproduit donc la physique du système mieux qu'une mesure ponctuelle, même parfaite. L'objet à expliquer étant lui-même un agrégat, l'explicative doit l'être aussi.

### 2. La vraie question est la pondération, et elle diffère selon la variable

Il ne s'agit pas de choisir *où* moyenner mais *avec quel poids* :

| Variable | Pondération | Motif |
|---|---|---|
| Irradiance | **puissance solaire installée** | c'est là que le soleil produit |
| Température | **population** | le sujet est le chauffage |

**Ce ne sont pas les mêmes cartes.** Utiliser la même pondération pour les deux serait une erreur.

### 3. L'agrégation est validable, pas à postuler

L'**indice de ciel clair** dérivé de la production elle-même (production rapportée à son enveloppe récente) est un indicateur de nébulosité **indépendant de toute source météo**. Une agrégation candidate se juge donc à sa corrélation avec cet indice, au lieu d'être supposée bonne.

Cet indice avait déjà été construit lors de l'étude de faisabilité du 2026-07-25 : autocorrélation journalière de 0,430 à J-1, écart-type de 0,226 pour une moyenne de 0,717.

### 4. L'exigence dépend de l'usage

Un résumé grossier suffit pour **expliquer les contrastes régionaux** : l'écart entre l'Occitanie et les Hauts-de-France écrase largement l'erreur d'agrégation. Il en faudrait un beaucoup plus fin s'il s'agissait un jour de **prévoir**.

### 5. À vérifier avant de s'engager

La pondération par capacité suppose de connaître la puissance installée à une **maille plus fine que la région**. Or les colonnes `tch_` ne donnent que le total régional.

*Complément factuel sur l'état du dépôt* : la fonction `capacite_installee()` de `src/analyses.py` déduit bien une puissance installée en inversant le taux de charge, mais **à la maille régionale uniquement**, et seulement à partir de 2020. Elle ne lève donc pas cette réserve. Une source externe serait nécessaire, par exemple le registre des installations de production d'ODRE.

---

## 2026-07-27 (suite 2) : sous-question 3, l'équilibrage

Reprise à zéro après un premier essai infructueux. Code rejouable dans `notebooks/04_equilibrage.py`.

### 1. Changement de méthode, et pourquoi

Un premier essai reposait sur des régressions des variations de chaque levier sur celles du solaire. Il a été **abandonné** après contrôle, pour trois défauts cumulés :

- **relation faible** : r² de 0,08 entre variation du solaire et variation de consommation ;
- **relation non linéaire** : la pente locale de l'hydraulique varie de −0,96 à +1,95 selon l'ampleur de la variation, et la tranche des petites variations, qui contient la majorité des observations, se comporte à l'inverse des autres ;
- **relation instable selon l'heure** : la pente passe de 0,03 à 11 h (r² = 0,001, soit rien) à 1,44 à 21 h.

Un coefficient unique par levier ne pouvait donc rien résumer honnêtement.

Une erreur de méthode est également reconnue : le « contrôle par l'identité comptable » avait été présenté comme une validation de la méthode. Or, l'identité étant vraie dans les données et la régression linéaire, **ce test ne pouvait pas échouer** sauf erreur de code. Il validait l'absence de bogue, rien de plus.

Erreur de conduite reconnue aussi : chaque étape intermédiaire avait été présentée comme un résultat, puis corrigée au contrôle suivant, trois fois de suite. Bryan a interrompu, à juste titre.

**Protocole retenu à sa demande** : idées → hypothèses → tests → verdict. Avec deux garde-fous : le **critère de validation est écrit avant tout calcul**, et les **hypothèses rejetées restent consignées**, faute de quoi « changer d'idée » revient à ne garder que ce qui arrange.

Critère commun fixé à l'avance : validée si |r| > 0,7 dans le sens prédit, rejetée si |r| < 0,3 ou sens contraire, indécise entre les deux. Ce seuil est plus exigeant que la significativité statistique, qui se situe vers r = 0,55 pour 13 points.

Les tests ne comportent **aucune régression** : uniquement des profils horaires et des maxima, qui ne supposent aucune forme de relation. Ils portent tous sur la France entière, l'échelle régionale ayant été écartée (voir plus bas).

### 2. Pourquoi le niveau national

Vérifié sur les 12 régions : `ech_physiques` **domine dans 8 régions sur 12**, jusqu'à 94 % pour les Pays de la Loire, et **quatre régions présentent un coefficient positif** (Auvergne-Rhône-Alpes +1,27, Normandie +1,20, Grand Est +0,82, Île-de-France +0,32), ce qui n'a aucun sens comme mécanisme d'équilibrage.

Explication : une région n'a **aucune obligation de s'équilibrer**, elle évacue son solde chez la voisine. En additionnant les 12 régions, les flux interrégionaux s'annulent deux à deux et il ne reste que le solde avec l'étranger. Les mégawatts s'additionnant, l'agrégation est légitime.

### 3. Les quatre verdicts

| Hypothèse | r | r² | Verdict |
|---|---|---|---|
| **H1** le pompage se déplace vers la mi-journée | **+0,90** | 0,82 | **VALIDÉE** |
| **H3** le nucléaire module | **−0,86** | 0,75 | **VALIDÉE** |
| H4 la remontée du soir s'accélère | −0,45 | 0,21 | REJETÉE |
| H2 les échanges évacuent le surplus de midi | −0,08 | 0,01 | REJETÉE |

**H1, le résultat le plus net.** Le pompage de mi-journée passe de 288 MW en 2013 à **1 608 MW en 2025**, soit ×5,6, pendant que le pompage nocturne recule de 2 305 à 1 450 MW. Surtout, l'**heure du maximum de pompage**, figée à 4 h 30 pendant douze années consécutives, **bascule à 15 h en 2025**. On stockait la nuit avec le surplus nucléaire, on stocke désormais à midi avec le surplus solaire.

**H3, contre l'attente.** Le rapport entre production nucléaire de mi-journée et de nuit passe de 1,037 en 2013 à **0,956 en 2025**, franchissant 1 en 2024 : le nucléaire produit désormais **moins à midi que la nuit**. C'était l'hypothèse annoncée comme la moins probable. L'affirmation antérieure « le nucléaire ne varie pas, ce n'est pas un objet d'étude dynamique » reste vraie en **amplitude**, mais il ne tourne plus en base pure.

**H4 rejetée, avec une précision indispensable.** La rampe de soirée passe de 2 943 MW par demi-heure en 2013 à 2 734 en 2025 : sens contraire à la prédiction. Cela ne contredit **pas** le résultat de la sous-question 2 (remontée du soir multipliée par 6,8 en Nouvelle-Aquitaine), car ce ne sont pas les mêmes grandeurs : une **amplitude** en MW là-bas, une **vitesse** en MW par demi-heure ici. Le système doit remonter plus **haut**, pas plus **vite**.

**H2 rejetée.** Aucune tendance du solde de mi-journée. 2022 sort du lot en positif, la France ayant importé pendant la crise du parc nucléaire, ce qui recoupe la rupture déjà consignée.

### 4. Réserve sur l'interprétation de r

Ces corrélations sont calculées **contre l'année**, sur 13 points. Elles mesurent la **régularité d'une évolution**, pas une force causale. « r² = 0,82 pour H1 » ne signifie pas que le solaire explique 82 % du pompage, mais que la part de mi-journée croît très régulièrement. Le lien avec le solaire vient du raisonnement et du calendrier, pas de ce chiffre.

### 5. Réponse à la sous-question 3

Le système absorbe le surplus solaire de mi-journée par **deux leviers** : le **stockage par pompage**, qui a changé d'horaire, et la **modulation du nucléaire**, qui a cessé de tourner en base pure. Ni les échanges avec l'étranger, ni une accélération des rampes de soirée ne jouent de rôle détectable.

### 6. Points ouverts

- La restitution du stockage reste invisible : la colonne `pompage` n'enregistre que le remplissage, le turbinage étant fondu dans `hydraulique`.
- L'approche par **journées jumelles** (deux jours semblables sauf l'ensoleillement) n'a pas été menée. Elle resterait la plus proche d'une expérience et permettrait de quantifier les contributions sans supposer de forme.
- Les pages « Qualité des données » et « Équilibrage » du tableau de bord restent à construire.

---

## 2026-07-27 (suite) : le basculement de l'ordre de la journée, vérifié

Le résultat pressenti la veille est soumis à quatre contrôles. Il tient, mais la **mesure initiale a dû être remplacée**. Code rejouable dans `notebooks/03_verification_basculement.py`.

### 1. Le résultat, formulé prudemment

Dans les régions très solaires, le moment où le réseau travaille le moins n'est plus la nuit mais le **milieu de journée**. Heure du minimum de la demande nette médiane en Nouvelle-Aquitaine :

| 2013 | 2016 | 2018 | **2019** | 2022 | 2025 |
|---|---|---|---|---|---|
| 4 h | 4 h | 4 h | **16 h** | 16 h | 15 h |

### 2. Les quatre contrôles

**Témoin, le plus décisif.** La consommation seule ne bascule dans **aucune des 12 régions**. Le phénomène n'apparaît qu'après soustraction du solaire : il ne peut donc pas venir d'un changement d'habitudes de consommation.

**Éolien.** Les deux définitions de demande nette donnent le même verdict pour **10 régions sur 12**. L'éolien n'explique pas le phénomène.

**Ordre.** Les régions basculent dans l'ordre de leur équipement, sans chevauchement :

| | Couverture solaire |
|---|---|
| 6 régions qui basculent | de **6,3 %** à 15,4 % |
| 6 régions qui ne basculent pas | de 0,6 % à **5,1 %** |

Corrélation entre l'année de bascule et la couverture : **r = −0,86**, contre −0,76 avec la production absolue. **La couverture prédit mieux que la production** : l'Auvergne-Rhône-Alpes produit 356 MW, le troisième volume du pays, et ne bascule jamais, car sa consommation (7 107 MW de moyenne) est trop élevée pour que ce solaire pèse. C'est la **part**, pas le volume.

**Robustesse, qui a invalidé la mesure initiale.** La première mesure comparait un creux (10 h-16 h) à un niveau de nuit (2 h-5 h), deux fenêtres choisies à la main. Testée sur 16 combinaisons, elle donnait **quatre années différentes** : 2015, 2016, 2019 ou 2021. Le résultat dépendait donc en partie d'un choix arbitraire.

**Mesure retenue à la place, sans aucun paramètre** : l'heure à laquelle se situe le minimum du profil journalier. On ne choisit plus de fenêtre, on constate où est le point le plus bas. L'année 2019 survit à ce changement pour la Nouvelle-Aquitaine ; l'Occitanie passe en revanche de 2019 à 2021, l'ancienne mesure étant trop empressée.

### 3. Stabilité, à ne pas passer sous silence

| Région | Bascule | Verdict |
|---|---|---|
| Nouvelle-Aquitaine | 2019 | **durable** |
| Occitanie | 2021 | **durable** |
| Pays de la Loire | 2025 | durable (une seule année observée) |
| Bourgogne-Franche-Comté | 2025 | durable (une seule année observée) |
| Provence-Alpes-Côte d'Azur | 2023 | **instable**, retour en 2024 |
| Centre-Val de Loire | 2021 | **instable**, retour en 2022 |

**Formulation à retenir** : établi pour deux régions, émergent pour quatre autres, absent pour six. Ne **pas** écrire que « la France a basculé en 2019 ».

### 4. Ce que ça apporte au projet

C'est le premier résultat substantiel, et il répond directement à la problématique : le solaire ne se contente pas d'ajouter de l'électricité, il **change la forme de la journée**. Un réseau conçu pour un creux nocturne doit désormais gérer un creux de mi-journée suivi d'une remontée brutale. Il donne aussi un seuil indicatif : la bascule survient autour de **5 à 6 % de couverture solaire**.

### 5. Enseignement de méthode

Une mesure dépendant de bornes choisies à la main doit être testée sur plusieurs jeux de bornes **avant** d'être publiée. Ici, quatre années différentes selon les fenêtres : sans ce contrôle, le projet aurait annoncé une date en partie arbitraire. Quand une mesure sans paramètre existe, elle est préférable.

---

## 2026-07-27 : tableau de bord Streamlit, et bascule vers la visualisation

Changement de méthode acté, puis construction d'un tableau de bord interactif.

### 1. Pourquoi passer à la visualisation

Bryan a contesté, à juste titre, la proposition de clore les sous-questions par des figures statiques. Argument retenu : **l'exploration menée jusqu'ici était presque entièrement numérique** (comptages, médianes, tableaux) pour trois figures seulement. Or des statistiques résumées cachent ce qu'un graphique montre immédiatement. « Se perdre » dans la visualisation est une méthode d'exploration légitime, pas une perte de temps.

Distinction conservée : le **brouillon** (`notebooks/03_brouillon_visuel.py`, figures rapides et peu commentées, jetables) et la **figure finale** (soignée, autoportante). Le premier alimente la seconde.

### 2. Décisions d'architecture

| Décision | Motif |
|---|---|
| **Streamlit** plutôt que Dash ou un rapport statique | Le moins de code pour un résultat propre, et les menus sont l'intérêt principal |
| **Plotly** dès le départ | Le survol des cases apporte réellement quelque chose sur une carte de chaleur |
| **Outil de travail ET pièce de portfolio** | Choix de Bryan, qui veut des outils complets et agréables |
| **Local pour l'instant**, version en ligne plus tard | Une version déployée exigerait un extrait allégé versionné, les données pesant 86 Mo |
| Calculs dans `src/`, affichage dans `app/` | Évite que les scripts et le tableau de bord divergent |

Découpage : `src/analyses.py` (calculs, renvoie des tableaux), `src/graphiques.py` (figures Plotly), `app/tableau_bord.py` (mise en page seule). Configuration versionnée dans `.streamlit/config.toml` : télémétrie coupée, thème accordé aux figures.

### 3. Mesure : la charge du navigateur n'est pas un problème

Inquiétude exprimée puis **mesurée**, au lieu d'être supposée :

| | Serveur | Poids envoyé |
|---|---|---|
| Une carte Plotly (233 664 cases) | 0,11 s | 2,7 Mo |
| Deux cartes côte à côte | 0,17 s | 5,4 Mo |
| La même en image matplotlib | 0,05 s | 0,12 Mo |

Plotly est 22 fois plus lourd, mais 5,4 Mo en local est négligeable. Aucune raison de renoncer à l'interaction ni de basculer sur une application de bureau. Réserve : le **temps de dessin dans le navigateur** n'a pas pu être mesuré depuis le serveur.

### 4. Décisions de lecture prises en construisant

- **Échelle de couleur calée sur le 99e centile**, pas sur le maximum. Le Grand Est paraissait pâle alors qu'aucune valeur n'était aberrante : ses journées record (30 juin 2025, jusqu'à 3 824 MW et **53 % de couverture**) écrasaient l'échelle. Le plafond passe ainsi de 3 824 à 1 156 MW.
- **Trois modes d'échelle** en comparaison : commune, propre à chacune, normalisée. Le mode normalisé s'appelle « 99e centile = 1 » et non « de 0 à 1 », car environ 1 % des valeurs dépassent 1. Défaut relevé par Bryan sur une infobulle affichant 1,14.
- **Quantifier plutôt que corriger** les valeurs négatives d'avant 2020. Poids mesuré en Nouvelle-Aquitaine : **0,021 %** du niveau de consommation. Harmoniser aurait détruit l'information d'autoconsommation pour un effet deux mille fois inférieur au signal.
- **Écarter les années incomplètes**, détecté automatiquement (moins de 350 jours) plutôt que codé en dur. 2026 ne couvre que **120 jours**, uniquement des mois froids : incluse, elle simulait une hausse brutale de consommation qui n'est qu'un effet de calendrier.

### 5. Quatre défauts trouvés en auditant avant de committer

Audit demandé par Bryan avant tout envoi. Le premier était grave.

| Défaut | Constat | Correction |
|---|---|---|
| **Agrégation nationale de taux** | « France entière » **additionnait** `tco_solaire` sur 12 régions : médiane affichée **33,3 %** contre **2,6 %** en réalité, maximum **620 %** au lieu de 47 %, et jusqu'à **1 100 %** pour `tch_solaire` | `agreger_national` recalcule les taux à partir des sommes, et **lève une erreur** pour `tch_solaire`, dont la référence (puissance installée) n'est pas une colonne. L'option est retirée de l'interface |
| **Saisons déséquilibrées** | L'onglet « Par saison » incluait 2026 tronquée : 330 jours d'hiver et 337 de printemps contre 276 d'été | Années incomplètes retirées du curseur. Les quatre saisons pèsent désormais 271 à 276 jours |
| **Ponctuation détruite** | Un `.replace(",", " ")` destiné aux milliers était appliqué à la phrase entière : « Avant 2020  RTE reportait  d'où… » | Fonction `nombre()` appliquée au seul nombre, avec virgule décimale française |
| **Avertissement trop large** | Un message signalait la rupture de 2021 sur des variables qu'elle ne concerne pas | Message conditionnel à la variable et à la région, et chiffré |

Enseignement de méthode : **un code HTTP 200 ne prouve rien** pour une application Streamlit, qui répond 200 en affichant une trace d'erreur dans la page. La vérification porte désormais sur la chaîne d'imports et l'exécution réelle.

Piège rencontré : Streamlit recharge le fichier de page mais **pas toujours les modules importés**. Après modification de `src/`, il faut arrêter et relancer l'application.

### 6. État

Trois pages : **Cartes de chaleur** (opérationnelle, comparaison à deux régions, trois modes d'échelle, sept variables), **Profils journaliers** (opérationnelle, onglets par saison et par année), **Qualité des données** (coquille vide).

Résultat marquant obtenu au passage, sur la demande nette médiane en Nouvelle-Aquitaine : le creux de mi-journée passe de 4 440 MW en 2013 à **1 791 MW** en 2025, et la remontée du soir est multipliée par **6,8** (328 vers 2 237 MW). Surtout, l'écart entre le niveau de nuit et le creux de midi **change de signe en 2019** : la mi-journée devient le moment où le réseau travaille le moins, alors que c'était l'inverse jusque-là. À confirmer et à interpréter avec Bryan.

### 7. Points ouverts

- Page « Qualité des données » à construire, et page « Équilibrage » (sous-question 3) à créer.
- ~~`notebooks/02_profils_saisonniers.py` et `03_brouillon_visuel.py` font double emploi avec le tableau de bord.~~ **Réglé** : `03_brouillon_visuel.py` supprimé, son rôle étant repris par le tableau de bord ; `02_profils_saisonniers.py` réécrit pour appeler `src/analyses.py` et ne plus rien calculer lui-même. Répartition des rôles actée : le **tableau de bord** sert à explorer, ce **script** fige quelques figures de vitrine visibles directement sur GitHub, sans quoi le dépôt ne montrerait aucun graphique à qui ne lance pas l'application.
- Trois figures proposées et non faites : profondeur du creux en courbe, distribution horaire de la demande nette, normalisation par jour.
- Le temps de dessin côté navigateur reste non mesuré.

---

## 2026-07-26 (suite 3) : recensement des ruptures temporelles

Détection systématique menée **avant** toute recherche de cause, pour ne pas ne trouver que ce qu'on cherchait. Referme la phase exploratoire.

### 1. Méthode

Quatre balayages sur 2013-2025 (2026 écarté, incomplet) :

- **structure** : taux de remplissage de chaque colonne par année, pour repérer ce qui apparaît ou disparaît ;
- **niveau** : moyenne annuelle par filière, en signalant les variations dépassant trois fois la variation habituelle de la variable, afin de ne pas confondre une croissance régulière avec un saut ;
- **comportement** : part de valeurs négatives par année ;
- **transitoire** : écart de chaque mois au même mois des autres années, en écarts-types.

### 2. Le résultat le plus important : une des deux chutes du nucléaire n'existe pas

| Année | Moyenne sur les 12 régions | Moyenne sur les 7 régions nucléaires |
|---|---|---|
| 2020 | −11,8 % | −11,8 % |
| **2021** | **−37,1 %** | **+7,9 %** |
| **2022** | **−22,7 %** | **−22,7 %** |

En 2021, les 5 régions sans centrale passent de « case vide » à « zéro ». Elles entrent donc dans la moyenne et la tirent mécaniquement vers le bas. Restreinte aux régions qui ont réellement du nucléaire, 2021 est **en hausse de 7,9 %**. En 2022 les deux mesures coïncident : la chute est **réelle**.

Une même détection, deux natures opposées. Sans ce contrôle, on aurait décrit une crise du nucléaire débutant en 2021.

### 3. Trois seuils structurels, pas un seul

Taux de remplissage par année (%) :

| Année | `pompage` | `nucleaire` | `tch_solaire` | `eolien_terrestre` | `stockage_batterie` |
|---|---|---|---|---|---|
| 2013-2014 | 50 | 58 | 0 | 0 | 0 |
| 2015-2019 | **58** | 58 | 0 | 0 | 0 |
| 2020 | 58 | 58 | **100** | 0 | 0 |
| 2021-2025 | **100** | **100** | 100 | **100** | **100** |

Les seuils sont **2015**, **2020** et **2021**. L'entrée précédente ne parlait que de 2020, c'était incomplet. Les passages à 100 % de 2021 ne sont pas de nouvelles données mais un changement de convention : le vide devient zéro.

### 4. Recensement complet et classement

Deux critères : un **artefact** (la donnée décrit un changement qui n'a pas eu lieu) est plus dangereux qu'un **événement réel** ; un effet **permanent** est plus dangereux qu'un effet **passager**.

| Rupture | Année | Nature | Niveau | Touche le sujet ? |
|---|---|---|---|---|
| Fin des valeurs négatives, apparition des `tco_`/`tch_` | 2020 | artefact permanent | **1** | **Oui**, le solaire |
| Vide devenu zéro (`nucleaire`, `pompage`, `eolien_terrestre`, batteries) | 2021 | artefact permanent | **1** | Indirectement : fausse toute moyenne « toutes régions » |
| Solaire négatif en Nouvelle-Aquitaine | 2015-2019 | artefact | 2 | **Oui**, le solaire |
| Pompage renseigné en Hauts-de-France | 2015 | artefact | 2 | Oui, pour l'équilibrage |
| Crise du parc nucléaire | 2022 | réel durable | 2 | Non directement |
| Confinement | mars à juin 2020 | réel passager | 3 | **Oui**, la consommation |
| Croissance des bioénergies | 2014 | réel | 3 | Non |
| Vague de froid | janvier 2017 | réel passager | 3 | Oui, la consommation |
| Réforme des régions | 2016 | **inexistante** | | Non |

Précisions sur trois lignes :

- **Bioénergies 2014** (+22,8 %) : la hausse touche **les 12 régions sans exception**, ce qui plaide pour une croissance réelle du parc plutôt qu'un changement de périmètre local.
- **Confinement** : l'anomalie dure environ trois mois puis s'efface. Écarts-types de la consommation en 2020 : mars −0,77, **avril −2,34**, mai −1,65, juin −1,53, juillet −0,79, août −0,23. Profil cohérent avec la période du 17 mars au 11 mai 2020.
- **Janvier 2017** (+2,1 écarts-types) : cause **non vérifiée**. Une vague de froid est l'explication attendue, elle n'a pas été établie sur les données.

### 5. Un résultat négatif utile

**Aucune rupture en 2016**, et le jeu compte **12 régions sur toute la période**. La réforme des régions ne laisse aucune trace : RTE a reconstruit l'historique sur le découpage actuel. Le soupçon exprimé dans l'entrée précédente était infondé.

### 6. Trois règles qui en découlent pour la suite

1. **Ne jamais moyenner sur les 12 régions sans vérifier le taux de remplissage** de la variable sur la période considérée. C'est exactement le piège de 2021.
2. **Traiter 2020 comme une frontière** pour toute série solaire longue, à cause du changement de convention.
3. **Nommer explicitement le confinement** plutôt que de le laisser peser sur une tendance de consommation.

### 7. Points ouverts

- Le pompage des Hauts-de-France à partir de 2015 : vraies valeurs ou zéros déclarés ? Non vérifié.
- La cause de janvier 2017 : non établie.

---

## 2026-07-26 (suite 2) : lignes `-` de l'éolien tranchées, valeurs négatives expliquées

Referme deux points de la phase exploratoire, et en ouvre un nouveau : une rupture de méthode en 2020.

### 1. Les 96 lignes `-` sont deux pannes de mesure, pas une absence de parc

Elles ne sont pas éparpillées : ce sont **deux blocs contigus de 48 créneaux**, soit une journée complète chacun.

| Région | Lignes | Dates |
|---|---|---|
| Centre-Val de Loire | 48 | 27 et 28 décembre 2013 |
| Île-de-France | 48 | 8 et 9 mai 2013 |

Les valeurs encadrant le trou tranchent la question :

| Région | 6 valeurs avant | 6 valeurs après |
|---|---|---|
| Centre-Val de Loire | 446, 474, 491, 535, 555, **557** | **620**, 628, 612, 624, 621, 584 |
| Île-de-France | 0, 0, 0, 1, 1, 4 | 3, 7, 4, 4, 5, 1 |

Le Centre-Val de Loire produisait 550 MW juste avant et 620 MW juste après : le parc tournait à plein régime.

**Décision** : la valeur manquante est le traitement correct, le code actuel est donc juste et ne change pas. **Ne jamais remplacer par zéro** : cela fabriquerait un effondrement de production de 24 heures suivi d'un retour instantané. Pour l'Île-de-France l'enjeu est nul, elle produisait 4 MW en moyenne en 2013.

Poids : 96 lignes sur 2,8 millions, soit **0,0034 %**. À documenter, pas à corriger.

### 1 bis. Valeurs négatives de production : physiques, mais rupture de méthode en 2020

| Filière | Lignes < 0 | % | Minimum | Médiane des négatifs |
|---|---|---|---|---|
| `thermique` | 78 327 | 2,79 % | −83 | −3 |
| `solaire` | 33 429 | 1,19 % | −23 | −1 |
| `nucleaire` | 444 | 0,02 % | −144 | −87 |
| `eolien` | 619 | 0,02 % | −6 | −1 |
| `hydraulique` | 8 | 0,00 % | −6 | −1 |
| `bioenergies` | 0 | 0 % | | jamais négative |

**Ce ne sont pas des erreurs** : ce sont les installations qui consomment au lieu de produire (auxiliaires d'une centrale à l'arrêt, onduleurs des panneaux la nuit). Deux indices le confirment, **sur le moment où elles surviennent** :

- le solaire n'est **jamais** négatif entre 10 h et 14 h. Répartition horaire locale : 16 812 lignes entre 0 h et 6 h, 5 254 entre 6 h et 10 h, **0** entre 10 h et 14 h, 123 entre 14 h et 18 h, 11 240 entre 18 h et 24 h ;
- la médiane du nucléaire négatif, −87 MW, correspond à l'ordre de grandeur des auxiliaires d'un réacteur à l'arrêt.

Les amplitudes sont faibles face aux niveaux habituels : −144 MW contre 6 075 MW de production moyenne pour le nucléaire, −23 contre 269 pour le solaire.

**Décision** : ne pas les corriger. Elles ont un sens physique, leur poids est négligeable, et pour la demande nette un solaire négatif l'augmente légèrement, ce qui est correct.

⚠️ **Constat le plus important : aucune valeur négative n'apparaît après 2019**, toutes filières confondues. C'est **la même année** où RTE commence à publier les `tco_` et `tch_`. Tout indique un **changement de convention** côté RTE, qui aurait cessé de reporter la consommation propre des installations.

**Conséquence pour la sous-question 2** : elle compare 2013 à 2026, donc de part et d'autre de cette rupture. Une évolution observée sur toute la période peut refléter un changement comptable plutôt qu'un phénomène réel. À traiter explicitement, par exemple en vérifiant que les conclusions tiennent sur la seule période 2020-2026.

#### Correction : le solaire négatif est une pratique de déclaration, pas un phénomène régional

La concentration régionale a été creusée après coup, et **elle nuance la lecture ci-dessus**. Le phénomène est physiquement réel partout, mais il n'est **déclaré** que par certaines régions et à certaines époques.

Solaire négatif avant 2020, par région :

| Région | Lignes < 0 | % de ses lignes | Solaire moyen |
|---|---|---|---|
| Nouvelle-Aquitaine | 33 379 | **27,2 %** | 243 MW |
| Provence-Alpes-Côte d'Azur | 32 | 0,03 % | 154 MW |
| Grand Est | 9 | 0,01 % | 70 MW |
| Occitanie | **9** | 0,01 % | **206 MW** |
| Les huit autres | 0 | 0 % | |

L'Occitanie a un parc **comparable** à la Nouvelle-Aquitaine et 3 700 fois moins de valeurs négatives. Ce n'est donc pas une question de taille de parc : les panneaux d'Occitanie consomment aussi la nuit, mais leur production n'est jamais reportée en négatif. Chronologie en Nouvelle-Aquitaine : rien en 2014, 2 433 lignes en 2015, environ 8 400 par an de 2016 à 2018, 5 719 en 2019, puis zéro à partir de 2020.

**Formulation correcte** : phénomène physique réel, mais **enregistré de façon incohérente selon les régions et les époques**. Ma première rédaction, qui le présentait comme purement physique, était juste sur le moment (jamais à midi) et fausse sur la répartition.

**Conséquences** : ne jamais comparer les régions sur cette base, et se méfier de la série solaire de la Nouvelle-Aquitaine avant 2020 pour la sous-question 2. Les profils saisonniers actuels ne sont pas touchés, ils portent sur 2023-2025.

Le **thermique** négatif suit une logique différente, mieux expliquée par la taille du parc :

| Région | Lignes < 0 | Thermique moyen |
|---|---|---|
| Île-de-France | 39 518 | 272 MW |
| Occitanie | 31 455 | **32 MW** |
| Pays de la Loire | 7 336 | **532 MW** |

L'Occitanie, avec un parc minuscule, passe souvent au négatif parce que ses auxiliaires dominent. Les Pays de la Loire, avec le plus gros parc, sont rarement négatifs parce que leurs centrales tournent.

### 2. Panorama de l'éolien par région (production moyenne, MW)

| Région | 2013 | 2020 | 2025 |
|---|---|---|---|
| Hauts-de-France | 371 | 1 322 | **1 429** |
| Grand Est | 420 | 1 000 | 1 066 |
| Pays de la Loire | 112 | 273 | 556 |
| Bretagne | 160 | 256 | 484 |
| Nouvelle-Aquitaine | 81 | 274 | 469 |
| Normandie | 110 | 233 | 430 |
| Occitanie | 250 | 415 | **382** |
| Centre-Val de Loire | 173 | 355 | 372 |
| Bourgogne-Franche-Comté | 32 | 221 | 252 |
| Auvergne-Rhône-Alpes | 84 | 131 | 160 |
| Île-de-France | 4 | 30 | 35 |
| Provence-Alpes-Côte d'Azur | 13 | 11 | 29 |

Deux constats utiles à la suite du projet :

- **La géographie de l'éolien est l'inverse de celle du solaire.** Les Hauts-de-France dominent l'éolien (1 429 MW) alors qu'ils sont parmi les derniers au solaire (1,8 % de couverture). Cela confirme directement l'explication des bandes très larges observées dans leurs profils saisonniers : c'est le vent, pas le soleil. La décision de calculer `demande_nette_solaire` séparément est donc justifiée par les données, et non seulement par principe.
- **L'Occitanie recule** (415 MW en 2020 contre 382 en 2025), seule région dans ce cas. À vérifier avant d'en conclure quoi que ce soit : il peut s'agir d'une année 2020 particulièrement ventée plutôt que d'une baisse réelle du parc. **Point ouvert.**

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

- ~~Nature des 96 lignes `-` de l'éolien : non mesuré ou parc absent (section 2).~~ **Tranché**, voir l'entrée « suite 2 » : deux pannes de mesure, la valeur manquante est correcte.
- Sous-question 1 à clore réellement : étendre au-delà de 2 régions et de 2023-2025, exploiter `demande_nette_solaire`, régénérer les figures après correction du nettoyage, et faire valider les résultats par Bryan.
- Sous-questions 2 (évolution pluriannuelle) et 3 (équilibrage) non commencées.
- Le code de faisabilité de l'entrée précédente n'est toujours pas porté dans le dépôt.
- Puissance installée avant 2020 : nécessiterait une source externe (registre des installations d'ODRE) plutôt qu'une extrapolation à rebours sur sept ans.

---

## 2026-07-26 : premiers profils saisonniers de demande nette (sous-question 1 NON close)

> ⚠️ **Correction apportée le jour même.** Cette entrée était initialement intitulée
> « sous-question 1 traitée ». C'était faux, et le titre a été rectifié. Ce qui est
> produit ici ne clôt pas la sous-question 1 : les profils ne portent que sur **2 régions
> sur 12** et sur **2023-2025**, n'utilisent qu'une des deux définitions de la demande
> nette (`demande_nette_solaire` n'existait pas encore), et ont été calculés **avant** la
> correction du nettoyage des changements d'heure. Ils n'ont pas non plus été validés par
> Bryan. Voir l'entrée suivante, section 6.

Premiers résultats descriptifs. Le dépôt passe de « aucun graphique produit » à trois figures et un module de préparation partagé.

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
