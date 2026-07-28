"""Phase 2, étape 3 : validation de l'indice de ciel clair contre l'irradiance ERA5.

Ce script exécute le protocole écrit **avant tout calcul** dans le journal du
2026-07-28 (suite 5). Il ne le redéfinit pas et ne l'assouplit pas.

Rappel du critère, pour qu'on n'ait pas à le chercher ailleurs
--------------------------------------------------------------
Référence externe : irradiance ERA5 (Open-Meteo, `models=era5`), sans aucun lien
avec la production électrique française. Le test peut donc échouer, ce qui
manquait aux trois tentatives précédentes, dont une était circulaire.

Grandeur de comparaison : l'**indice de clarté** de Liu et Jordan (1960),

    k_t = irradiance globale au sol / irradiance extraterrestre

**Volet A, corrélation.** Spearman entre l'indice journalier et k_t journalier,
par région, sur 2021-2024. Médiane sur les 12 régions :

    >= 0,80  -> validé
    0,60 à 0,80 -> partiellement validé, usage restreint et signalé
    < 0,60   -> rejeté

**Volet B, utilité, et c'est le volet décisif.** L'indice doit faire mieux qu'un
concurrent trivial : le facteur de charge `tch_solaire`, disponible depuis 2020
et qui ne demande aucun calcul. S'il ne fait pas mieux, l'enveloppe glissante
n'apporte rien et l'indice est abandonné. Ce volet ne comporte aucun seuil
arbitraire.

Plafond connu d'avance, consigné au journal (suite 6) : deux séries ERA5
distantes d'environ 11 km ne s'accordent qu'à 0,977 en cumul journalier. Aucune
validation ne peut donc viser 1. Ce plafond ne sert pas d'excuse : il pèse
identiquement sur l'indice et sur son concurrent.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et chargement
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.analyses import (  # noqa: E402
    CENTRES_REGIONS,
    indice_ciel_clair,
    indice_journalier,
    irradiance_extraterrestre,
)
from src.meteo import charger_meteo  # noqa: E402
from src.preparation import charger_donnees  # noqa: E402

# Période figée au protocole : parc solaire déjà important, `tch_` disponible,
# et données déclarées définitives par RTE (les années 2025-2026 sont révisables).
ANNEES = range(2021, 2025)

SEUIL_VALIDE = 0.80
SEUIL_REJET = 0.60

df = charger_donnees()
meteo = charger_meteo()
print(f"Production : {len(df):,} lignes | Météo : {len(meteo):,} lignes")

# %% Indice de ciel clair journalier
# L'indice est construit sur TOUTE la période, pas seulement sur 2021-2024 :
# l'enveloppe glissante a besoin des bords pour ses fenêtres de 30 jours.
avec_indice = indice_ciel_clair(df)
journalier = indice_journalier(avec_indice)
journalier["date"] = pd.to_datetime(journalier["date"])

print(f"Journées couvertes par l'indice : {len(journalier):,}")
print(f"Indice : moyenne {journalier['indice'].mean():.3f}, "
      f"écart-type {journalier['indice'].std():.3f}")

# %% Indice de clarté k_t, journalier, à partir de la météo
# Convention Open-Meteo : la valeur horodatée à t est la moyenne sur l'heure
# PRÉCÉDANT t. On évalue donc la géométrie solaire au centre de cet intervalle,
# soit t moins 30 minutes, et c'est ce même instant qui décide du jour.
meteo = meteo.copy()
meteo["instant_centre"] = meteo["horodatage_utc"] - pd.Timedelta(minutes=30)

morceaux = []
for region, (latitude, longitude) in CENTRES_REGIONS.items():
    part = meteo[meteo["point"] == region].copy()
    part["extraterrestre"] = irradiance_extraterrestre(
        part["instant_centre"], latitude, longitude
    )
    morceaux.append(part)
meteo = pd.concat(morceaux, ignore_index=True)

# Le jour est celui de l'heure LOCALE, comme la colonne `date` des données RTE.
meteo["date"] = (
    meteo["instant_centre"].dt.tz_convert("Europe/Paris").dt.normalize().dt.tz_localize(None)
)

# k_t journalier = rapport des cumuls, et non moyenne des rapports horaires :
# c'est la définition standard, et elle évite la division par presque zéro à
# l'aube et au crépuscule.
clarte = (
    meteo.groupby(["point", "date"], observed=True)
    .agg(irradiance=("shortwave_radiation", "sum"),
         extraterrestre=("extraterrestre", "sum"),
         nebulosite=("cloud_cover", "mean"))
    .reset_index()
)
clarte = clarte[clarte["extraterrestre"] > 0]
clarte["k_t"] = clarte["irradiance"] / clarte["extraterrestre"]
clarte = clarte.rename(columns={"point": "libelle_region"})

print(f"k_t : moyenne {clarte['k_t'].mean():.3f}, "
      f"étendue {clarte['k_t'].min():.3f} à {clarte['k_t'].max():.3f}")

# %% Contrôle de plausibilité de k_t, avant de s'en servir comme référence
# Une référence qu'on n'a pas regardée n'est pas une référence. Les bornes
# attendues sont connues de la littérature : k_t journalier se situe en gros
# entre 0,05 (couvert épais) et 0,75 (ciel très clair) sous nos latitudes.
print("k_t moyen par mois, sur toute la période :")
print(clarte.assign(mois=clarte["date"].dt.month)
      .groupby("mois")["k_t"].mean().round(3).to_string())
print()
print(f"Part de k_t > 0,80 (suspect) : "
      f"{100 * (clarte['k_t'] > 0.80).mean():.2f} %")
print(f"Corrélation k_t / nébulosité déclarée : "
      f"{clarte['k_t'].corr(clarte['nebulosite'], method='spearman'):.3f}")

# %% Concurrent du volet B : le facteur de charge, sans aucun calcul savant
# Deux variantes, pour être équitable envers le concurrent :
#   - `tch_jour`   : moyenne sur les 48 créneaux du jour, donc facteur de charge
#                    journalier au sens strict ;
#   - `tch_jour_exploitables` : moyenne restreinte aux créneaux où l'indice est
#                    lui-même défini, pour comparer sur exactement la même base.
base = df[["libelle_region", "date", "tch_solaire"]].copy()
base["date"] = pd.to_datetime(base["date"])
concurrent = (
    base.dropna(subset=["tch_solaire"])
    .groupby(["libelle_region", "date"], observed=True)["tch_solaire"]
    .mean()
    .rename("tch_jour")
    .reset_index()
)

memes_creneaux = avec_indice.loc[
    avec_indice["indice_ciel_clair"].notna(),
    ["libelle_region", "date", "tch_solaire"],
].copy()
memes_creneaux["date"] = pd.to_datetime(memes_creneaux["date"])
concurrent_restreint = (
    memes_creneaux.dropna(subset=["tch_solaire"])
    .groupby(["libelle_region", "date"], observed=True)["tch_solaire"]
    .mean()
    .rename("tch_jour_exploitables")
    .reset_index()
)

print(f"Facteur de charge journalier : {len(concurrent):,} journées")

# %% Assemblage et restriction à la période du protocole
table = (
    journalier.merge(clarte, on=["libelle_region", "date"], how="inner")
    .merge(concurrent, on=["libelle_region", "date"], how="left")
    .merge(concurrent_restreint, on=["libelle_region", "date"], how="left")
)
table = table[table["date"].dt.year.isin(ANNEES)]
table = table.dropna(subset=["indice", "k_t", "tch_jour", "tch_jour_exploitables"])

print(f"Journées retenues : {len(table):,} "
      f"({table['date'].dt.year.min()} à {table['date'].dt.year.max()})")
print(table.groupby("libelle_region", observed=True).size().to_string())

# %% VOLET A et VOLET B : corrélations par région
resultats = []
for region, part in table.groupby("libelle_region", observed=True):
    resultats.append({
        "region": region,
        "journees": len(part),
        "indice": part["indice"].corr(part["k_t"], method="spearman"),
        "tch_jour": part["tch_jour"].corr(part["k_t"], method="spearman"),
        "tch_exploit": part["tch_jour_exploitables"].corr(part["k_t"], method="spearman"),
    })

resultats = pd.DataFrame(resultats).set_index("region")
resultats["gain_vs_tch"] = resultats["indice"] - resultats["tch_jour"]
resultats["gain_vs_exploit"] = resultats["indice"] - resultats["tch_exploit"]

print("Corrélation de Spearman avec k_t, par région :")
print(resultats.round(3).to_string())

# %% Verdict
mediane_indice = resultats["indice"].median()
mediane_tch = resultats["tch_jour"].median()
mediane_exploit = resultats["tch_exploit"].median()

print("=" * 70)
print("VOLET A : corrélation de l'indice à k_t")
print(f"  médiane sur les 12 régions : {mediane_indice:.3f}")
if mediane_indice >= SEUIL_VALIDE:
    verdict_a = "VALIDÉ"
elif mediane_indice >= SEUIL_REJET:
    verdict_a = "PARTIELLEMENT VALIDÉ, usage restreint"
else:
    verdict_a = "REJETÉ"
print(f"  -> {verdict_a}")

print()
print("VOLET B : l'indice bat-il le facteur de charge brut ?")
print(f"  médiane indice                : {mediane_indice:.3f}")
print(f"  médiane tch_solaire (jour)    : {mediane_tch:.3f}")
print(f"  médiane tch_solaire (mêmes créneaux) : {mediane_exploit:.3f}")
gagne = (resultats["gain_vs_tch"] > 0).sum()
gagne_exploit = (resultats["gain_vs_exploit"] > 0).sum()
print(f"  régions où l'indice fait mieux : {gagne}/12 (variante stricte : "
      f"{gagne_exploit}/12)")
verdict_b = "UTILE" if mediane_indice > max(mediane_tch, mediane_exploit) else "INUTILE"
print(f"  -> {verdict_b}")
print("=" * 70)
