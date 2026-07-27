"""Figures de vitrine : profils journaliers de demande nette.

Ce script **ne calcule rien lui-même** : il appelle `src/analyses.py`, comme le
tableau de bord, afin que les deux ne puissent pas diverger. Son rôle est de
produire les images fixes destinées au README et au dépôt, que le tableau de
bord ne fournit pas puisqu'il faut le lancer pour voir quoi que ce soit.

Répartition des rôles :

- **tableau de bord** (`app/tableau_bord.py`) : explorer, toutes régions, toutes
  variables, interactif ;
- **ce script** : figer quelques figures représentatives, visibles directement
  sur GitHub sans rien exécuter.

Choix de cadrage, identiques à ceux du tableau de bord :

- pas d'agrégat national, l'écart entre régions étant l'objet d'intérêt ;
- deux régions contrastées, Nouvelle-Aquitaine (couverture solaire moyenne
  d'environ 16 %) et Hauts-de-France (environ 2 %), aux consommations
  comparables, ce qui rend la comparaison honnête ;
- années incomplètes écartées, sans quoi les saisons seraient déséquilibrées ;
- médiane, moyenne et éventail de quantiles tracés ensemble : un réseau se
  dimensionne sur le jour le plus contraignant, pas sur le jour moyen.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et paramètres
import sys
from pathlib import Path

import matplotlib.pyplot as plt

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.analyses import (  # noqa: E402
    annees_incompletes,
    profils_par_annee,
    profils_saisonniers,
    profondeur_creux,
)
from src.graphiques import ENCRE, ENCRE_SECONDAIRE, GRILLE  # noqa: E402
from src.preparation import SAISONS, charger_donnees, filtrer  # noqa: E402

REGIONS = ["Nouvelle-Aquitaine", "Hauts-de-France"]
ANNEES = (2023, 2025)
VARIABLE = "demande_nette"

COULEUR_REGION = {"Nouvelle-Aquitaine": "#2a78d6", "Hauts-de-France": "#eb6834"}
DOSSIER = RACINE / "figures"
DOSSIER.mkdir(exist_ok=True)


def style_axe(ax):
    """Grille et axes discrets : les données priment sur le décor."""
    ax.grid(True, axis="y", color=GRILLE, linewidth=0.8)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        ax.spines[cote].set_color("#d5d4cf")
    ax.tick_params(colors=ENCRE_SECONDAIRE, labelsize=9)
    ax.set_xlim(0, 23.5)
    ax.set_xticks([0, 6, 12, 18])
    ax.set_xticklabels(["0 h", "6 h", "12 h", "18 h"])


def teinte_annee(part: float) -> tuple:
    """Rampe ambre du clair au foncé, pour une grandeur ordonnée comme l'année."""
    etapes = [(0.0, (247, 223, 160)), (0.55, (237, 161, 0)), (1.0, (94, 62, 0))]
    for (p0, c0), (p1, c1) in zip(etapes, etapes[1:]):
        if part <= p1:
            t = (part - p0) / (p1 - p0) if p1 > p0 else 0
            return tuple((a + (z - a) * t) / 255 for a, z in zip(c0, c1))
    return (94 / 255, 62 / 255, 0)


# %% Chargement, via la même source que le tableau de bord
df = charger_donnees()
peri = filtrer(df, regions=REGIONS, annees=ANNEES)
print(f"Périmètre : {len(peri):,} lignes, {ANNEES[0]} à {ANNEES[1]}")

# %% Figure 1 : profils par saison, grille régions x saisons
fig, axes = plt.subplots(len(REGIONS), len(SAISONS), figsize=(15, 7),
                         sharex=True, sharey=True)

for i, region in enumerate(REGIONS):
    couleur = COULEUR_REGION[region]
    profils = profils_saisonniers(peri[peri["libelle_region"] == region], VARIABLE)
    for j, saison in enumerate(SAISONS):
        ax = axes[i, j]
        p = profils[profils["saison"] == saison].sort_values("heure_decimale")
        h = p["heure_decimale"]

        ax.fill_between(h, p["d10"], p["d90"], color=couleur, alpha=0.16, linewidth=0)
        ax.fill_between(h, p["q25"], p["q75"], color=couleur, alpha=0.32, linewidth=0)
        ax.plot(h, p["mediane"], color=couleur, linewidth=2, label="Médiane")
        ax.plot(h, p["moyenne"], color=ENCRE, linewidth=1.2,
                linestyle=(0, (4, 3)), label="Moyenne")

        style_axe(ax)
        if i == 0:
            ax.set_title(saison, fontsize=11, color=ENCRE, pad=8)
        if j == 0:
            ax.set_ylabel(f"{region}\nDemande nette (MW)", fontsize=10, color=ENCRE)

