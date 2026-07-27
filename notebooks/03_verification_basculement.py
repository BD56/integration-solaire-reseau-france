"""Vérification : le solaire a-t-il inversé l'ordre de la journée ?

Un premier calcul suggérait qu'en Nouvelle-Aquitaine, la demande nette est
devenue plus basse en milieu de journée que la nuit à partir de 2019. Ce script
soumet ce résultat à quatre contrôles avant d'y croire.

Les quatre contrôles
--------------------
1. **Témoin.** Le phénomène apparaît-il aussi sur la consommation seule ? Si oui,
   il ne doit rien au solaire mais à un changement d'habitudes.
2. **Éolien.** Le résultat change-t-il selon qu'on retire le solaire seul ou le
   solaire et l'éolien ?
3. **Ordre.** Les régions basculent-elles dans l'ordre de leur équipement
   solaire ? Une bascule dans une région peu solaire ruinerait l'explication.
4. **Robustesse.** Le résultat dépend-il des bornes horaires choisies ?

Le quatrième contrôle a **invalidé la mesure initiale** : selon la fenêtre de
nuit retenue, la bascule tombait en 2015, 2016, 2019 ou 2021. Elle est donc
remplacée ici par une mesure **sans borne arbitraire** : l'heure à laquelle se
situe le minimum de la journée. On ne choisit plus rien, on constate.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports
import sys
from pathlib import Path

import pandas as pd

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.analyses import annees_incompletes, profils_par_annee  # noqa: E402
from src.preparation import charger_donnees  # noqa: E402

# %% Chargement, années incomplètes écartées
df = charger_donnees()
df = df[~df["annee"].isin(annees_incompletes(df))]
REGIONS = sorted(df["libelle_region"].unique())
print(f"{len(REGIONS)} régions, {df['annee'].min()} à {df['annee'].max()}")


def heure_du_minimum(donnees, variable):
    """Heure locale du minimum de la journée, année par année.

    Mesure sans paramètre : on ne choisit ni fenêtre de nuit ni fenêtre de midi,
    on cherche simplement le point le plus bas du profil journalier médian.
    """
    profils = profils_par_annee(donnees, variable)
    return {
        annee: groupe.loc[groupe["mediane"].idxmin(), "heure_decimale"]
        for annee, groupe in profils.groupby("annee")
    }


def annee_de_bascule(donnees, variable, plage_midi=(10, 17)):
    """Première année où le minimum de la journée tombe en milieu de journée."""
    for annee, heure in sorted(heure_du_minimum(donnees, variable).items()):
        if plage_midi[0] <= heure <= plage_midi[1]:
            return annee
    return None


# %% Contrôle 1 et 2 : témoin (consommation seule) et rôle de l'éolien
lignes = []
for region in REGIONS:
    base = df[df["libelle_region"] == region]
    recent = base[base["annee"] >= 2023]
    lignes.append({
        "région": region,
        "consommation": annee_de_bascule(base, "consommation"),
        "demande nette": annee_de_bascule(base, "demande_nette"),
        "demande nette solaire": annee_de_bascule(base, "demande_nette_solaire"),
        "couverture %": round(recent["tco_solaire"].mean(), 1),
        "solaire MW": round(recent["solaire"].mean()),
    })

resultats = pd.DataFrame(lignes).sort_values("couverture %", ascending=False)
print(resultats.to_string(index=False))

bascules_conso = resultats["consommation"].notna().sum()
print(f"\nContrôle 1, témoin : la consommation seule bascule dans "
      f"{bascules_conso} région(s) sur {len(REGIONS)}.")
print("  Si ce nombre vaut 0, le phénomène n'apparaît qu'après soustraction du")
print("  solaire, et ne peut donc pas venir d'un changement de consommation.")

identiques = (resultats["demande nette"].fillna(-1)
              == resultats["demande nette solaire"].fillna(-1)).sum()
print(f"\nContrôle 2, éolien : les deux définitions donnent le même verdict pour "
      f"{identiques} région(s) sur {len(REGIONS)}.")

# %% Contrôle 3 : les régions basculent-elles dans l'ordre de leur équipement ?
bascule = resultats.dropna(subset=["demande nette solaire"])
jamais = resultats[resultats["demande nette solaire"].isna()]

print(f"Régions qui basculent      : couverture de "
      f"{bascule['couverture %'].min()} % à {bascule['couverture %'].max()} %")
print(f"Régions qui ne basculent pas : couverture de "
      f"{jamais['couverture %'].min()} % à {jamais['couverture %'].max()} %")
print(f"\nCorrélation entre l'année de bascule et la couverture solaire : "
      f"r = {bascule['demande nette solaire'].corr(bascule['couverture %']):.2f}")
print(f"Corrélation avec la production absolue : "
      f"r = {bascule['demande nette solaire'].corr(bascule['solaire MW']):.2f}")
print("\n  La couverture prédit mieux que la production : l'Auvergne-Rhône-Alpes")
print("  produit beaucoup mais consomme trop pour que ce solaire pèse.")

# %% Contrôle 4 : sensibilité aux bornes, qui a invalidé la mesure initiale
def bascule_avec_fenetres(donnees, variable, midi, nuit):
    """Mesure initiale, dépendante de deux fenêtres choisies à la main."""
    profils = profils_par_annee(donnees, variable)
    for annee, groupe in profils.groupby("annee"):
        creux = groupe[groupe["heure_decimale"].between(*midi)]["mediane"].min()
        niveau_nuit = groupe[groupe["heure_decimale"].between(*nuit)]["mediane"].median()
        if niveau_nuit - creux > 0:
            return annee
    return None


na = df[df["libelle_region"] == "Nouvelle-Aquitaine"]
sensibilite = []
for midi in [(10, 16), (11, 15), (9, 17), (12, 14)]:
    for nuit in [(2, 5), (1, 4), (3, 5), (0, 6)]:
        sensibilite.append({
            "fenêtre midi": f"{midi[0]}-{midi[1]} h",
            "fenêtre nuit": f"{nuit[0]}-{nuit[1]} h",
            "bascule": bascule_avec_fenetres(na, "demande_nette_solaire", midi, nuit),
        })
sensibilite = pd.DataFrame(sensibilite)
print(sensibilite.to_string(index=False))
print(f"\nLa mesure initiale donne {sensibilite['bascule'].nunique()} années "
      f"différentes selon les fenêtres : {sorted(sensibilite['bascule'].unique())}.")
print("C'est pourquoi elle est écartée au profit de l'heure du minimum, qui ne")
print("dépend d'aucune borne.")

# %% Résultat : l'heure du minimum, année par année
table = pd.DataFrame({r: heure_du_minimum(df[df["libelle_region"] == r],
                                          "demande_nette_solaire")
                      for r in REGIONS}).T
table.index.name = "région"
print("Heure locale du minimum de la demande nette médiane :\n")
print(table.round(0).to_string())
print("\n  Un minimum vers 4-5 h est l'ordre attendu.")
print("  Un minimum vers 14-16 h signifie que le milieu de journée est devenu")
print("  le moment le plus creux.")

# %% Stabilité : la bascule tient-elle, ou hésite-t-elle ?
print("Une fois basculée, la région le reste-t-elle ?\n")
for region in bascule["région"]:
    heures = heure_du_minimum(df[df["libelle_region"] == region], "demande_nette_solaire")
    depuis = int(bascule.loc[bascule["région"] == region, "demande nette solaire"].iloc[0])
    apres = [a for a in sorted(heures) if a >= depuis]
    retours = [a for a in apres if not (10 <= heures[a] <= 17)]
    verdict = "durable" if not retours else f"instable, retours en {retours}"
    print(f"  {region:<28} bascule en {depuis} : {verdict}")
