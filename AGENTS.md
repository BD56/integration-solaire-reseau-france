# AGENTS.md

Document de référence de ce projet, valable pour **tous** les assistants (Claude, Mistral Vibe, autres). À lire en priorité, avant toute modification.

Le **style de travail général** attendu par Bryan, indépendant du projet, est dans le dépôt séparé **`guide-assistant`**. Ce fichier ne couvre que ce qui est propre à ce projet.

L'**historique des décisions et des constats** est dans [`docs/journal-projet.md`](docs/journal-projet.md), par ordre chronologique inverse. À consulter en début de session pour savoir où en est le projet, et à compléter d'une entrée quand une décision est prise.

---

## 1. Objet

Analyse de l'intégration de la production solaire dans le réseau électrique français, à partir des données officielles RTE / Enedis.

Problématique figée : *comment la montée du solaire transforme-t-elle la demande nette d'électricité en France, et comment le système s'adapte-t-il à son intermittence ?*

Le découpage en deux phases et les sous-questions sont détaillés dans le [`README.md`](README.md). Ne pas les redéfinir sans en discuter avec Bryan.

## 2. Langue et typographie

- **Tout est en français** : documentation, README, commentaires de code, messages de commit, noms de variables métier.
- **Éviter les anglicismes.** Employer une formulation descriptive française pour un concept dont le nom courant est anglais. Exemple imposé : le terme « duck curve » est proscrit, dire « demande nette », « creux de mi-journée », « remontée du soir ».
- **Pas de tiret cadratin « — » dans la documentation.** Le remplacer par deux points, une virgule, une parenthèse ou un point-virgule selon le sens. Le signe moins « − » et la flèche « → » restent autorisés, ils portent du sens.

## 3. Environnement et reproductibilité

- Gestion par **uv**, Python **3.12**. Dépendances verrouillées dans `uv.lock`.
- Installation : `uv sync`. Téléchargement des données : `uv run python src/download.py`.
- Les **données ne sont pas versionnées** (`data/` est ignoré). Elles sont régénérables en une commande depuis l'API ODRE.
- Les rendus HTML de la documentation (`docs/*.html`) sont régénérés localement et ignorés. Ne pas s'en préoccuper.

## 4. Format du code d'analyse

- Les analyses sont des **scripts `.py` découpés en cellules `# %%`**, pas des carnets `.ipynb`. Raison : différences Git lisibles et pas de dépendance à Jupyter. Bryan les exécute cellule par cellule dans Spyder.
- Nommage : `notebooks/NN_sujet.py`, numérotation croissante dans l'ordre logique de lecture (`01_exploration.py`, `02_visualisation.py`, ...).
- **Tout code d'analyse qui compte va dans le dépôt**, sous forme rejouable. Un résultat produit par un script jetable dont Bryan ne voit que la sortie n'a aucune valeur : il doit pouvoir le réexécuter et le vérifier lui-même.
- **Séparer les faits de l'interprétation.** Annoncer clairement ce que le code montre, puis, distinctement, la lecture qu'on en fait. Bryan doit pouvoir se forger la sienne.

## 5. Données : réserves connues

Jeu `eco2mix-regional-cons-def` (ODRE), pas de 30 minutes, 12 régions métropolitaines, environ 2,8 millions de lignes depuis fin 2012. Le détail des 32 variables est dans [`docs/dictionnaire_donnees.md`](docs/dictionnaire_donnees.md).

Pièges vérifiés sur les données, à traiter systématiquement :

| Point | Constat | Traitement |
|---|---|---|
**Tout le chargement et le nettoyage sont centralisés dans `src/preparation.py`.** Ne pas les réécrire dans un script d'analyse : appeler `charger_donnees()`. Le détail des 32 colonnes est dans le [dictionnaire](docs/dictionnaire_donnees.md), qui fait foi.