axes[0, 0].legend(frameon=False, fontsize=9, loc="lower left",
                  labelcolor=ENCRE_SECONDAIRE)
fig.suptitle(f"Demande nette au fil de la journée, par saison "
             f"({ANNEES[0]} à {ANNEES[1]})", fontsize=13, color=ENCRE, y=0.98)
fig.text(0.5, 0.005,
         "Trait plein : médiane. Tirets : moyenne. Bandes : quartiles (q25 à q75) "
         "et déciles (d10 à d90). Heure locale.",
         ha="center", fontsize=9, color=ENCRE_SECONDAIRE)
fig.tight_layout(rect=(0, 0.03, 1, 0.96))
fig.savefig(DOSSIER / "01_profils_saisonniers.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()

# %% Figure 2 : évolution année par année (sous-question 2)
fig, axes = plt.subplots(1, len(REGIONS), figsize=(14, 5), sharey=False)

for ax, region in zip(axes, REGIONS):
    base = df[df["libelle_region"] == region]
    base = base[~base["annee"].isin(annees_incompletes(base))]
    par_annee = profils_par_annee(base, VARIABLE)
    annees = sorted(par_annee["annee"].unique())

    for rang, annee in enumerate(annees):
        p = par_annee[par_annee["annee"] == annee].sort_values("heure_decimale")
        ax.plot(p["heure_decimale"], p["mediane"], linewidth=1.8,
                color=teinte_annee(rang / max(len(annees) - 1, 1)),
                label=str(annee) if annee in (annees[0], annees[-1]) else None)

    style_axe(ax)
    ax.set_title(region, fontsize=11, color=ENCRE)
    ax.set_xlabel("Heure locale", fontsize=10, color=ENCRE_SECONDAIRE)
    ax.set_ylabel("Demande nette médiane (MW)", fontsize=10, color=ENCRE)
    ax.legend(frameon=False, fontsize=9, labelcolor=ENCRE_SECONDAIRE)

fig.suptitle(f"Déformation de la demande nette, {annees[0]} à {annees[-1]}",
             fontsize=13, color=ENCRE)
fig.text(0.5, 0.005,
         "Une courbe par année, du clair (ancien) au foncé (récent). "
         "Années incomplètes écartées.",
         ha="center", fontsize=9, color=ENCRE_SECONDAIRE)
fig.tight_layout(rect=(0, 0.04, 1, 0.94))
fig.savefig(DOSSIER / "02_evolution_annuelle.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()

# %% Indicateurs chiffrés, mêmes définitions que le tableau de bord
for region in REGIONS:
    base = df[df["libelle_region"] == region]
    base = base[~base["annee"].isin(annees_incompletes(base))]
    print(f"\n=== {region} ===")
    print(profondeur_creux(base, VARIABLE).round(0).to_string(index=False))

# %% Figure 3 : une journée réelle, en complément illustratif
jour = peri[
    (peri["libelle_region"] == "Nouvelle-Aquitaine")
    & (peri["date_heure_locale"].dt.date.astype(str) == "2024-06-21")
].sort_values("heure_decimale")

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(jour["heure_decimale"], jour["consommation"], color=ENCRE_SECONDAIRE,
        linewidth=2, label="Consommation")
ax.plot(jour["heure_decimale"], jour["demande_nette"], color="#2a78d6",
        linewidth=2, label="Demande nette")
ax.fill_between(jour["heure_decimale"], jour["demande_nette"], jour["consommation"],
                color="#eda100", alpha=0.30, linewidth=0,
                label="Effacé par le solaire et l'éolien")
style_axe(ax)
ax.set_title("Nouvelle-Aquitaine, 21 juin 2024", fontsize=12, color=ENCRE)
ax.set_xlabel("Heure locale", fontsize=10, color=ENCRE_SECONDAIRE)
ax.set_ylabel("Puissance (MW)", fontsize=10, color=ENCRE)
ax.legend(frameon=False, fontsize=9, labelcolor=ENCRE_SECONDAIRE)
fig.tight_layout()
fig.savefig(DOSSIER / "03_journee_illustration.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()
