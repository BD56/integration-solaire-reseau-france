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

| Variable | Intitulé | Type | Description |
|---|---|---|---|
| `code_insee_region` | Code INSEE région | texte | Code INSEE de la région (✅ doc) |
| `libelle_region` | Région | texte | Nom de la région (12 régions métropolitaines) |
| `nature` | Nature | texte | `Données définitives` (2013 à 2024, validées) ou `Données consolidées` (récentes, susceptibles de révision) |
| `date` | Date | texte | Date `AAAA-MM-JJ` |
| `heure` | Heure | texte | Heure `HH:MM` |
| `date_heure` | Date - Heure | datetime (UTC) | Horodatage complet (**seul champ déjà typé en date**) |

## ⚡ Consommation & production par filière (MW, pas de 30 min)

| Variable | Intitulé | Unité | Description | Remarques |
|---|---|---|---|---|
| `consommation` | Consommation | MW | Demande d'électricité de la région | |
| `solaire` ⭐ | Solaire | MW | Production photovoltaïque | Cœur du projet |
| `eolien` | Eolien | MW | Production éolienne totale | ⚠️ **stocké en texte** ; `'ND'`/`'-'` = manquant ; = terrestre + offshore |
| `eolien_terrestre` | Eolien terrestre | MW | Part terrestre de l'éolien | |
| `eolien_offshore` | Eolien offshore | MW | Part en mer de l'éolien | Faible (déploiement récent) |
| `nucleaire` | Nucléaire | MW | Production nucléaire | ~75 % renseigné (régions sans centrale = vide) |
| `hydraulique` | Hydraulique | MW | Production hydraulique | |
| `thermique` | Thermique | MW | Production thermique fossile (gaz, charbon, fioul) | |
| `bioenergies` | Bioénergies | MW | Production à partir de biomasse/déchets | |
| `pompage` | Pompage | MW | Puissance consommée par les pompes des **STEP** (stockage hydraulique) | **Toujours ≤ 0** (c'est une charge). ✅ données (100 % ≤ 0) |
| `ech_physiques` | Ech. physiques | MW | Solde des échanges avec les régions limitrophes | **< 0 = export, > 0 = import**. ✅ doc + données (46 % / 54 %) |

## 🔋 Stockage par batterie

| Variable | Intitulé | Description | Remarques |
|---|---|---|---|
| `stockage_batterie` | Stockage batterie | Énergie stockée en batterie | ❌ **Toujours à 0 dans ce jeu régional, inexploitable** (✅ données : min = max = 0) |
| `destockage_batterie` | Déstockage batterie | Énergie restituée par les batteries | ❌ idem |

## 📊 Taux par filière (%)

Deux indicateurs, disponibles pour : thermique, nucléaire, éolien, solaire, hydraulique, bioénergies.

| Préfixe | Nom complet | Définition | Vérification |
|---|---|---|---|
| `tco_…` | **Taux de COuverture** | Part de la filière dans la **consommation** de la région | ✅ doc **+ données** : `tco_solaire` = `100 × solaire / consommation` (écart médian 0.000, corrélation 1.0000) |
| `tch_…` | **Taux de CHarge** (facteur de charge) | Production rapportée à la **capacité installée et en service** de la filière | ✅ doc RTE (non vérifiable sur les données : la capacité installée n'est pas fournie) |

Exemples : `tco_solaire`, `tch_solaire`, `tco_eolien`, `tch_eolien`, etc.

## 🗑️ À ignorer

| Variable | Description |
|---|---|
| `column_30` | Colonne parasite, vide, à supprimer au chargement |

---

## ⚠️ Points de vigilance qualité (constats sur les données)

- **Début de série vide** : les toutes premières lignes (jan. 2013) sont entièrement à `NaN`, il faut filtrer sur `consommation` renseignée.
- **`eolien` en texte** : à convertir en numérique ; `'ND'` et `'-'` deviennent des valeurs manquantes.
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
