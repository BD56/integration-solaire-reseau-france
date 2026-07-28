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

log_parc, log_ressource = np.log(facteur_parc), np.log(facteur_ressource)
part_ressource = log_ressource / (log_parc + log_ressource)
print(f"Décomposition logarithmique de l'écart de production :")
print(f"  parc installé : {100 * (1 - part_ressource):4.0f} %")
print(f"  ressource     : {100 * part_ressource:4.0f} %")

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
