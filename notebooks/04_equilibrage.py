"""Sous-question 3 : comment le système absorbe le solaire, puis compense sa chute.

Méthode
-------
Quatre hypothèses, **écrites avec leur critère de validation avant tout calcul**,
pour qu'aucun critère ne puisse être assoupli après avoir vu le résultat. Les
hypothèses rejetées restent dans ce fichier : un rejet est un résultat, et les
effacer reviendrait à ne garder que ce qui arrange.

Critère commun, fixé à l'avance
-------------------------------
Chaque hypothèse porte sur une tendance au fil des années, mesurée par la
corrélation entre l'indicateur et l'année :

- **validée**   si |r| > 0,7 dans le sens prédit ;
- **rejetée**   si |r| < 0,3, ou si le sens est contraire à la prédiction ;
- **indécise**  entre les deux.

Pourquoi au niveau national
---------------------------
À l'échelle régionale, `ech_physiques` ne mesure pas un équilibrage : une région
n'a aucune obligation de s'équilibrer, elle évacue son solde chez la voisine.
En additionnant les 12 régions, les flux entre régions s'annulent deux à deux et
il ne reste que le solde de la France avec l'étranger. Les mégawatts
s'additionnant, l'agrégation est légitime.

Ce que ce script ne fait pas
----------------------------
Aucune régression, aucune relation supposée linéaire. Uniquement des profils
horaires et des maxima, qui ne demandent aucune hypothèse de forme.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et données nationales
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.analyses import annees_incompletes  # noqa: E402
from src.preparation import charger_donnees  # noqa: E402

SEUIL_VALIDE, SEUIL_REJETE = 0.7, 0.3
MI_JOURNEE, NUIT, SOIREE = (11, 15), (2, 5), (16, 21)

df = charger_donnees()
df = df[~df["annee"].isin(annees_incompletes(df))]

COLONNES = ["solaire", "consommation", "demande_nette", "pompage",
            "ech_physiques", "nucleaire", "hydraulique", "thermique"]
national = (
    df.groupby(["date_heure", "date", "annee", "heure_decimale"], as_index=False)[COLONNES]
    .sum()
)
print(f"{len(national):,} pas de temps nationaux, "
      f"{national['annee'].min()} à {national['annee'].max()}".replace(",", " "))


def verdict(annees, valeurs, sens_attendu: int, libelle: str) -> dict:
    """Applique le critère fixé à l'avance. `sens_attendu` vaut +1 ou -1."""
    r = float(np.corrcoef(annees, valeurs)[0, 1])
    bon_sens = np.sign(r) == sens_attendu
    if abs(r) > SEUIL_VALIDE and bon_sens:
        etat = "VALIDÉE"
    elif abs(r) < SEUIL_REJETE or not bon_sens:
        etat = "REJETÉE"
    else:
        etat = "INDÉCISE"
    print(f"\n  {libelle}")
    print(f"  r = {r:+.2f}   sens attendu : {'croissant' if sens_attendu > 0 else 'décroissant'}"
          f"   ->   {etat}")
    return {"r": r, "etat": etat}


def moyenne_par_heure(colonne: str) -> pd.DataFrame:
    """Profil horaire moyen, une ligne par année."""
    return national.pivot_table(index="annee", columns="heure_decimale",
                                values=colonne, aggfunc="mean")


def entre(profil: pd.DataFrame, bornes: tuple) -> pd.Series:
    """Moyenne du profil sur une plage horaire."""
    colonnes = [h for h in profil.columns if bornes[0] <= h <= bornes[1]]
    return profil[colonnes].mean(axis=1)


# %% H1 : le pompage s'est-il déplacé de la nuit vers la mi-journée ?
# Prédiction : historiquement on pompait la nuit, avec le surplus nucléaire.
# Si le solaire crée un surplus de mi-journée, le pompage doit s'y déplacer.
# Validée si la part du pompage effectuée en mi-journée croît (sens attendu : +1).
profil_pompage = moyenne_par_heure("pompage").abs()   # le pompage est négatif
part_midi = entre(profil_pompage, MI_JOURNEE) / profil_pompage.mean(axis=1)

