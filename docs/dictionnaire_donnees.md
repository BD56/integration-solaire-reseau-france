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
| `nucleaire` | MW | L'électricité produite par les **centrales nucléaires** situées dans la région. | ~75 % renseigné : 5 régions n'ont aucune centrale, ce n'est pas une donnée manquante |
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
- **Petites valeurs négatives** sur certaines productions (`thermique`, `nucleaire`, `solaire`, `hydraulique` : quelques MW négatifs) : artefacts de mesure/consolidation (auto-consommation des centrales), marginaux.
- **`tco_`/`tch_` peuvent dépasser 100 %** : normal pour le TCO (à un instant, une région peu consommatrice et bien ensoleillée peut produire plus que sa consommation locale, surplus exporté) ; pour le TCH, lié à la référence de capacité installée.
- **Doublons et trous d'horodatage** : ~28 doublons et ~13 petits trous par région (changements d'heure ou relevés manquants), marginaux (~0,02 %).
- **`nucleaire`** : ~75 % renseigné (les régions sans centrale nucléaire sont à vide, ce n'est pas une donnée manquante).

---

## Sources

- [ODRE : Données éCO2mix régionales consolidées et définitives](https://odre.opendatasoft.com/explore/dataset/eco2mix-regional-cons-def/information/)
- [RTE : éCO2mix, production d'électricité par filière](https://www.rte-france.com/eco2mix/la-production-delectricite-par-filiere)
- Définitions TCO/TCH : documentation RTE-éCO2mix.