| Point | Constat | Traitement |
|---|---|---|
| `eolien` | typée texte. `ND` (12 lignes) = ligne entièrement vide ; `-` (96 lignes) = **deux pannes de mesure d'une journée** en 2013 | convertir en numérique (`errors="coerce"`). **Ne jamais remplacer par zéro** : le parc tournait à 550 MW juste avant le trou |
| `column_30` | colonne parasite, entièrement vide | supprimer |
| `stockage_batterie`, `destockage_batterie` | **toujours à zéro**, inexploitables | ne pas construire d'analyse dessus. Le seul stockage observable est `pompage` |
| horodatages | passage à l'heure d'été : les créneaux locaux 02:00 et 02:30 n'existent pas mais sont publiés, et retombent sur le même instant UTC que 03:00 et 03:30 | supprimer les deux étiquettes fictives, pas déduper au hasard. Le jour doit compter **46** créneaux |
| horodatages | passage à l'heure d'hiver : une heure réelle **manque** (saut de 1 h 30 en UTC, une fois par an et par région) | la série UTC **n'est pas une grille régulière**. Bloquant pour tout modèle de série temporelle |
| fuseau | `date_heure` est en **UTC**, `date` et `heure` sont en **heure locale** | raisonner en UTC fabrique une fausse déformation saisonnière. Utiliser `heure_decimale` |
| valeurs négatives | production négative = l'installation consomme (auxiliaires, onduleurs la nuit). Physiquement réel, mais **déclaré de façon incohérente** : le solaire négatif est à 99,8 % en Nouvelle-Aquitaine, 2015-2019 | ne pas corriger, mais **ne jamais comparer les régions** sur cette base |
| `nature` | `Données définitives` jusqu'à 2024, `Données consolidées` pour 2025-2026 (révisables) | découpage temporel, pas un doublon. Conserver les deux |

### Ruptures temporelles, à connaître avant toute analyse pluriannuelle

| Année | Rupture | Portée |
|---|---|---|
| **2021** | `nucleaire`, `pompage`, `eolien_terrestre` et les batteries passent de « case vide » à « **zéro** » | ⚠️ **Le piège principal.** La moyenne du nucléaire sur les 12 régions chute de **37,1 %** en 2021, alors qu'elle **augmente de 7,9 %** sur les 7 régions qui ont réellement une centrale. La chute est un pur artefact de calcul |
| **2020** | fin des valeurs négatives, apparition des `tco_` et `tch_` | changement de convention RTE. Frontière pour toute série solaire longue |
| 2015 | apparition du solaire négatif en Nouvelle-Aquitaine, du `pompage` en Hauts-de-France | artefacts de déclaration |
| 2022 | crise du parc nucléaire | **réelle** (−22,7 %, confirmé par les deux modes de calcul) |
| mars à juin 2020 | confinement | réel, passager, touche la consommation |
| 2016 | réforme des régions | **aucune trace** : 12 régions sur toute la période, historique reconstruit par RTE |

➡️ **Règle qui en découle : ne jamais moyenner sur les 12 régions sans vérifier le taux de remplissage** de la variable sur la période considérée. Restreindre aux régions réellement concernées.

Le recensement complet et son classement par importance sont dans le [journal](docs/journal-projet.md), entrée du 2026-07-26 (suite 3).

## 5 bis. Discipline de méthode, imposée après plusieurs erreurs

Ces règles viennent d'échecs constatés, détaillés dans le [journal](docs/journal-projet.md). Elles s'appliquent à tout nouveau calcul.

**Écrire le critère de validation avant de calculer.** Sinon le critère se relâche une fois le résultat vu. Une prédiction se consigne dans le journal **avant** d'être vérifiée.

**Conserver les hypothèses rejetées.** Un rejet est un résultat. Ne garder que ce qui fonctionne revient à choisir ses preuves.

**Chercher la méthode établie avant d'improviser une mesure.** Pour une saisonnalité, il existe la décomposition STL, la force de saisonnalité de Hyndman, l'analyse spectrale, le test de Kruskal-Wallis. Trois mesures improvisées se sont révélées sans valeur au cours de ce projet.

