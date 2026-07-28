"""Phase 2, étape 1 : les écarts régionaux viennent-ils du soleil ou du parc ?

La production en MW mélange deux causes : la **ressource** reçue et la **taille
du parc** installé. On ne peut donc pas conclure d'une forte production qu'une
région est ensoleillée. C'est pourtant l'erreur commise le 2026-07-26, où les
régions avaient été classées « par ensoleillement » sur la foi de leur production.

Le taux de charge `tch_solaire` rapporte la production à la puissance installée :
il **divise par le parc**. Ce qui reste mesure ce que chaque mégawatt installé
parvient à produire, et approche donc la ressource.

Prédiction enregistrée avant mesure (journal du 2026-07-28)
------------------------------------------------------------
> Le parc installé expliquera l'essentiel des écarts régionaux, la ressource
> assez peu. Attendu : des productions variant d'un facteur proche de 10 entre
> régions, pour un taux de charge ne variant que d'un facteur 1,5 environ.

Limites de cette approche
-------------------------
Le taux de charge n'est **pas** de l'irradiance. Il est contaminé par
l'écrêtement, l'orientation des panneaux, la technologie et l'âge du parc, et
n'existe qu'à partir de 2020. Le détail est dans `docs/dictionnaire_donnees.md`.
L'écrêtement est la réserve la plus gênante : il abaisse le taux de charge sans
baisse d'ensoleillement, et frappe d'abord les régions les plus solaires, donc
son biais joue dans le sens même qu'on cherche à mesurer.

Ce script permet donc de dire **si** la ressource explique une part des écarts,
pas de la quantifier précisément.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et périmètre
import sys
from pathlib import Path

import pandas as pd

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.analyses import annees_incompletes  # noqa: E402
from src.preparation import capacite_installee, charger_donnees  # noqa: E402

df = charger_donnees()
# Le taux de charge n'existe qu'à partir de 2020.
df = df[(df["annee"] >= 2020) & (~df["annee"].isin(annees_incompletes(df)))]
print(f"Période retenue : {df['annee'].min()} à {df['annee'].max()}")

# %% Décomposition : production, ressource et parc, région par région
# Le facteur de charge annuel est la moyenne du taux de charge sur l'année entière,
# nuits comprises. C'est l'indicateur standard du rendement d'un parc.
capacites = capacite_installee(df, "solaire")
capacite_moyenne = capacites.groupby("libelle_region")["capacite_mw"].median()

tableau = pd.DataFrame({
    "production_mw": df.groupby("libelle_region")["solaire"].mean(),
    "facteur_charge_%": df.groupby("libelle_region")["tch_solaire"].mean(),
    "capacite_mw": capacite_moyenne,
}).sort_values("production_mw", ascending=False)
print(tableau.round(1).to_string())

# %% Le test : quelle cause varie le plus entre régions ?
def ecart(colonne: pd.Series) -> float:
    """Rapport entre la plus forte et la plus faible valeur régionale."""
    return colonne.max() / colonne.min()


print("Écart entre la région la plus forte et la plus faible :\n")
for libelle, colonne in [
    ("Production (MW)", "production_mw"),
    ("Parc installé (MW)", "capacite_mw"),
    ("Facteur de charge (%)", "facteur_charge_%"),
]:
    serie = tableau[colonne]
    print(f"  {libelle:<24} facteur {ecart(serie):5.1f}   "
          f"(de {serie.min():.1f} à {serie.max():.1f})")

print("\n  Si le facteur de charge varie beaucoup moins que le parc, alors")
print("  les écarts de production viennent surtout du nombre de panneaux.")

# %% Verdict par rapport à la prédiction enregistrée
facteur_production = ecart(tableau["production_mw"])
facteur_parc = ecart(tableau["capacite_mw"])
facteur_ressource = ecart(tableau["facteur_charge_%"])

print("Prédiction : production autour de 10, facteur de charge autour de 1,5.")
print(f"Mesuré     : production {facteur_production:.1f}, "
      f"parc {facteur_parc:.1f}, facteur de charge {facteur_ressource:.2f}.\n")

# La relation est multiplicative : production = parc x facteur de charge.
# La décomposition doit donc se faire en logarithmes, où les facteurs
# s'additionnent. Une différence de rapports donnerait un résultat faux.
import numpy as np  # noqa: E402

# ⚠️ RETIRÉ le 2026-07-28 après revue. Le calcul ci-dessous normalisait par la
# SOMME DES DEUX LOGARITHMES, et non par le logarithme de l'écart qu'il prétend
# décomposer. Or les trois maxima ne sont pas atteints par les mêmes régions :
# la production et le parc culminent en Nouvelle-Aquitaine, le facteur de charge
# en Provence-Alpes-Côte d'Azur. L'identité ne se transporte donc pas aux
# rapports max/min : 15,265 x 1,377 = 21,0 alors que la production varie de 19,2.
# On l'affiche pour mémoire, on ne le publie plus.
log_parc, log_ressource = np.log(facteur_parc), np.log(facteur_ressource)
part_ressource = log_ressource / (log_parc + log_ressource)
print("Ancienne décomposition, RETIRÉE (normalisation fausse, pour mémoire) :")
print(f"  parc {100 * (1 - part_ressource):.0f} %, ressource {100 * part_ressource:.0f} %")
print(f"  contrôle : log(production) = {np.log(facteur_production):.4f} mais "
      f"log(parc) + log(ressource) = {log_parc + log_ressource:.4f}. "
      "L'identité ne se ferme pas.\n")

# %% Décomposition exacte, qui elle se ferme
# Sur les 12 régions, production = capacité x facteur de charge est vraie région
# par région. En logarithmes, la variance se décompose exactement :
#
#     var(log prod) = var(log parc) + var(log ressource) + 2 cov(log parc, log ressource)
#
# Le terme de covariance n'est pas un résidu à négliger : c'est un résultat en
# soi. Il dit que le parc a été construit là où le soleil est.
regional = tableau.copy()
regional["capacite_effective"] = 100 * regional["production_mw"] / regional["facteur_charge_%"]
lp = np.log(regional["production_mw"])
lc = np.log(regional["capacite_effective"])
lf = np.log(regional["facteur_charge_%"])

variance = lp.var(ddof=0)
v_parc, v_ressource = lc.var(ddof=0), lf.var(ddof=0)
covariance = np.cov(lc, lf, ddof=0)[0, 1]

print("Décomposition EXACTE de la variance des logarithmes (12 régions) :")
print(f"  var(log production)  = {variance:.5f}  "
      f"(contrôle : {v_parc + v_ressource + 2 * covariance:.5f}, l'identité se ferme)")
print(f"  parc installé        : {100 * v_parc / variance:5.1f} %")
print(f"  ressource SEULE      : {100 * v_ressource / variance:5.1f} %")
print(f"  covariance parc x ressource : {100 * 2 * covariance / variance:5.1f} %")
print(f"  corrélation log(parc), log(ressource) : {np.corrcoef(lc, lf)[0, 1]:.3f}")
print()
print("  Lecture : la ressource seule ne pèse presque rien. Ce qui pèse, après")
print("  le parc, c'est le terme croisé, et il dit quelque chose de plus")
print("  intéressant que l'ancien « 10 % de ressource » : le parc a été")
print("  construit là où le soleil est. L'ancien chiffre confondait la")
print("  ressource avec cette covariance.")

# %% Classement par ressource, à comparer au classement par production
comparaison = pd.DataFrame({
    "rang production": tableau["production_mw"].rank(ascending=False).astype(int),
    "rang ressource": tableau["facteur_charge_%"].rank(ascending=False).astype(int),
    "facteur_charge_%": tableau["facteur_charge_%"].round(1),
    "capacite_mw": tableau["capacite_mw"].round(0),
})
comparaison["écart de rang"] = (comparaison["rang production"]
                                - comparaison["rang ressource"])
print(comparaison.sort_values("rang ressource").to_string())
print("\n  Un écart de rang important signale une région dont la place au")
print("  classement de production ne s'explique pas par son ensoleillement.")
