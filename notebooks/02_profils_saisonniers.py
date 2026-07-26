"""Phase 1, sous-question 1 : profils journaliers de demande nette par saison.

Objectif : caractériser la déformation de la demande nette au fil de la journée
(creux de mi-journée, remontée du soir) et voir comment cette forme change selon
la saison, sur deux régions volontairement contrastées.

Choix de cadrage
----------------
- **Pas d'agrégat national.** L'écart entre régions est l'objet d'intérêt ;
  l'agrégat le dilue. On compare Nouvelle-Aquitaine (couverture solaire moyenne
  ~16 %) et Hauts-de-France (~2 %), dont les consommations moyennes sont
  comparables (~4 700 contre ~5 300 MW), ce qui rend la comparaison honnête.
- **Années récentes uniquement.** Agréger 2013 à 2026 mélangerait une époque
  quasi sans solaire et une époque très équipée, ce qui diluerait le creux que
  l'on cherche à voir. L'évolution dans le temps relève de la sous-question 2.
- **Profils, pas journée isolée.** Une journée réelle vient en complément, pour
  illustrer, à la fin du script.
- **Moyenne et médiane tracées ensemble, plus un éventail de quantiles.** Un
  réseau se dimensionne sur le jour le plus contraignant, pas sur le jour moyen :
  ce sont les quantiles extrêmes qui portent l'information utile.

Utilisation dans Spyder : exécuter les cellules une par une avec Ctrl+Entrée.
"""

# %% Imports et paramètres
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    RACINE = Path(__file__).resolve().parents[1]
except NameError:
    RACINE = Path.cwd()
sys.path.insert(0, str(RACINE))

from src.preparation import SAISONS, charger_donnees, filtrer  # noqa: E402

REGIONS = ["Nouvelle-Aquitaine", "Hauts-de-France"]
ANNEES = (2023, 2025)

# Palette catégorielle validée (séparation vision normale 27,6 ; déficience 9,2).
COULEUR_REGION = {"Nouvelle-Aquitaine": "#2a78d6", "Hauts-de-France": "#eb6834"}
COULEUR_SAISON = {
    "Hiver": "#2a78d6",
    "Printemps": "#1baf7a",
    "Été": "#eb6834",
    "Automne": "#4a3aa7",
}

ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
DOSSIER_FIGURES = RACINE / "figures"
DOSSIER_FIGURES.mkdir(exist_ok=True)