print("=== H1 : le pompage se déplace-t-il vers la mi-journée ? ===")
apercu = pd.DataFrame({
    "pompage mi-journée (MW)": entre(profil_pompage, MI_JOURNEE).round(0),
    "pompage nuit (MW)": entre(profil_pompage, NUIT).round(0),
    "part de la mi-journée": part_midi.round(3),
    "heure du maximum": profil_pompage.idxmax(axis=1),
})
print(apercu.to_string())
h1 = verdict(part_midi.index, part_midi.values, +1,
             "H1, part du pompage effectuée en mi-journée")

# %% H2 : les échanges évacuent-ils le surplus de mi-journée ?
# Prédiction : la France exporte de plus en plus à midi (ech_physiques < 0).
# Validée si l'export de mi-journée croît, donc si ech_physiques décroît (-1).
profil_echanges = moyenne_par_heure("ech_physiques")
echanges_midi = entre(profil_echanges, MI_JOURNEE)

print("=== H2 : les échanges évacuent-ils le surplus de mi-journée ? ===")
print(pd.DataFrame({
    "échanges mi-journée (MW)": echanges_midi.round(0),
    "échanges nuit (MW)": entre(profil_echanges, NUIT).round(0),
}).to_string())
print("\n  Rappel de convention : négatif = la France exporte.")
h2 = verdict(echanges_midi.index, echanges_midi.values, -1,
             "H2, solde des échanges en mi-journée")

# %% H3 : le nucléaire module-t-il, ou reste-t-il en base ?
# Prédiction : s'il suit le solaire, il doit produire relativement moins à midi.
# Validée si le rapport mi-journée sur nuit décroît (-1).
profil_nucleaire = moyenne_par_heure("nucleaire")
rapport = entre(profil_nucleaire, MI_JOURNEE) / entre(profil_nucleaire, NUIT)

print("=== H3 : le nucléaire module-t-il ? ===")
print(pd.DataFrame({
    "nucléaire mi-journée (MW)": entre(profil_nucleaire, MI_JOURNEE).round(0),
    "nucléaire nuit (MW)": entre(profil_nucleaire, NUIT).round(0),
    "rapport midi / nuit": rapport.round(3),
}).to_string())
h3 = verdict(rapport.index, rapport.values, -1,
             "H3, rapport nucléaire mi-journée sur nuit")

# %% H4 : la remontée du soir devient-elle plus brutale ?
# Prédiction : le système doit remonter sa production de plus en plus vite.
# Validée si la variation maximale de demande nette en soirée croît (+1).
soir = national[national["heure_decimale"].between(*SOIREE)].sort_values("date_heure")
soir = soir.assign(variation=soir["demande_nette"].diff())
rampe = soir.groupby(["annee", "date"])["variation"].max().groupby("annee").median()

print("=== H4 : la remontée du soir s'accélère-t-elle ? ===")
print(pd.DataFrame({"rampe médiane du soir (MW par demi-heure)": rampe.round(0)}).to_string())
h4 = verdict(rampe.index, rampe.values, +1,
             "H4, rampe maximale de soirée")

# %% Récapitulatif des quatre verdicts
recap = pd.DataFrame([
    {"hypothèse": "H1, le pompage se déplace vers la mi-journée", **h1},
    {"hypothèse": "H2, les échanges évacuent le surplus de midi", **h2},
    {"hypothèse": "H3, le nucléaire module", **h3},
    {"hypothèse": "H4, la remontée du soir s'accélère", **h4},
])
print(recap.to_string(index=False))
print(f"\nCritères fixés avant calcul : validée si |r| > {SEUIL_VALIDE}, "
      f"rejetée si |r| < {SEUIL_REJETE} ou sens contraire.")
