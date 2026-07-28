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
CLES = ["date_heure", "date", "annee", "heure_decimale"]
national = df.groupby(CLES, as_index=False)[COLONNES].sum()

# `sum()` de pandas ignore les NaN : un créneau où une région manque est sommé
# sur 11 régions et non 12, ce qui fabrique un creux artificiel de plusieurs
# gigawatts. Cela concerne les 96 lignes de 2013 sans éolien (deux journées,
# Centre-Val de Loire et Île-de-France), dont 22 tombent dans la fenêtre du soir.
#
# ⚠️ Le remède doit être appliqué COLONNE PAR COLONNE. Un `min_count=12` global
# effacerait `pompage` et `nucleaire` sur toute la période antérieure à 2021, où
# une case vide ne signifie pas « mesure manquante » mais « pas de centrale dans
# cette région ». Seule `demande_nette` est concernée, l'éolien y entrant.
complet = df.groupby(CLES)["demande_nette"].count() == df["libelle_region"].nunique()
national = national.merge(complet.rename("douze_regions").reset_index(), on=CLES)
national.loc[~national["douze_regions"], "demande_nette"] = np.nan
print(f"  {(~national['douze_regions']).sum()} pas de temps écartés de la demande "
      "nette nationale (moins de 12 régions renseignées).")
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

# %% H1 et H3, témoin saisonnier : le déplacement vient-il vraiment du solaire ?
# Ajouté le 2026-07-28 après revue. H1 et H3 sont des corrélations contre l'année
# sur treize points : elles établissent une régularité, pas une cause. Le témoin
# saisonnier, lui, n'est pas une corrélation contre l'année : si le solaire est
# la cause, l'effet doit être fort en été et faible en hiver.


def profil_saisonnier(colonne: str, mois: list[int]) -> pd.DataFrame:
    part = national[pd.to_datetime(national["date"]).dt.month.isin(mois)]
    return part.pivot_table(index="annee", columns="heure_decimale",
                            values=colonne, aggfunc="mean")


print("=== H1 et H3 : témoin saisonnier ===")
for libelle, mois in [("été  ", [6, 7, 8]), ("hiver", [12, 1, 2])]:
    pompe = profil_saisonnier("pompage", mois).abs()
    midi = entre(pompe, MI_JOURNEE)
    nuc = profil_saisonnier("nucleaire", mois)
    rapport_nuc = entre(nuc, MI_JOURNEE) / entre(nuc, NUIT)
    print(f"  {libelle} | pompage de mi-journée ×{midi.iloc[-1] / midi.iloc[0]:.2f} "
          f"| rapport nucléaire midi/nuit {rapport_nuc.iloc[0]:.4f} -> "
          f"{rapport_nuc.iloc[-1]:.4f}")

print("  ⚠️ H3 passe ce témoin : le nucléaire ne module qu'en été.")
print("     H1 NE LE PASSE PAS : le pompage se déplace aussi en hiver, où le")
print("     solaire ne peut presque rien. H1 reste vraie comme constat, mais son")
print("     attribution au solaire est la MOINS établie des trois, alors que le")
print("     journal la présentait comme le résultat le plus net.")

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
#
# ⚠️ CORRIGÉ le 2026-07-28 après revue. La version publiée appliquait `.diff()`
# à la trame DÉJÀ FILTRÉE sur la fenêtre du soir. La première variation de chaque
# soirée comparait donc le créneau 21:00 de la veille au 16:00 du jour, un saut
# de dix-neuf heures qui entrait dans le maximum journalier : il en portait le
# maximum dans 13,80 % des journées, et son ampleur décroissant avec les années
# (+868 MW en 2013, +60 MW en 2025), il inclinait la tendance.
#
# Le verdict en dépendait entièrement : r = −0,453 (rejetée, et de sens
# contraire) devient r = +0,892 (VALIDÉE). Borner le `.diff()` à la journée est
# la correction.


def rampe_du_soir(trame: pd.DataFrame, bornes=SOIREE, colonne="demande_nette") -> pd.Series:
    """Variation maximale par demi-heure en soirée, médiane par année.

    Le `.diff()` est calculé **par journée** (`groupby("date")`), sans quoi il
    enjambe la nuit et compare deux jours différents.
    """
    fenetre = trame[trame["heure_decimale"].between(*bornes)].sort_values("date_heure").copy()
    fenetre["variation"] = fenetre.groupby("date", observed=True)[colonne].diff()
    return fenetre.groupby(["annee", "date"])["variation"].max().groupby("annee").median()


rampe = rampe_du_soir(national)

print("=== H4 : la remontée du soir s'accélère-t-elle ? ===")
print(pd.DataFrame({"rampe médiane du soir (MW par demi-heure)": rampe.round(0)}).to_string())
h4 = verdict(rampe.index, rampe.values, +1,
             "H4, rampe maximale de soirée")

# %% H4, contrôle 1 : sensibilité aux bornes de la fenêtre du soir
# Règle de méthode du projet : une mesure qui dépend de bornes choisies à la main
# doit voir ses bornes varier avant publication.
print("=== H4, sensibilité aux bornes ===")
for bornes in [(16, 21), (17, 22), (15, 21), (16, 22), (17, 21), (18, 22), (14, 23)]:
    r_test = rampe_du_soir(national, bornes)
    print(f"  {bornes} : r = {np.corrcoef(r_test.index, r_test.values)[0, 1]:+.3f}")
print("  ⚠️ Cinq fenêtres sur sept donnent exactement +0,892 et une le renforce,")
print("     mais la plus large (14-23 h) change de signe. À citer avec H4.")

# %% H4, contrôle 2 : le témoin qui écarte l'électrification des usages
# Une rampe du soir qui s'accélère pourrait venir de la croissance de la pointe
# ou de l'électrification, pas du solaire. Deux témoins départagent.
#
# Témoin A : la consommation BRUTE, sur laquelle le solaire n'agit pas.
# Témoin B : quasi-expérience saisonnière. Ce n'est pas une corrélation contre
#            l'année, donc pas la même faiblesse : l'effet doit être présent là
#            où le solaire peut agir (été) et absent où il ne le peut pas (hiver).
print("=== H4, contrôle par témoin ===")
rampe_conso = rampe_du_soir(national, colonne="consommation")
print(f"  demande nette   : r = {np.corrcoef(rampe.index, rampe.values)[0, 1]:+.3f} "
      f"({rampe.iloc[0]:.0f} -> {rampe.iloc[-1]:.0f} MW)")
print(f"  consommation    : r = "
      f"{np.corrcoef(rampe_conso.index, rampe_conso.values)[0, 1]:+.3f} "
      f"({rampe_conso.iloc[0]:.0f} -> {rampe_conso.iloc[-1]:.0f} MW)")

for saison, mois in [("été", [6, 7, 8]), ("hiver", [12, 1, 2])]:
    part = national[pd.to_datetime(national["date"]).dt.month.isin(mois)]
    r_nette = rampe_du_soir(part)
    r_conso = rampe_du_soir(part, colonne="consommation")
    print(f"  {saison:6s} demande nette r = "
          f"{np.corrcoef(r_nette.index, r_nette.values)[0, 1]:+.3f} | "
          f"consommation r = {np.corrcoef(r_conso.index, r_conso.values)[0, 1]:+.3f}")

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