**Vérifier qu'un test peut échouer.** Question à poser systématiquement : *le résultat découle-t-il de la définition des grandeurs comparées ?* Si oui, le test ne prouve rien. Une validation doit confronter à une référence **extérieure** à ce qu'elle valide. C'est cette question qui a fait tomber le diagnostic circulaire de l'indice de ciel clair.

**Se méfier des bornes choisies à la main.** Les faire varier avant de publier. La date du basculement de la demande nette passait de 2015 à 2021 selon les fenêtres horaires retenues, jusqu'à ce qu'une mesure sans paramètre la fixe.

**Ne pas présenter une supposition comme un constat.** La production solaire mélange ressource et parc installé : en déduire un classement d'ensoleillement est une supposition, pas une mesure. Distinguer toujours ce que le code montre, ce qu'on en déduit, et ce qu'on suppose sans pouvoir le vérifier.

## 6. Principe méthodologique : pas de raisonnement en autarcie régionale

Le réseau est **interconnecté**. « Une région ne produit pas telle filière localement » ne veut **pas** dire « cette région ne dépend pas de cette filière ».

Exemple vérifié : l'Île-de-France n'a aucune centrale nucléaire, et sa production locale toutes filières confondues ne couvre qu'environ 4,5 % de sa consommation (médiane). Le reste vient d'imports interrégionaux. Les cinq régions sans centrale nucléaire (Bretagne, Pays de la Loire, Provence-Alpes-Côte d'Azur, Île-de-France, Bourgogne-Franche-Comté) sont importatrices quasiment 100 % du temps.

→ Pour parler de dépendance à une filière, toujours regarder `ech_physiques` en plus de la production locale. Ne jamais conclure qu'une région ne bénéficie pas d'une filière au seul motif qu'elle n'en produit pas.

Distinction utile : le solaire et l'éolien sont les **objets d'étude** (fortement variables) ; le nucléaire, l'hydraulique et le thermique sont les **acteurs de l'équilibrage** ; les bioénergies sont quasi négligeables (écart-type le plus faible). Le nucléaire varie très peu dans le temps (amplitude jour et nuit d'environ 198 MW, contre environ 442 MW pour le solaire), ce n'est pas un objet d'étude dynamique.

## 7. Travail à deux assistants

Bryan travaille avec deux assistants sur ce projet :

- **Claude Code** : accès à la machine locale **et** au dépôt distant. Peut exécuter le code et pousser.
- **Mistral Vibe** : accès **uniquement au dépôt GitHub**. Aucun accès à la machine, ni aux conversations tenues avec Claude.

Conséquences pratiques :

- GitHub est le **seul point de synchronisation**. Ce qui n'est pas poussé n'existe pas pour Mistral.
- Toute décision structurante doit être écrite dans [`docs/journal-projet.md`](docs/journal-projet.md) puis poussée, sinon elle est perdue pour l'autre assistant.
- Le code et la documentation doivent être **autoportants** : l'autre assistant n'a que le dépôt comme contexte.
- Côté Mistral Vibe, attacher aussi le dépôt `guide-assistant` pour le style de travail général.

## 8. Attentes de Bryan sur la conduite du travail

- **Le contredire quand c'est justifié.** Il cherche un partenaire de réflexion, pas une validation de complaisance. Concéder ce qui est juste, mais pointer clairement les failles et les angles morts, avec un avis tranché et argumenté.
- **Ne pas le traiter comme un débutant.** Il est en master de mathématiques appliquées et statistique, avec un portfolio fourni.
- **Ne pas aller trop vite.** Une étape à la fois, et vérifier l'état réel du dépôt avant de proposer une suite.

## 9. État et prochaine étape

Voir la dernière entrée de [`docs/journal-projet.md`](docs/journal-projet.md), qui fait foi.

Au 2026-07-25 : pipeline de données, dictionnaire de données et script d'exploration en place. **Aucune sous-question n'est encore traitée, aucun graphique produit.** Prochaine étape prévue : `notebooks/02_visualisation.py`, tracer la demande nette sur une journée type.
