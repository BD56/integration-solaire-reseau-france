# 📖 Dictionnaire des données : éCO2mix régional

Référence des variables du jeu de données `eco2mix-regional-cons-def`.

- **Source** : [Open Data Réseaux Énergies (ODRE)](https://odre.opendatasoft.com/explore/dataset/eco2mix-regional-cons-def/information/), données issues de l'application **éCO2mix** de **RTE**.
- **Licence** : Licence Ouverte / Etalab.
- **Couverture** : du 2012-12-31 au 2026-04-30, **pas de 30 minutes**, **12 régions** métropolitaines (~2,8 M lignes).
- **Granularité** : une ligne = une région × un créneau de 30 min. Productions et consommation en **MW**.

> **Méthode de vérification.** Chaque information a été recoupée de deux façons :
> ✅ **doc** = documentation officielle RTE/ODRE ; ✅ **données** = vérifié directement sur le jeu.

---

## 🏷️ Repères (identifiants, temps)

| Variable | Type | En clair |
|---|---|---|
| `code_insee_region` | texte | Le numéro officiel de la région (ex. `75` pour la Nouvelle-Aquitaine). |
| `libelle_region` | texte | Le nom de la région. Il y en a 12, la métropole seulement. |
| `nature` | texte | Dit si la mesure est **définitive** (validée, jusqu'à 2024) ou **consolidée** (récente, encore susceptible d'être corrigée). |
| `date` | texte | La date, **au calendrier français** (`AAAA-MM-JJ`). |
| `heure` | texte | L'heure **qu'affichait une horloge en France** (`HH:MM`), donc décalée de +1 h en hiver et +2 h en été. |
| `date_heure` | datetime (UTC) | Le **même instant**, mais exprimé en heure universelle, qui ne subit pas les changements d'heure. Seul champ déjà typé en date. |

## ⚡ Consommation & production par filière (MW, pas de 30 min)

Toutes ces colonnes sont une **puissance instantanée en mégawatts**, mesurée toutes
les 30 minutes. Ce n'est pas une quantité d'énergie consommée sur la période, mais
le débit électrique à cet instant.

| Variable | Unité | En clair | Remarques |
|---|---|---|---|
| `consommation` | MW | L'électricité **appelée** par la région à cet instant : logements, entreprises, transports. | |
| `solaire` ⭐ | MW | L'électricité produite par les **panneaux photovoltaïques**. Nulle la nuit, maximale en milieu de journée. | Cœur du projet |
| `eolien` | MW | L'électricité produite par les **éoliennes**, terrestres et en mer confondues. Géographie inverse de celle du solaire : les régions du Nord dominent. | ⚠️ **stockée en texte** ; `'ND'` et `'-'` valent manquant, voir les points de vigilance |
| `eolien_terrestre` | MW | La part produite par les éoliennes **à terre**. | |
| `eolien_offshore` | MW | La part produite par les éoliennes **en mer**. | Faible, déploiement récent |
| `nucleaire` | MW | L'électricité produite par les **centrales nucléaires** situées dans la région. **7 régions sur 12** en ont une. | Vide pour les 5 autres jusqu'en 2020, puis **zéro** à partir de 2021 : voir l'avertissement sur les moyennes |
| `hydraulique` | MW | L'électricité produite par l'**eau** : barrages, centrales au fil de l'eau, et **turbinage des STEP** (voir `pompage`). | |
| `thermique` | MW | L'électricité produite en **brûlant** du gaz, du charbon ou du fioul. Pilotable, sert d'ajustement. | |
| `bioenergies` | MW | L'électricité produite à partir de **biomasse, biogaz et déchets**. | Faible et très stable |
| `pompage` | MW | Le **stockage hydraulique** en train de se remplir. Une STEP a deux bassins : quand il y a de l'électricité en trop, on s'en sert pour **pomper** l'eau vers le bassin haut. C'est donc une consommation. | **Toujours ≤ 0** (vérifié : 100 %). ⚠️ Seul le remplissage figure ici ; la restitution est fondue dans `hydraulique` |
| `ech_physiques` | MW | Le solde des **échanges avec les régions voisines**. C'est ce qui rend le réseau interconnecté : une région peut consommer ce qu'elle ne produit pas. | **< 0 : la région exporte. > 0 : elle importe.** Vérifié : 46 % / 54 % |

## 🔋 Stockage par batterie

| Variable | En clair | Remarques |
|---|---|---|
| `stockage_batterie` | L'électricité que les batteries sont en train d'**absorber**. | ❌ **Toujours à 0 dans ce jeu régional, inexploitable** (vérifié : min = max = 0) |
| `destockage_batterie` | L'électricité que les batteries **restituent** au réseau. | ❌ idem |

Conséquence pratique : le **seul stockage observable** dans ce jeu est le pompage
hydraulique (`pompage`), pas les batteries.

## 📊 Taux par filière (%)

Deux indicateurs, disponibles pour : thermique, nucléaire, éolien, solaire, hydraulique, bioénergies.

| Préfixe | En clair | Formule et vérification |
|---|---|---|
| `tco_…` | **Taux de couverture** : quelle **part de la consommation** cette filière couvre à cet instant. Exemple : `tco_solaire` = 30 % signifie que le solaire fournissait 30 % de l'électricité appelée. | `100 × filiere / consommation`. ✅ doc **et** données : écart médian 0,003 point, maximum 0,01, pour toutes les filières |
| `tch_…` | **Taux de charge** : à quel point le parc **tourne par rapport à sa taille**. Élevé en plein soleil, nul la nuit. Ne dépend pas de la consommation. | `100 × filiere / puissance installée`. ✅ doc RTE, non vérifiable directement : la puissance installée n'est pas fournie |

Exemples : `tco_solaire`, `tch_solaire`, `tco_eolien`, `tch_eolien`, etc.

**La différence en une phrase** : le TCO se compare à la **demande**, le TCH se
compare à la **capacité de production**.

Deux points utiles, tous deux exploités par `src/preparation.py` :

- Les deux séries n'existent qu'à partir de **2020** (0 % renseigné avant, 100 % après).
  Le TCO étant une formule exacte, il est **reconstruit** pour 2013-2019, et les
  lignes concernées sont marquées par la colonne `tco_reconstruit`.
- Le TCH ne peut pas être reconstruit, mais il peut être **inversé** pour en déduire
  la puissance installée : `puissance installée = 100 × filiere / tch`. C'est une
  information réellement nouvelle (la taille du parc n'est nulle part ailleurs dans
  le jeu), disponible sur **2020-2026 seulement**. Voir `capacite_installee()`.

### Le TCH comme approche de la ressource solaire, et ses limites

La production en MW **mélange deux causes** : la ressource reçue et la taille du
parc installé. On ne peut donc pas conclure d'une forte production qu'une région
est ensoleillée. Le TCH, lui, **divise par le parc** : ce qui reste mesure ce que
chaque mégawatt installé parvient à produire, ce qui approche la ressource.

C'est le seul indicateur interne au jeu permettant de séparer les deux causes, et
il évite l'erreur qui consiste à déduire l'ensoleillement de la production.

⚠️ **Mais ce n'est pas de l'irradiance.** Quatre réserves à garder en tête :

| Réserve | Effet |
|---|---|
| **Écrêtement** | Si le réseau ne peut absorber toute la production, elle est coupée. Le TCH baisse **sans que le soleil ait diminué**, et cela touche d'abord les régions les plus solaires : le biais joue donc dans le sens même qu'on cherche à mesurer. |
| **Orientation et inclinaison** des panneaux | Deux parcs sous le même soleil n'ont pas le même rendement. |
| **Technologie et âge** du parc | Un parc récent produit davantage à capacité égale. |
| **Disponible à partir de 2020 seulement** | Sept années restent hors de portée. |

S'y ajoute que la formule du TCH **n'a jamais pu être vérifiée sur les données**,
faute de connaître la puissance installée, contrairement au TCO dont la formule a
été confirmée au centième de point près. On fait donc confiance à la définition
de RTE.

**Conclusion d'usage** : le TCH permet de dire *si* la ressource explique une part
des écarts régionaux, pas de la quantifier précisément. Pour cela il faudra une
source météorologique externe.

**Étalon disponible pour vérifier ces calculs.** ODRE publie un jeu officiel de
facteurs de charge régionaux annuels,
[`fc-tc-regionaux-annuels-enr`](https://odre.opendatasoft.com/explore/dataset/fc-tc-regionaux-annuels-enr/),
couvrant **2014 à 2024** et incluant la Corse, absente d'éCO2mix régional. Il va
donc au-delà de la limite de 2020 du TCH.

Comparaison menée sur 2020-2025 : **corrélation des valeurs r = 0,987**, écart de
rang maximal de 2 places. En revanche les valeurs recalculées à partir d'éCO2mix
dépassent l'officiel de **0,6 à 0,8 point de façon systématique**, par différence
de définition : la moyenne des taux instantanés surestime le rapport de l'énergie
annuelle à la puissance installée, le parc grandissant en cours d'année. Ce biais
n'affecte ni le classement ni les rapports entre régions.

## 🧮 Colonnes calculées

Ces colonnes ne viennent pas de la source : elles sont fabriquées par
`src/preparation.py` au chargement.

| Variable | Unité | En clair |
|---|---|---|
| `date_heure_locale` | datetime | Le même instant que `date_heure`, mais **converti en heure française**. C'est la référence à utiliser pour tout profil journalier. |
| `heure_decimale` | heures | L'heure locale sous forme de nombre : 13,5 pour 13 h 30. Pratique pour tracer une courbe et regrouper par créneau. |
| `annee`, `mois`, `jour_semaine` | entier | Découpage du calendrier, **en heure locale**. `jour_semaine` va de 0 (lundi) à 6 (dimanche). |
| `saison` | catégorie ordonnée | `Hiver`, `Printemps`, `Été`, `Automne`, au sens **météorologique** : l'hiver couvre décembre, janvier et février, et ainsi de suite. |
| `demande_nette` ⭐ | MW | Ce qu'il **reste à produire** une fois retirées les renouvelables non pilotables : `consommation − solaire − eolien`. C'est la variable centrale du projet : elle mesure le travail qui incombe au reste du système. Convention du secteur. |
| `demande_nette_solaire` | MW | La même chose, mais en ne retirant **que le solaire** : `consommation − solaire`. Isole l'objet d'étude du projet. L'écart avec `demande_nette` mesure exactement l'apport de l'éolien. |
| `tco_reconstruit` | booléen | Vaut `True` là où le taux de couverture a été **recalculé** par nos soins (années 2013 à 2019), et `False` là où il vient de RTE. Sert à ne jamais confondre une valeur publiée et une valeur reconstruite. |

⚠️ `demande_nette` est **indéfinie** sur les 96 lignes où l'éolien manque. C'est
volontaire : on préfère un trou visible à un zéro inventé. `demande_nette_solaire`
n'a pas ce problème, le solaire étant renseigné partout.

## 🗑️ À ignorer

| Variable | En clair |
|---|---|
| `column_30` | Colonne parasite, entièrement vide, sans aucun contenu. Supprimée au chargement. |

---

## ⚠️ Points de vigilance qualité (constats sur les données)

- **Fuseau horaire, piège actif** : `date_heure` est en **UTC**, alors que `date` et `heure` sont en **heure locale**. Raisonner sur l'heure UTC fabrique une fausse déformation saisonnière : le pic solaire moyen y tombe à 11 h en juin contre 12 h en décembre, un décalage dû au seul changement d'heure (en heure locale il est à 13 h dans les deux cas). Utiliser `heure_decimale`, dérivée de `date_heure_locale` par `src/preparation.py`, pour tout profil journalier.
- **Début de série vide** : les toutes premières lignes (jan. 2013) sont entièrement à `NaN`, il faut filtrer sur `consommation` renseignée.
- **`eolien` en texte** : à convertir en numérique. Les deux marqueurs ne désignent pas la même chose :
  - **`ND`, 12 lignes** (les 12 régions, 1er janvier 2013) : la ligne entière est vide. Elles disparaissent de toute façon avec le filtre sur `consommation`.
  - **`-`, 96 lignes** : lignes par ailleurs valides où seul l'éolien manque. Ce sont **deux pannes de mesure d'une journée complète** (48 créneaux contigus chacune) : Centre-Val de Loire les 27 et 28 décembre 2013, Île-de-France les 8 et 9 mai 2013.
  - ⚠️ **Ne pas remplacer par zéro.** Le Centre-Val de Loire produisait 550 MW juste avant le trou et 620 MW juste après : le parc tournait à plein régime. Un zéro fabriquerait un effondrement de production de 24 heures suivi d'un retour instantané. La valeur manquante est le traitement correct, et c'est ce que fait `src/preparation.py`.
  - Conséquence : ce sont exactement les 96 lignes où `demande_nette` reste indéfinie.
- **Batteries vides** : `stockage_batterie` / `destockage_batterie` inexploitables (voir ci-dessus).
- **Valeurs négatives de production** : elles ne sont **pas des erreurs**, ce sont les installations qui **consomment** au lieu de produire (auxiliaires d'une centrale à l'arrêt, onduleurs des panneaux la nuit). Ne pas les ramener à zéro : pour la demande nette, un solaire négatif l'augmente légèrement, ce qui est correct.

  ⚠️ **Mais le phénomène est enregistré de façon incohérente.** Il est physiquement réel partout, il n'est déclaré que par certaines régions et à certaines époques. Ne jamais comparer les régions sur cette base (détail plus bas).

  | Filière | Lignes < 0 | % | Minimum | Médiane des négatifs |
  |---|---|---|---|---|
  | `thermique` | 78 327 | 2,79 % | −83 | −3 |
  | `solaire` | 33 429 | 1,19 % | −23 | −1 |
  | `nucleaire` | 444 | 0,02 % | −144 | −87 |
  | `eolien` | 619 | 0,02 % | −6 | −1 |
  | `hydraulique` | 8 | 0,00 % | −6 | −1 |
  | `bioenergies` | 0 | 0 % | | jamais négative |

  Deux indices confirment la lecture physique sur le **moment** où elles surviennent : le solaire n'est **jamais** négatif entre 10 h et 14 h (84 % des cas surviennent la nuit), et la médiane du nucléaire négatif, −87 MW, correspond à l'ordre de grandeur des auxiliaires d'un réacteur à l'arrêt. Les amplitudes restent faibles face aux niveaux habituels (−144 MW contre 6 075 MW de production moyenne pour le nucléaire).

- ⚠️ **Le solaire négatif est une pratique de déclaration, pas une différence régionale réelle.** Avant 2020, il est concentré à **99,8 % en Nouvelle-Aquitaine** (33 379 lignes, soit 27,2 % de ses relevés). L'Occitanie, dont le parc solaire est comparable (206 MW de production moyenne contre 243), n'en compte que **9**, un rapport de 1 à 3 700. Les huit autres régions n'en ont aucune. Les panneaux d'Occitanie consomment pourtant la nuit eux aussi : la Nouvelle-Aquitaine est simplement la seule à l'avoir reporté, entre 2015 et 2019.

  Conséquences : **ne pas comparer les régions** sur cette base, et se méfier de la série solaire de la Nouvelle-Aquitaine avant 2020 pour toute analyse pluriannuelle.

  Le **thermique** négatif suit une logique différente, mieux expliquée par la taille du parc : l'Occitanie, avec un parc minuscule (32 MW de moyenne), passe souvent au négatif parce que ses auxiliaires dominent, alors que les Pays de la Loire, avec le plus gros parc (532 MW), sont rarement négatifs parce que leurs centrales tournent.

- ⚠️ **Le vide devient zéro en 2021, et ça fausse les moyennes.** Les colonnes `nucleaire`, `pompage`, `eolien_terrestre` et les batteries passent d'un remplissage partiel à **100 %** en 2021. Ce ne sont pas de nouvelles données : les régions concernées passent de « case vide » à « zéro ». Conséquence mesurée : la moyenne du nucléaire sur les 12 régions chute de **37,1 %** en 2021, alors que la moyenne sur les **7 régions qui ont réellement une centrale augmente de 7,9 %**. La chute est un pur artefact de calcul.

  ➡️ **Règle** : ne jamais moyenner sur les 12 régions sans vérifier le taux de remplissage de la variable sur la période. Restreindre aux régions réellement concernées, ou traiter les vides et les zéros de la même façon.

  (À titre de comparaison, la baisse de **22,7 %** du nucléaire en **2022** est **réelle** : les deux modes de calcul donnent le même résultat. Il s'agit de la crise du parc.)

- ⚠️ **Rupture de méthode en 2020, à retenir pour toute analyse pluriannuelle.** **Aucune** valeur négative n'apparaît après 2019, toutes filières confondues. C'est la même année où RTE commence à publier les `tco_` et `tch_`. Tout indique un changement de convention côté RTE, qui aurait cessé de reporter la consommation propre des installations. Conséquence : une évolution observée entre 2013 et 2026 peut refléter ce changement comptable plutôt qu'un phénomène réel. À prendre en compte pour la sous-question 2.
- **`tco_`/`tch_` peuvent dépasser 100 %** : normal pour le TCO (à un instant, une région peu consommatrice et bien ensoleillée peut produire plus que sa consommation locale, surplus exporté) ; pour le TCH, lié à la référence de capacité installée.
- ⚠️ **`tch_solaire` monte jusqu'à 172,49 %**, ce qui n'est physiquement pas possible : un parc ne produit pas 1,7 fois sa puissance installée. Mesuré : **56 lignes** au-dessus de 100 % (0,0042 % du total), en 2020, 2023, 2024 et 2025, concentrées dans les régions **du Nord** (Grand Est 17, Hauts-de-France 16, Bretagne 10, Bourgogne-Franche-Comté 9, Normandie 2). Lecture la plus probable : la puissance installée de référence utilisée par RTE est **en retard sur le parc réel** dans ces régions, où le solaire croît vite depuis une base faible. Conséquence pratique : `capacite_installee()` inverse précisément cette variable, ses valeurs sont donc **sous-estimées** pour ces régions et ces dates. Sans effet sur les analyses actuelles, qui emploient des médianes, mais bloquant pour toute lecture ponctuelle de la capacité.
- **Doublons et trous d'horodatage** : ~28 doublons et ~13 petits trous par région (changements d'heure ou relevés manquants), marginaux (~0,02 %).
- **`nucleaire`** : ~75 % renseigné (les régions sans centrale nucléaire sont à vide, ce n'est pas une donnée manquante).

---

## Sources

- [ODRE : Données éCO2mix régionales consolidées et définitives](https://odre.opendatasoft.com/explore/dataset/eco2mix-regional-cons-def/information/)
- [RTE : éCO2mix, production d'électricité par filière](https://www.rte-france.com/eco2mix/la-production-delectricite-par-filiere)
- Définitions TCO/TCH : documentation RTE-éCO2mix.
