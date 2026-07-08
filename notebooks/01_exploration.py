"""Phase 1 — Étape 1 : exploration et nettoyage des données éCO2mix.

Objectif : charger les données, comprendre leur structure, repérer les
problèmes de qualité, puis construire la variable centrale du projet :
la DEMANDE NETTE (consommation - solaire - éolien).

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
Pense à régler le dossier de travail de Spyder sur la racine du projet.
"""

# %% Imports et chemins
from pathlib import Path

import pandas as pd

# Racine du projet = le dossier qui contient "data/".
# Robuste que le script soit lancé entier (__file__) ou cellule par cellule (cwd).
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
except NameError:  # en exécution cellule par cellule, __file__ n'existe pas
    PROJECT_ROOT = Path.cwd()

DATA_PATH = PROJECT_ROOT / "data" / "eco2mix_regional.parquet"
assert DATA_PATH.exists(), (
    f"Fichier introuvable : {DATA_PATH}\n"
    "Règle le dossier de travail de Spyder sur la racine du projet, "
    "ou lance d'abord : uv run python src/download.py"
)

# %% Chargement des données
df = pd.read_parquet(DATA_PATH)
print(f"{df.shape[0]:,} lignes x {df.shape[1]} colonnes")
print("Période :", df["date_heure"].min(), "->", df["date_heure"].max())
print("Régions :", df["libelle_region"].nunique())

# %% Structure : colonnes et types
print(df.dtypes)

# %% Qualité (1) : valeurs manquantes par colonne (on n'affiche que les colonnes concernées)
manquants = df.isna().sum()
print(manquants[manquants > 0].sort_values(ascending=False))

# %% Qualité (2) : 'eolien' est stocké en texte -> quelles valeurs ne sont pas numériques ?
non_numerique = pd.to_numeric(df["eolien"], errors="coerce").isna() & df["eolien"].notna()
print("Valeurs non numériques dans 'eolien' :", df.loc[non_numerique, "eolien"].unique())
print("Lignes concernées :", int(non_numerique.sum()))

# %% Nettoyage
propre = df.copy()

# a) Supprimer la colonne parasite (vide)
propre = propre.drop(columns=["column_30"])

# b) Convertir 'eolien' en nombre : 'ND' et '-' deviennent des valeurs manquantes (NaN)
propre["eolien"] = pd.to_numeric(propre["eolien"], errors="coerce")

# c) Retirer les lignes sans consommation (début de série vide, aucune information)
avant = len(propre)
propre = propre.dropna(subset=["consommation"]).reset_index(drop=True)
print(f"Lignes retirées (consommation manquante) : {avant - len(propre):,}")
print(f"Lignes restantes : {len(propre):,}")

# %% Variable centrale : la demande nette
# demande nette = consommation - production renouvelable variable (solaire + éolien)
# Remarque : là où l'éolien est manquant, la demande nette reste indéfinie (NaN),
# on ne comble pas artificiellement -> on garde une trace honnête du trou.
propre["demande_nette"] = propre["consommation"] - propre["solaire"] - propre["eolien"]
print("Demande nette indéfinie (éolien manquant) :", int(propre["demande_nette"].isna().sum()))
print(propre[["consommation", "solaire", "eolien", "demande_nette"]].describe())

# %% Contrôle sur un cas concret : une journée d'été en PACA (région ensoleillée)
jour = propre[
    (propre["libelle_region"] == "Provence-Alpes-Côte d'Azur")
    & (propre["date"] == "2024-06-21")
].sort_values("heure")
apercu = jour[["heure", "consommation", "solaire", "eolien", "demande_nette"]].iloc[::4]
print(apercu.to_string(index=False))
