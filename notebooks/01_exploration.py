"""Phase 1, étape 1 : exploration et contrôle qualité des données éCO2mix.

Le nettoyage n'est plus défini ici : il vit dans `src/preparation.py`, appelé
par tous les scripts d'analyse. Ce script sert à **vérifier** ce que fait ce
nettoyage et à documenter l'état des données, pas à le refaire.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
Le dossier de travail doit être la racine du projet.
"""

# %% Imports et accès au module de préparation
import sys
from pathlib import Path

import pandas as pd

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:  # exécution cellule par cellule : __file__ n'existe pas
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.preparation import charger_donnees, filtrer, resume_nature  # noqa: E402

# %% Données brutes : état avant nettoyage
brut = pd.read_parquet(RACINE / "data" / "eco2mix_regional.parquet")
print(f"{brut.shape[0]:,} lignes x {brut.shape[1]} colonnes")
print(brut.dtypes)

# %% Qualité (1) : valeurs manquantes, colonnes concernées uniquement
manquants = brut.isna().sum()
print(manquants[manquants > 0].sort_values(ascending=False))

# %% Qualité (2) : pourquoi 'eolien' est-elle en texte ?
non_numerique = pd.to_numeric(brut["eolien"], errors="coerce").isna() & brut["eolien"].notna()
print("Valeurs non numériques :", brut.loc[non_numerique, "eolien"].unique())
print("Lignes concernées :", int(non_numerique.sum()))

# %% Qualité (3) : les doublons d'horodatage tombent-ils sur les changements d'heure ?
doublons = brut.duplicated(subset=["libelle_region", "date_heure"], keep=False)
print(f"Lignes en doublon : {int(doublons.sum()):,}")
print("Dates concernées :", sorted(brut.loc[doublons, "date"].astype(str).unique()))

# %% Qualité (4) : colonnes de stockage par batterie, exploitables ?
for colonne in ["stockage_batterie", "destockage_batterie"]:
    serie = brut[colonne]
    print(f"{colonne:<22} min={serie.min()} max={serie.max()} "
          f"non nulles={(serie.fillna(0) != 0).sum()}")

# %% Chargement nettoyé (source unique : src/preparation.py)
df = charger_donnees()

# %% Contrôle du fuseau horaire : le pic solaire doit tomber à la même heure locale
for mois, libelle in [(6, "juin"), (12, "décembre")]:
    du_mois = df[df["mois"] == mois]
    pic_utc = du_mois.groupby(du_mois["date_heure"].dt.hour)["solaire"].mean().idxmax()
    pic_local = du_mois.groupby(du_mois["heure_decimale"])["solaire"].mean().idxmax()
    print(f"{libelle:<10} pic solaire : {pic_utc} h en UTC, {pic_local} h en heure locale")

# %% Nature des données : définitives (validées) contre consolidées (révisables)
print(resume_nature(df).tail(8))

# %% Panorama régional : quelles régions sont contrastées pour le solaire ?
recent = filtrer(df, annees=(2024, 2025))
panorama = (
    recent.groupby("libelle_region")
    .agg(
        solaire_moyen=("solaire", "mean"),
        consommation_moyenne=("consommation", "mean"),
        couverture_solaire=("tco_solaire", "mean"),
    )
    .round(1)
    .sort_values("couverture_solaire", ascending=False)
)
print(panorama.to_string())

# %% Contrôle sur un cas concret : une journée d'été en Nouvelle-Aquitaine
journee = df[
    (df["libelle_region"] == "Nouvelle-Aquitaine")
    & (df["date_heure_locale"].dt.date.astype(str) == "2024-06-21")
].sort_values("heure_decimale")
apercu = journee[["heure_decimale", "consommation", "solaire", "eolien", "demande_nette"]]
print(apercu.iloc[::4].to_string(index=False))
