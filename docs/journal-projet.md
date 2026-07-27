# Journal du projet

Fichier de suivi des décisions et des constats, tenu par ordre chronologique inverse (le plus récent en haut).

Objectif : garder une trace lisible par toute personne ou assistant qui reprend le projet, y compris sans accès à l'historique des conversations. Chaque entrée précise les faits établis, les décisions actées, et ce qui reste ouvert.

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
