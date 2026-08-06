"""Sous-question 1 : la journée type de demande nette, et sa déformation saisonnière.

Ce script exécute le protocole écrit **avant tout calcul** au journal du
2026-07-29. Il ne le redéfinit pas et ne l'assouplit pas.

Pourquoi ce script existe
-------------------------
La sous-question 1 n'était pas une question mais un **sujet** : « dynamique
journalière, creux de mi-journée, remontée du soir, déformation saisonnière ».
Pas de verbe, rien à trancher, donc rien qui puisse se refermer. Elle est restée
ouverte pendant que les sous-questions 2 et 3 se refermaient, non par manque de
travail mais par défaut de formulation.

Reformulation retenue
---------------------
**Question affichée (A)** : à quoi ressemble une journée type de demande nette,
et comment cette forme se déforme-t-elle selon la saison ?

A reste non refermable par nature. Ce sont les deux suivantes qui portent la
condition de clôture, et elles seules sont préenregistrées :

**(B)** Le creux de mi-journée est-il du même ordre en été et en hiver, ou le
solaire déforme-t-il la journée différemment selon la saison ?

**(C)** Cette déformation dépend-elle davantage de la **saison** ou de la
**région** ?

Critères, fixés d'avance
------------------------
**B** : rapport été / hiver de la déformation, médiane sur les 12 régions.

    >= 2    -> fortement saisonnière
    1,2 à 2 -> modérément saisonnière
    < 1,2   -> non saisonnière

Ces bornes sont un choix assumé. L'**étalon rapporté à côté n'est pas
arbitraire** : le rapport été / hiver de la production solaire elle-même.

**C** : décomposition de la variance sur le plan région × saison. Aucun seuil,
le facteur qui explique le plus l'emporte. L'interaction est rapportée, pas
absorbée.

**Prédiction enregistrée avant calcul** : la saison domine la région. Si le
calcul dit l'inverse, c'est un résultat, pas une erreur.

Ce que ce script ne fait pas
----------------------------
Il ne cherche pas **pourquoi** telle région se distingue. Cela exige une source
météorologique et appartient à la phase 2.

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

from src.analyses import (  # noqa: E402
    decomposition_saison_region,
    deformation_solaire,
    profils_saisonniers,
    rapport_saisonnier,
)
from src.preparation import charger_donnees  # noqa: E402

# Période figée au protocole : années complètes, parc solaire déjà important, et
# fenêtre assez courte pour que sa croissance ne domine pas (cette croissance est
# le sujet de la sous-question 2, pas de la 1).
ANNEES = range(2021, 2026)

SEUIL_FORT, SEUIL_FAIBLE = 2.0, 1.2

df = charger_donnees()
peri = df[df["annee"].isin(ANNEES)]
print(f"Périmètre : {len(peri):,} lignes, "
      f"{peri['annee'].min()} à {peri['annee'].max()}, "
      f"{peri['libelle_region'].nunique()} régions".replace(",", " "))

# %% A : à quoi ressemble une journée type, saison par saison
# Niveau descriptif. Il ouvre la question, il ne la referme pas.
region_temoin = "Nouvelle-Aquitaine"
profils = profils_saisonniers(peri[peri["libelle_region"] == region_temoin],
                              "demande_nette_solaire")
apercu = (
    profils.groupby("saison", observed=True)
    .apply(lambda p: pd.Series({
        "creux de mi-journée (MW)": p[p["heure_decimale"].between(10, 16)]["mediane"].min(),
        "niveau de nuit (MW)": p[p["heure_decimale"].between(2, 5)]["mediane"].median(),
        "pic du soir (MW)": p[p["heure_decimale"].between(18, 21)]["mediane"].max(),
    }), include_groups=False)
)
print(f"=== A : journée type en {region_temoin}, demande nette ===")
print(apercu.round(0).to_string())

# %% La grandeur mesurée : la déformation attribuable au solaire
# Comparer des creux entre saisons serait trompeur, la consommation hivernale
# étant bien plus élevée. On mesure donc une différence entre deux profils de la
# même journée, la consommation brute servant de témoin insensible au solaire.
deformation = deformation_solaire(peri)
print("=== Déformation attribuable au solaire (MW), par région et saison ===")
print(deformation.pivot(index="libelle_region", columns="saison",
                        values="deformation").round(0).to_string())

# %% B : la déformation est-elle saisonnière ?
comparaison = rapport_saisonnier(deformation)
print("=== B : rapport été / hiver, par région ===")
print(comparaison[["deformation_ete", "deformation_hiver", "rapport_deformation",
                   "rapport_solaire", "ecart_a_l_etalon"]].round(2).to_string())

mediane_b = comparaison["rapport_deformation"].median()
etalon_b = comparaison["rapport_solaire"].median()
if mediane_b >= SEUIL_FORT:
    verdict_b = "FORTEMENT SAISONNIÈRE"
elif mediane_b >= SEUIL_FAIBLE:
    verdict_b = "MODÉRÉMENT SAISONNIÈRE"
else:
    verdict_b = "NON SAISONNIÈRE"

print("=" * 70)
print("CRITÈRE B")
print(f"  rapport été / hiver de la déformation, médiane : {mediane_b:.2f}")
print(f"  -> {verdict_b}")
print(f"  étalon, rapport été / hiver du solaire        : {etalon_b:.2f}")
print("  Si les deux coïncident, la déformation est simplement")
print("  proportionnelle à la ressource. Sinon, quelque chose l'amplifie")
print("  ou l'amortit, et il faut le dire.")
print("=" * 70)

# %% C : la saison ou la région ?
parts = decomposition_saison_region(deformation)
print("=" * 70)
print("CRITÈRE C : décomposition de la variance")
print(f"  part de la SAISON      : {parts['part_saison_%']:5.1f} %")
print(f"  part de la RÉGION      : {parts['part_region_%']:5.1f} %")
print(f"  part de l'INTERACTION  : {parts['part_interaction_%']:5.1f} %")
print(f"  contrôle, somme        : {parts['controle_somme_%']:5.1f} %")
print(f"  -> facteur dominant : {parts['facteur_dominant'].upper()}")
print("  Prédiction enregistrée avant calcul : la saison domine.")
print("=" * 70)

# %% Contrôle des bornes, imposé par la règle du projet
# Une mesure qui dépend de fenêtres choisies à la main doit voir ces fenêtres
# varier avant publication. Les trois plages viennent de `profondeur_creux`.
print("=== Sensibilité aux fenêtres horaires ===")
for nuit, midi in [((2, 5), (10, 16)), ((1, 5), (11, 15)), ((2, 4), (10, 15)),
                   ((3, 5), (11, 16)), ((0, 5), (9, 17))]:
    d = deformation_solaire(peri, nuit=nuit, midi=midi)
    c = rapport_saisonnier(d)
    p = decomposition_saison_region(d)
    print(f"  nuit {nuit}, midi {midi} : rapport B = "
          f"{c['rapport_deformation'].median():.2f} | "
          f"saison {p['part_saison_%']:.0f} % contre région {p['part_region_%']:.0f} %")

# %% Contrôle de robustesse : l'autre définition de la demande nette
# Le journal du 2026-07-26 reprochait de n'avoir employé qu'une seule des deux.
print("=== Robustesse : demande nette solaire ET éolien ===")
d_eolien = deformation_solaire(peri, variable="demande_nette")
c_eolien = rapport_saisonnier(d_eolien)
p_eolien = decomposition_saison_region(d_eolien)
print(f"  rapport B = {c_eolien['rapport_deformation'].median():.2f} | "
      f"saison {p_eolien['part_saison_%']:.0f} % contre "
      f"région {p_eolien['part_region_%']:.0f} %")
print("  L'éolien étant plus fort en hiver, il doit ABAISSER le rapport B.")
