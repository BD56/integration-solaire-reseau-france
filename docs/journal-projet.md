# Journal du projet

Fichier de suivi des décisions et des constats, tenu par ordre chronologique inverse (le plus récent en haut).

Objectif : garder une trace lisible par toute personne ou assistant qui reprend le projet, y compris sans accès à l'historique des conversations. Chaque entrée précise les faits établis, les décisions actées, et ce qui reste ouvert.

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