def etiquettes_sans_chevauchement(ax, positions, ecart_minimal):
    """Place des étiquettes en fin de courbe en les écartant si elles se superposent.

    `positions` est une liste de (y, texte, couleur). Les courbes convergent
    souvent en fin de journée : sans écartement, les étiquettes se chevauchent.
    """
    ordonnees = sorted(positions, key=lambda p: p[0])
    ajustees = []
    for y, texte, couleur in ordonnees:
        if ajustees and y - ajustees[-1][0] < ecart_minimal:
            y = ajustees[-1][0] + ecart_minimal
        ajustees.append((y, texte, couleur))
    for y, texte, couleur in ajustees:
        ax.annotate(texte, xy=(23.5, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9, color=couleur)


def style_axe(ax):
    """Grille et axes discrets : les données priment sur le décor."""
    ax.grid(True, axis="y", color="#e6e5e1", linewidth=0.8)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        ax.spines[cote].set_color("#d5d4cf")
    ax.tick_params(colors=ENCRE_SECONDAIRE, labelsize=9)
    ax.set_xlim(0, 23.5)
    ax.set_xticks([0, 6, 12, 18])
    ax.set_xticklabels(["0 h", "6 h", "12 h", "18 h"])


# %% Chargement et restriction du périmètre
df = charger_donnees()
peri = filtrer(df, regions=REGIONS, annees=ANNEES)
print(f"Périmètre : {len(peri):,} lignes, "
      f"{peri['date_heure_locale'].min().date()} -> {peri['date_heure_locale'].max().date()}")
print(peri.groupby("libelle_region")["demande_nette"].describe().round(0).to_string())

# %% Calcul des profils : statistiques par région, saison et demi-heure locale
def profils(donnees: pd.DataFrame, variable: str = "demande_nette") -> pd.DataFrame:
    """Moyenne, médiane et quantiles de `variable` par région, saison et heure locale."""
    groupes = donnees.groupby(["libelle_region", "saison", "heure_decimale"], observed=True)
    resultat = groupes[variable].agg(
        moyenne="mean",
        mediane="median",
        d10=lambda s: s.quantile(0.10),
        q25=lambda s: s.quantile(0.25),
        q75=lambda s: s.quantile(0.75),
        d90=lambda s: s.quantile(0.90),
        effectif="size",
    )
    return resultat.reset_index()


prof = profils(peri)
print(f"{len(prof):,} points de profil "
      f"({prof['effectif'].min()} à {prof['effectif'].max()} jours par point)")
print(prof.head(4).to_string(index=False))

# %% Figure 1 : profils détaillés, une grille régions x saisons
fig, axes = plt.subplots(
    len(REGIONS), len(SAISONS), figsize=(15, 7), sharex=True, sharey=True
)

for i, region in enumerate(REGIONS):
    couleur = COULEUR_REGION[region]
    for j, saison in enumerate(SAISONS):
        ax = axes[i, j]
        p = prof[(prof["libelle_region"] == region) & (prof["saison"] == saison)]
        p = p.sort_values("heure_decimale")
        h = p["heure_decimale"]

        # Éventail des quantiles : c'est lui qui porte les jours contraignants.
        ax.fill_between(h, p["d10"], p["d90"], color=couleur, alpha=0.16, linewidth=0)
        ax.fill_between(h, p["q25"], p["q75"], color=couleur, alpha=0.32, linewidth=0)
        ax.plot(h, p["mediane"], color=couleur, linewidth=2, label="Médiane")
        ax.plot(h, p["moyenne"], color=ENCRE, linewidth=1.2, linestyle=(0, (4, 3)),
                label="Moyenne")

        style_axe(ax)
        if i == 0:
            ax.set_title(saison, fontsize=11, color=ENCRE, pad=8)
        if j == 0:
            ax.set_ylabel(f"{region}\nDemande nette (MW)", fontsize=10, color=ENCRE)

axes[0, 0].legend(frameon=False, fontsize=9, loc="lower left", labelcolor=ENCRE_SECONDAIRE)
fig.suptitle(
    f"Demande nette au fil de la journée, par saison ({ANNEES[0]} à {ANNEES[1]})",
    fontsize=13, color=ENCRE, y=0.98,
)
fig.text(0.5, 0.005,
         "Trait plein : médiane. Tirets : moyenne. Bandes : quartiles (q25 à q75) "
         "et déciles (d10 à d90). Heure locale.",
         ha="center", fontsize=9, color=ENCRE_SECONDAIRE)
fig.tight_layout(rect=(0, 0.03, 1, 0.96))
fig.savefig(DOSSIER_FIGURES / "01_profils_saisonniers.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()

# %% Figure 2 : synthèse, les quatre saisons superposées (médianes seules)
fig, axes = plt.subplots(1, len(REGIONS), figsize=(13, 4.8), sharey=True)

for ax, region in zip(axes, REGIONS):
    fins = []
    for saison in SAISONS:
        p = prof[(prof["libelle_region"] == region) & (prof["saison"] == saison)]
        p = p.sort_values("heure_decimale")
        ax.plot(p["heure_decimale"], p["mediane"], color=COULEUR_SAISON[saison],
                linewidth=2, label=saison)
        fins.append((p.iloc[-1]["mediane"], saison, COULEUR_SAISON[saison]))
    # Étiquettes directes : l'identité ne repose jamais sur la seule couleur.
    style_axe(ax)
    ax.set_xlim(0, 28)
    etendue = ax.get_ylim()[1] - ax.get_ylim()[0]
    etiquettes_sans_chevauchement(ax, fins, ecart_minimal=0.055 * etendue)
    ax.set_title(region, fontsize=11, color=ENCRE)
    ax.set_xlabel("Heure locale", fontsize=10, color=ENCRE_SECONDAIRE)

axes[0].set_ylabel("Demande nette médiane (MW)", fontsize=10, color=ENCRE)
axes[0].legend(frameon=False, fontsize=9, loc="lower left", labelcolor=ENCRE_SECONDAIRE)
fig.suptitle(f"Comparaison des saisons ({ANNEES[0]} à {ANNEES[1]})",
             fontsize=13, color=ENCRE)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(DOSSIER_FIGURES / "02_saisons_superposees.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()

# %% Indicateurs chiffrés : profondeur du creux et ampleur de la remontée du soir
def indicateurs(p: pd.DataFrame, colonne: str) -> pd.Series:
    """Creux de mi-journée (10 h-16 h) et remontée jusqu'au pic du soir (18 h-21 h)."""
    midi = p[p["heure_decimale"].between(10, 16)][colonne].min()
    soir = p[p["heure_decimale"].between(18, 21)][colonne].max()
    return pd.Series({"creux_midi": midi, "pic_soir": soir, "remontee": soir - midi})


lignes = []
for region in REGIONS:
    for saison in SAISONS:
        p = prof[(prof["libelle_region"] == region) & (prof["saison"] == saison)]
        for stat, libelle in [("mediane", "jour médian"), ("d10", "jour le plus creusé")]:
            valeurs = indicateurs(p, stat)
            lignes.append({"région": region, "saison": saison, "cas": libelle, **valeurs})

tableau = pd.DataFrame(lignes).round(0)
print(tableau.to_string(index=False))

# %% Complément illustratif : une journée réelle d'été, région ensoleillée
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
fig.savefig(DOSSIER_FIGURES / "03_journee_illustration.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()
