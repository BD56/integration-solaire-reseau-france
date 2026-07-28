"""Phase 2, étape 2 : construction et validation de l'indice de ciel clair.

L'indice mesure la nébulosité à partir de la production solaire seule, sans
aucune source météorologique. Il servira ensuite d'arbitre pour départager des
agrégations spatiales de la météo : une agrégation candidate sera jugée à sa
corrélation avec lui.

Protocole, figé avant construction (journal du 2026-07-28)
----------------------------------------------------------
Les réglages (fenêtre de 30 jours, quantile 0,95, maille créneau × région) ont
été écrits **avant** tout calcul et **ne seront pas ajustés** au vu des tests.
Si l'indice échoue, c'est l'indice qui sera déclaré inadapté.

Trois tests internes, avec leur seuil d'échec écrit à l'avance :

1. **Neutralité saisonnière.** L'enveloppe glissante absorbant déjà la course du
   soleil, l'indice ne devrait presque pas avoir de cycle saisonnier.
   Échec si l'indice médian de décembre s'écarte de plus de **0,15** de celui de
   juin. Ce serait le signe que l'enveloppe manque de journées dégagées en hiver.
2. **Cohérence spatiale.** Les nuages étant des phénomènes de grande échelle, la
   corrélation entre régions doit **décroître avec la distance**.
   Échec sinon : l'indice mesurerait autre chose que le ciel.
3. **Comportement sur journées identifiables.** Les journées les plus lumineuses
   doivent donner un indice proche de 1, les plus sombres un indice très bas.

Aucune source externe n'est consultée dans ce script, volontairement.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et construction
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
    annees_incompletes,
    indice_ciel_clair,
    indice_journalier,
)
from src.preparation import charger_donnees  # noqa: E402

SEUIL_SAISON = 0.15

df = charger_donnees()
df = df[~df["annee"].isin(annees_incompletes(df))]

avec_indice = indice_ciel_clair(df)
journalier = indice_journalier(avec_indice)

exploitables = avec_indice["indice_ciel_clair"].notna()
print(f"Créneaux exploitables : {exploitables.sum():,} sur {len(avec_indice):,} "
      f"({100 * exploitables.mean():.1f} %)".replace(",", " "))
print(f"Journées couvertes    : {len(journalier):,}".replace(",", " "))
print(f"\nIndice journalier : moyenne {journalier['indice'].mean():.3f}, "
      f"écart-type {journalier['indice'].std():.3f}")

# %% Rappel : les valeurs obtenues lors de l'étude de faisabilité
# (journal du 2026-07-25, code non versionné) : moyenne 0,717, écart-type 0,226,
# autocorrélation à J-1 de 0,430. Sert de point de repère, pas de critère.
journalier_trie = journalier.sort_values(["libelle_region", "date"])
decale = journalier_trie.groupby("libelle_region")["indice"].shift(1)
autocorrelation = journalier_trie["indice"].corr(decale)
print(f"Autocorrélation à J-1 : {autocorrelation:.3f}   "
      f"(étude de faisabilité : 0,430)")

# %% TEST 1 : neutralité saisonnière (échec si écart > 0,15)
journalier["mois"] = pd.to_datetime(journalier["date"]).dt.month
par_mois = journalier.groupby("mois")["indice"].median()
print(par_mois.round(3).to_string())

ecart_saison = abs(par_mois.loc[12] - par_mois.loc[6])
print(f"\n  décembre {par_mois.loc[12]:.3f}   juin {par_mois.loc[6]:.3f}   "
      f"écart {ecart_saison:.3f}")
print(f"  amplitude sur l'année : {par_mois.max() - par_mois.min():.3f}")
test1 = "RÉUSSI" if ecart_saison <= SEUIL_SAISON else "ÉCHOUÉ"
print(f"  seuil d'échec fixé à {SEUIL_SAISON}   ->   TEST 1 {test1}")

# %% TEST 2 : cohérence spatiale, la corrélation décroît-elle avec la distance ?
# Les distances sont calculées entre centres de régions, à vol d'oiseau.
CENTRES = {   # latitude, longitude approximatives des centres régionaux
    "Auvergne-Rhône-Alpes": (45.4, 4.6), "Bourgogne-Franche-Comté": (47.2, 4.8),
    "Bretagne": (48.2, -2.9), "Centre-Val de Loire": (47.5, 1.7),
    "Grand Est": (48.7, 5.6), "Hauts-de-France": (49.9, 2.7),
    "Normandie": (49.1, 0.1), "Nouvelle-Aquitaine": (45.2, 0.2),
    "Occitanie": (43.7, 2.0), "Pays de la Loire": (47.5, -0.8),
    "Provence-Alpes-Côte d'Azur": (43.9, 6.1), "Île-de-France": (48.7, 2.5),
}

tableau = journalier.pivot_table(index="date", columns="libelle_region", values="indice")
correlations = tableau.corr()

paires = []
for i, a in enumerate(CENTRES):
    for b in list(CENTRES)[i + 1:]:
        (lat_a, lon_a), (lat_b, lon_b) = CENTRES[a], CENTRES[b]
        distance = 111 * np.hypot(lat_a - lat_b, (lon_a - lon_b) * np.cos(np.radians(45)))
        paires.append({"a": a, "b": b, "distance_km": distance,
                       "correlation": correlations.loc[a, b]})
paires = pd.DataFrame(paires)

pente = np.polyfit(paires["distance_km"], paires["correlation"], 1)[0]
r_distance = paires["distance_km"].corr(paires["correlation"])
print(f"  {len(paires)} paires de régions")
print(f"  corrélation entre distance et corrélation des indices : r = {r_distance:+.3f}")
print(f"  pente : {pente * 100:+.4f} par 100 km")
print("\n  Les 3 paires les plus proches :")
print(paires.nsmallest(3, "distance_km").round(3).to_string(index=False))
print("\n  Les 3 paires les plus éloignées :")
print(paires.nlargest(3, "distance_km").round(3).to_string(index=False))
test2 = "RÉUSSI" if r_distance < -0.3 else "ÉCHOUÉ"
print(f"\n  TEST 2 {test2}   (la corrélation doit décroître avec la distance)")

# %% TEST 3 : comportement sur les journées extrêmes
extremes = journalier.groupby("date")["indice"].mean().sort_values()
print("  Les 5 journées les plus sombres (moyenne nationale) :")
print(extremes.head(5).round(3).to_string())
print("\n  Les 5 journées les plus lumineuses :")
print(extremes.tail(5).round(3).to_string())
# ⚠️ CORRIGÉ le 2026-07-28 après revue. Le critère n'avait PAS DE BORNE
# SUPÉRIEURE : `extremes.max() > 0.9` était satisfait par un maximum de 1,345,
# donc par une valeur physiquement impossible. Un indice de ciel clair vaut au
# plus 1 par définition ; au-delà, la production dépasse ce que l'enveloppe
# prétend être le maximum atteignable, ce qui signale une enveloppe fausse et non
# un ciel exceptionnel. Le test scorait « réussi » sur le symptôme même qu'il
# aurait dû détecter, et le journal le comptait ensuite parmi les « tests
# propres » en faveur de l'indice. Un test sans borne d'un côté ne départage pas.
haut, bas = extremes.max(), extremes.min()
test3 = "RÉUSSI" if 0.9 < haut <= 1.05 and bas < 0.4 else "ÉCHOUÉ"
print(f"\n  TEST 3 {test3}   (attendu : maximum entre 0,9 et 1,05, minimum très bas)")
if haut > 1.05:
    print(f"  ÉCHEC PAR LE HAUT : maximum à {haut:.3f}, or l'indice ne peut pas")
    print("  dépasser 1. L'enveloppe est trop basse sur ces journées.")

# %% Verdict des trois tests internes
print(pd.DataFrame([
    {"test": "1, neutralité saisonnière", "résultat": test1},
    {"test": "2, cohérence spatiale", "résultat": test2},
    {"test": "3, journées extrêmes", "résultat": test3},
]).to_string(index=False))
print("\nAucune source externe n'a été consultée. La confirmation extérieure")
print("viendra ensuite, et seulement ensuite.")
