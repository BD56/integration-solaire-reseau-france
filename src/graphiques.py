"""Figures Plotly, construites à partir des tableaux de `src.analyses`.

Ce module ne calcule rien : il reçoit des tableaux déjà agrégés et les met en
forme. Il est utilisé par le tableau de bord, et peut l'être par les scripts.

Conventions graphiques
----------------------
- Rampe séquentielle : **une seule teinte**, du clair au foncé. Jamais d'arc-en-ciel,
  qui ferait lire des ruptures là où la grandeur varie continûment.
- Axes et grilles discrets : la donnée prime sur le décor.
- Les valeurs absentes apparaissent en gris, pour que les trous se voient.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
SURFACE = "#ffffff"
GRILLE = "#e6e5e1"
ABSENT = "#d9d8d4"

# Rampe séquentielle ambre, du clair au foncé.
RAMPE_SOLAIRE = [
    [0.0, "#fdfbf6"],
    [0.35, "#f7dfa0"],
    [0.70, "#eda100"],
    [1.0, "#8a5c00"],
]

MISE_EN_PAGE = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(color=ENCRE_SECONDAIRE, size=12),
    margin=dict(l=60, r=20, t=60, b=50),
    hoverlabel=dict(bgcolor=SURFACE, font_size=12),
)


def _etiquettes_heures(heures: pd.Index) -> list[str]:
    """Convertit 13.5 en « 13:30 », pour un survol lisible."""
    return [f"{int(h):02d}:{int(round((h % 1) * 60)):02d}" for h in heures]


def plafond_couleur(grille: pd.DataFrame, centile: float = 0.99) -> float:
    """Haut de l'échelle de couleur, calé sur un centile plutôt que le maximum.

    Sur une distribution asymétrique, quelques journées record écraseraient
    toute la lecture : le Grand Est paraissait pâle alors que sa production
    courante est simplement très inférieure à son record. Les valeurs au-delà
    du centile saturent au lieu de faire disparaître le reste.
    """
    valeurs = grille.to_numpy()
    plafond = float(np.nanquantile(valeurs, centile))
    if not np.isfinite(plafond) or plafond <= 0:
        plafond = float(np.nanmax(valeurs))
    return plafond


def normaliser(grille: pd.DataFrame) -> pd.DataFrame:
    """Divise la grille par son propre 99e centile, qui vaut donc 1.

    Attention : environ 1 % des valeurs **dépassent 1**, ce qui est voulu. Caler
    la référence sur le maximum ferait qu'une seule journée record écraserait
    toute la lecture, exactement le défaut qu'on cherche à éviter. Le mode ne
    doit donc pas être présenté comme allant « de 0 à 1 ».

    Efface complètement les niveaux pour ne comparer que les **formes**. Utile
    entre régions de tailles très différentes, où l'échelle commune rendrait la
    plus petite illisible.

    Ce n'est qu'une normalisation d'**affichage**. Pour neutraliser réellement
    la taille du parc installé, la variable `tch_solaire` (taux de charge) est le
    bon outil, car elle rapporte la production à la puissance installée. Elle
    n'existe qu'à partir de 2020.
    """
    return grille / plafond_couleur(grille)


def courbes_profil(
    profils: pd.DataFrame,
    saison: str,
    unite: str = "MW",
    couleur: str = "#2a78d6",
) -> go.Figure:
    """Profil journalier d'une saison : médiane, moyenne et éventail de quantiles.

    Les bandes de quantiles portent l'information utile pour un réseau, qui se
    dimensionne sur le jour le plus contraignant et non sur le jour moyen.
    L'écart entre moyenne et médiane mesure l'asymétrie de la distribution.
    """
    p = profils[profils["saison"] == saison].sort_values("heure_decimale")
    heures = p["heure_decimale"]
    figure = go.Figure()

    for bas, haut, opacite, nom in [
        ("d10", "d90", 0.14, "déciles (d10 à d90)"),
        ("q25", "q75", 0.28, "quartiles (q25 à q75)"),
    ]:
        figure.add_trace(go.Scatter(
            x=list(heures) + list(heures[::-1]),
            y=list(p[haut]) + list(p[bas][::-1]),
            fill="toself", fillcolor=_transparence(couleur, opacite),
            line=dict(width=0), hoverinfo="skip", name=nom,
        ))

    figure.add_trace(go.Scatter(
        x=heures, y=p["moyenne"], mode="lines", name="moyenne",
        line=dict(color=ENCRE, width=1.4, dash="dash"),
        hovertemplate="%{x:.1f} h<br>moyenne <b>%{y:.0f} " + unite + "</b><extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=heures, y=p["mediane"], mode="lines", name="médiane",
        line=dict(color=couleur, width=2.5),
        hovertemplate="%{x:.1f} h<br>médiane <b>%{y:.0f} " + unite + "</b><extra></extra>",
    ))

    figure.update_layout(
        title=dict(text=saison, font=dict(color=ENCRE, size=15)),
        height=340, showlegend=False, **MISE_EN_PAGE,
    )
    _axes_journee(figure, unite)
    return figure


def profils_par_annee(
    par_annee: pd.DataFrame, titre: str, unite: str = "MW"
) -> go.Figure:
    """Profil journalier médian, une courbe par année, du clair au foncé.

    L'année est une grandeur ordonnée : on lui applique donc une rampe
    séquentielle d'une seule teinte, et non des couleurs catégorielles qui
    feraient lire des groupes là où il y a une progression continue.
    """
    annees = sorted(par_annee["annee"].unique())
    figure = go.Figure()
    for rang, annee in enumerate(annees):
        p = par_annee[par_annee["annee"] == annee].sort_values("heure_decimale")
        part = rang / max(len(annees) - 1, 1)
        figure.add_trace(go.Scatter(
            x=p["heure_decimale"], y=p["mediane"], mode="lines", name=str(annee),
            line=dict(color=_teinte_sequentielle(part), width=2),
            hovertemplate=f"<b>{annee}</b><br>%{{x:.1f}} h<br>"
                          f"<b>%{{y:.0f}} {unite}</b><extra></extra>",
        ))
    figure.update_layout(
        title=dict(text=titre, font=dict(color=ENCRE, size=15)),
        height=460,
        legend=dict(title="", orientation="v", x=1.01, y=1, font=dict(size=11)),
        **MISE_EN_PAGE,
    )
    _axes_journee(figure, unite)
    return figure


def _axes_journee(figure: go.Figure, unite: str) -> None:
    """Axes communs aux profils journaliers : heure locale en abscisse."""
    figure.update_xaxes(
        title_text="Heure locale", range=[0, 23.5],
        tickmode="array", tickvals=[0, 6, 12, 18],
        ticktext=["0 h", "6 h", "12 h", "18 h"],
        showgrid=False, linecolor=GRILLE,
    )
    figure.update_yaxes(title_text=unite, gridcolor=GRILLE, zeroline=False, linecolor=GRILLE)


def _transparence(couleur_hex: str, alpha: float) -> str:
    """Convertit « #2a78d6 » en « rgba(42,120,214,alpha) »."""
    r, v, b = (int(couleur_hex[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{v},{b},{alpha})"


def _teinte_sequentielle(part: float) -> str:
    """Interpole la rampe ambre pour une position entre 0 (clair) et 1 (foncé)."""
    etapes = [(0.0, (247, 223, 160)), (0.55, (237, 161, 0)), (1.0, (94, 62, 0))]
    for (p0, c0), (p1, c1) in zip(etapes, etapes[1:]):
        if part <= p1:
            t = (part - p0) / (p1 - p0) if p1 > p0 else 0
            r, v, b = (round(a + (z - a) * t) for a, z in zip(c0, c1))
            return f"rgb({r},{v},{b})"
    return "rgb(94,62,0)"


def carte_chaleur(
    grille: pd.DataFrame,
    titre: str,
    unite: str = "MW",
    plafond: float | None = None,
    hauteur: int = 460,
) -> go.Figure:
    """Carte de chaleur heure locale x date, une case par relevé.

    `plafond` impose le haut de l'échelle de couleur. Le laisser à `None` le
    calcule sur cette grille seule ; le fournir permet de partager la même
    échelle entre plusieurs cartes, et donc de comparer les niveaux.
    """
    valeurs = grille.to_numpy()
    if plafond is None:
        plafond = plafond_couleur(grille)

    format_valeur = ":.2f" if unite == "" else ":.0f"
    suffixe = f" {unite}" if unite else ""

    figure = go.Figure(
        go.Heatmap(
            z=valeurs,
            x=pd.to_datetime(grille.columns),
            y=_etiquettes_heures(grille.index),
            colorscale=RAMPE_SOLAIRE,
            zmin=0,
            zmax=plafond,
            hovertemplate=(
                "%{x|%d/%m/%Y}<br>%{y}<br><b>%{z" + format_valeur + "}"
                + suffixe + "</b><extra></extra>"
            ),
            colorbar=dict(
                title=dict(text=unite or "part", side="right"),
                thickness=14,
                outlinewidth=0,
                tickfont=dict(color=ENCRE_SECONDAIRE),
            ),
        )
    )
    figure.update_layout(
        title=dict(text=titre, font=dict(color=ENCRE, size=15)),
        height=hauteur,
        **MISE_EN_PAGE,
    )
    figure.update_xaxes(showgrid=False, linecolor=GRILLE, ticks="outside", tickcolor=GRILLE)
    figure.update_yaxes(
        showgrid=False,
        linecolor=GRILLE,
        title_text="Heure locale",
        tickmode="array",
        tickvals=["00:00", "06:00", "12:00", "18:00"],
    )
    return figure
