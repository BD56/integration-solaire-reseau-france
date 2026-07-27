"""Brouillon visuel : regarder les données sans hypothèse préalable.

Ce script n'est pas un livrable. Il sert à **voir** ce que les tableaux de
statistiques ne montrent pas : formes, discontinuités, anomalies. Les figures y
sont volontairement peu commentées, elles ne sont pas destinées à un lecteur
extérieur.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et réglages
import sys
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.preparation import charger_donnees  # noqa: E402

ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"

# Rampe séquentielle : une seule teinte, du clair au foncé. Les valeurs absentes
# apparaissent en gris, pour que les trous se voient au lieu de se fondre.
RAMPE_SOLAIRE = LinearSegmentedColormap.from_list(
    "solaire", ["#fdfbf6", "#f7dfa0", "#eda100", "#8a5c00"]
)
RAMPE_SOLAIRE.set_bad("#d9d8d4")

# %% Chargement
df = charger_donnees(verbeux=False)


def grille_horaire(donnees, variable="solaire"):
    """Tableau heure locale x date : une case par relevé, sans agrégation."""
    g = donnees.pivot_table(index="heure_decimale", columns="date", values=variable,
                            aggfunc="mean")
    return g.reindex(sorted(g.columns), axis=1)


def tracer_carte(ax, grille, titre, vmax=None, annees=True):
    """Trace une grille en carte de chaleur, échelle de couleur imposable."""
    dates = [mdates.date2num(d) for d in grille.columns.astype("datetime64[ns]")]
    image = ax.imshow(
        grille.to_numpy(), aspect="auto", origin="lower", cmap=RAMPE_SOLAIRE,
        extent=(dates[0], dates[-1], 0, 24), interpolation="nearest",
        vmin=0, vmax=vmax,
    )
    ax.set_xlim(dates[0], dates[-1])   # sinon l'axe déborde au-delà des données
    ax.set_yticks([0, 6, 12, 18, 24])
    ax.set_yticklabels(["0 h", "6 h", "12 h", "18 h", "24 h"])
    if annees:
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.set_xticks([])
    ax.tick_params(colors=ENCRE_SECONDAIRE, labelsize=8)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    ax.set_title(titre, fontsize=10, color=ENCRE)
    return image


def dater_derniere_ligne(axes):
    """N'affiche les années que sur la rangée du bas, pour alléger la grille."""
    for ax in axes[-1]:
        ax.xaxis.set_major_locator(mdates.YearLocator(3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


# %% National : les 12 régions additionnées
national = (
    df.groupby(["date", "heure_decimale"], as_index=False)["solaire"].sum()
)
grille_nat = grille_horaire(national)
print(f"{grille_nat.shape[0]} créneaux x {grille_nat.shape[1]} jours "
      f"= {grille_nat.size:,} cases")

fig, ax = plt.subplots(figsize=(15, 5))
image = tracer_carte(ax, grille_nat, "Production solaire nationale, une case par relevé de 30 minutes")
ax.set_ylabel("Heure locale", fontsize=10, color=ENCRE)
barre = fig.colorbar(image, ax=ax, pad=0.01)
barre.set_label("MW", fontsize=9, color=ENCRE_SECONDAIRE)
barre.ax.tick_params(colors=ENCRE_SECONDAIRE, labelsize=9)
fig.tight_layout()
plt.show()

# %% Les 12 régions, ÉCHELLE COMMUNE : montre la disparité réelle des niveaux
regions = sorted(df["libelle_region"].unique())
grilles = {r: grille_horaire(df[df["libelle_region"] == r]) for r in regions}
maximum = max(np.nanmax(g.to_numpy()) for g in grilles.values())
print(f"maximum toutes régions confondues : {maximum:.0f} MW")

fig, axes = plt.subplots(4, 3, figsize=(15, 11))
for ax, region in zip(axes.flat, regions):
    image = tracer_carte(ax, grilles[region], region, vmax=maximum, annees=False)
dater_derniere_ligne(axes)
fig.suptitle("Production solaire par région, échelle de couleur commune",
             fontsize=13, color=ENCRE)
fig.colorbar(image, ax=axes, pad=0.01, shrink=0.6, label="MW")
plt.show()

# %% Les 12 régions, ÉCHELLE PROPRE : montre la forme de chacune
fig, axes = plt.subplots(4, 3, figsize=(15, 11))
for ax, region in zip(axes.flat, regions):
    g = grilles[region]
    tracer_carte(ax, g, f"{region}  (max {np.nanmax(g.to_numpy()):.0f} MW)", annees=False)
dater_derniere_ligne(axes)
fig.suptitle("Production solaire par région, échelle propre à chaque région",
             fontsize=13, color=ENCRE)
fig.tight_layout(rect=(0, 0, 1, 0.96))
plt.show()
