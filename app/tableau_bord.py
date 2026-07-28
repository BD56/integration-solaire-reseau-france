"""Tableau de bord : intégration du solaire dans le réseau électrique français.

Ce fichier ne contient **que** la mise en page et les menus. Les calculs sont
dans `src/analyses.py`, les figures dans `src/graphiques.py`, afin que les
scripts d'analyse et le tableau de bord partagent le même code et ne divergent
pas.

Lancement, depuis la racine du projet :

    uv run streamlit run app/tableau_bord.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from src.analyses import (  # noqa: E402
    SANS_AGREGATION_NATIONALE,
    agreger_national,
    annees_incompletes,
    grille_horaire,
    impact_negatifs,
    profils_par_annee,
    profils_saisonniers,
    profondeur_creux,
)
from src.graphiques import (  # noqa: E402
    carte_chaleur,
    courbes_profil,
    normaliser,
    plafond_couleur,
    plage_commune,
)
from src.graphiques import profils_par_annee as figure_par_annee  # noqa: E402
from src.preparation import SAISONS, charger_donnees  # noqa: E402

st.set_page_config(
    page_title="Solaire et réseau électrique français",
    page_icon="☀️",
    layout="wide",
)


# Le chargement isolé dans une fonction mise en cache : les 2,8 millions de
# lignes ne sont lues qu'une fois, pas à chaque interaction. C'est aussi le seul
# point à modifier le jour où l'on branchera une source allégée pour une version
# en ligne.
@st.cache_data(show_spinner="Chargement des données éCO2mix…")
def donnees():
    return charger_donnees(verbeux=False)


def nombre(valeur: float, decimales: int = 0) -> str:
    """Formate un nombre à la française : espace pour les milliers, virgule décimale.

    À n'appliquer qu'au nombre lui-même. Un `.replace(",", " ")` sur une phrase
    entière effacerait aussi ses virgules de ponctuation.
    """
    texte = f"{valeur:,.{decimales}f}"
    return texte.replace(",", " ").replace(".", ",")


VARIABLES = {
    "Production solaire": ("solaire", "MW"),
    "Production éolienne": ("eolien", "MW"),
    "Consommation": ("consommation", "MW"),
    "Demande nette (solaire et éolien retirés)": ("demande_nette", "MW"),
    "Demande nette (solaire seul retiré)": ("demande_nette_solaire", "MW"),
    "Taux de couverture solaire (part de la consommation)": ("tco_solaire", "%"),
    "Taux de charge solaire (part du parc installé)": ("tch_solaire", "%"),
}

df = donnees()

st.sidebar.title("☀️ Solaire et réseau")
st.sidebar.caption("Données RTE / Enedis via ODRE, pas de 30 minutes, 2013 à 2026.")
page = st.sidebar.radio(
    "Page",
    ["Cartes de chaleur", "Profils saisonniers", "Qualité des données"],
    label_visibility="collapsed",
)

# ----------------------------------------------------------------------------
if page == "Cartes de chaleur":
    st.title("Cartes de chaleur")
    st.caption(
        "Une case par relevé de 30 minutes, sans aucune agrégation. "
        "L'axe vertical est l'heure locale, l'axe horizontal la date."
    )

    reglages, _ = st.columns([3, 1])
    with reglages:
        libelle = st.selectbox("Variable", list(VARIABLES))
        variable, unite = VARIABLES[libelle]

    # Le taux de charge se rapporte à la puissance installée, qui n'est pas une
    # colonne du jeu : il n'existe donc pas d'agrégation nationale possible.
    # Additionner les 12 taux donnerait un chiffre dénué de sens (jusqu'à 1 100 %).
    national_possible = variable not in SANS_AGREGATION_NATIONALE
    regions = (["France entière"] if national_possible else []) \
        + sorted(df["libelle_region"].unique())
    if not national_possible:
        st.caption(
            "« France entière » n'est pas proposée pour le taux de charge : il se "
            "rapporte à la puissance installée, qui n'est pas fournie par le jeu, "
            "et des taux ne s'additionnent pas."
        )

    with reglages:

        comparer = st.toggle("Comparer deux régions", value=True)

        echelle = st.radio(
            "Échelle de couleur",
            ["Commune aux deux", "Propre à chacune", "Normalisée (99e centile = 1)"],
            horizontal=True,
            help=(
                "Commune : montre la disparité réelle des niveaux, au risque de rendre "
                "la plus petite région illisible. Propre : compare les formes. "
                "Normalisée : comparaison de formes la plus stricte, les niveaux "
                "disparaissent totalement."
            ),
            disabled=not comparer,
        )

    def grille_de(region: str):
        """Grille d'une région, ou de la France entière.

        L'agrégation nationale passe par `agreger_national`, qui additionne les
        puissances mais **recalcule** les taux : additionner des pourcentages
        donnerait un taux de couverture médian de 33 % au lieu de 2,6 %.
        """
        if region == "France entière":
            base = agreger_national(df, variable)
        else:
            base = df[df["libelle_region"] == region]
        return grille_horaire(base, variable)

    if not comparer:
        region = st.selectbox("Région", regions, index=0)
        grille = grille_de(region)
        st.plotly_chart(
            carte_chaleur(grille, f"{libelle}, {region}", unite),
            use_container_width=True,
        )
        cases = grille.size
    else:
        gauche, droite = st.columns(2)
        with gauche:
            region_a = st.selectbox("Région de gauche", regions,
                                    index=regions.index("Nouvelle-Aquitaine"))
        with droite:
            region_b = st.selectbox("Région de droite", regions,
                                    index=regions.index("Hauts-de-France"))

        if region_a == region_b:
            st.info("Les deux cartes montrent la même région.", icon="ℹ️")
        elif "France entière" in (region_a, region_b):
            st.info(
                "« France entière » **contient** l'autre région : la comparaison "
                "oppose une partie à l'ensemble qui l'inclut.",
                icon="ℹ️",
            )

        grille_a, grille_b = grille_de(region_a), grille_de(region_b)
        cases = grille_a.size + grille_b.size

        if echelle.startswith("Normalisée"):
            grille_a, grille_b = normaliser(grille_a), normaliser(grille_b)
            plafond_a = plafond_b = 1.0
            unite_affichee = ""
        elif echelle == "Commune aux deux":
            commun = max(plafond_couleur(grille_a), plafond_couleur(grille_b))
            plafond_a = plafond_b = commun
            unite_affichee = unite
        else:
            plafond_a, plafond_b = None, None
            unite_affichee = unite

        with gauche:
            st.plotly_chart(
                carte_chaleur(grille_a, region_a, unite_affichee, plafond_a, hauteur=420),
                use_container_width=True,
            )
        with droite:
            st.plotly_chart(
                carte_chaleur(grille_b, region_b, unite_affichee, plafond_b, hauteur=420),
                use_container_width=True,
            )

    note = (
        f"{nombre(cases)} cases affichées. "
        "L'échelle est calée sur le 99e centile : les journées record saturent, "
        "afin de ne pas écraser la lecture des valeurs courantes."
    )
    if variable == "tch_solaire":
        note += " Le taux de charge n'existe qu'à partir de 2020."
    if variable == "tco_solaire":
        note += (" ⚠️ Avant 2020, RTE ne publiait pas le taux de couverture : "
                 "les valeurs affichées sont **reconstruites** par le projet "
                 "(`100 × solaire / consommation`, erreur médiane 0,003 point).")
    st.caption(note)

    if comparer and echelle != "Commune aux deux":
        st.warning(
            "Les deux cartes n'ont pas la même échelle : leurs **formes** sont "
            "comparables, leurs **niveaux** ne le sont pas.",
            icon="⚠️",
        )

# ----------------------------------------------------------------------------
elif page == "Profils saisonniers":
    st.title("Profils journaliers")
    st.caption(
        "À quoi ressemble une journée type, et comment cette forme se déforme "
        "selon la saison puis au fil des années."
    )

    VARIABLES_PROFIL = {
        "Demande nette (solaire et éolien retirés)": "demande_nette",
        "Demande nette (solaire seul retiré)": "demande_nette_solaire",
        "Consommation": "consommation",
        "Production solaire": "solaire",
    }

    reglages, _ = st.columns([3, 1])
    with reglages:
        region = st.selectbox("Région", sorted(df["libelle_region"].unique()),
                              key="region_profil")
        libelle_var = st.selectbox("Variable", list(VARIABLES_PROFIL))
        variable = VARIABLES_PROFIL[libelle_var]

    base_region = df[df["libelle_region"] == region]
    incompletes = annees_incompletes(base_region)

    onglet_saison, onglet_annee = st.tabs(
        ["Par saison", "Par année (sous-question 2)"]
    )

    with onglet_saison:
        # Une année tronquée déséquilibre les saisons : si elle s'arrête en avril,
        # elle ajoute des jours d'hiver et de printemps mais aucun d'été. Ces deux
        # saisons seraient alors tirées vers l'année la plus récente, pas les autres.
        annees_possibles = [a for a in sorted(base_region["annee"].unique())
                            if a not in incompletes]
        debut, fin = st.select_slider(
            "Période retenue", options=annees_possibles,
            value=(max(annees_possibles[0], 2023), annees_possibles[-1]),
            help=(
                "Agréger toute la période mélangerait une époque quasi sans "
                "solaire et une époque très équipée, ce qui diluerait le creux."
            ),
        )
        peri = base_region[base_region["annee"].between(debut, fin)]
        profils = profils_saisonniers(peri, variable)

        if incompletes:
            jours = peri.groupby("saison", observed=True)["date"].nunique()
            st.caption(
                f"Années incomplètes écartées ({', '.join(map(str, incompletes))}) : "
                "elles n'auraient alimenté qu'une partie des saisons. "
                "Jours retenus par saison : "
                + ", ".join(f"{s} {n}" for s, n in jours.items()) + "."
            )

        # Échelle verticale commune aux quatre saisons : sans elle, chaque
        # panneau se cale sur ses propres valeurs et l'hiver, deux fois plus
        # haut que l'été, paraît d'amplitude comparable.
        echelle_commune = plage_commune(profils)

        colonnes = st.columns(2)
        for indice, saison in enumerate(SAISONS):
            with colonnes[indice % 2]:
                st.plotly_chart(
                    courbes_profil(profils, saison, plage_y=echelle_commune),
                    use_container_width=True,
                    key=f"profil_{saison}",
                )
        st.caption(
            "Trait plein : médiane. Tirets : moyenne. Bandes : quartiles et déciles. "
            "Un réseau se dimensionne sur le jour le plus contraignant, pas sur le "
            "jour moyen : ce sont donc les déciles qui portent l'information utile."
        )

    with onglet_annee:
        if incompletes:
            ecarter = st.toggle(
                f"Écarter les années incomplètes ({', '.join(map(str, incompletes))})",
                value=True,
                help=(
                    "Une année tronquée ne couvre qu'une partie des saisons. "
                    "Comparée à des années entières, elle paraît anormalement haute "
                    "ou basse alors que seul le calendrier diffère."
                ),
            )
        else:
            ecarter = False

        base_annees = (
            base_region[~base_region["annee"].isin(incompletes)]
            if ecarter else base_region
        )

        par_annee = profils_par_annee(base_annees, variable)
        st.plotly_chart(
            figure_par_annee(par_annee, f"{libelle_var}, {region}"),
            use_container_width=True,
        )

        if incompletes and not ecarter:
            jours = base_region[base_region["annee"].isin(incompletes)] \
                .groupby("annee")["date"].nunique()
            detail = ", ".join(f"**{a}** ne couvre que {n} jours" for a, n in jours.items())
            st.warning(
                f"Années incomplètes affichées : {detail}. Elles ne contiennent "
                "qu'une partie des saisons, leur niveau n'est donc pas comparable "
                "aux années entières. L'écart visible tient au calendrier, pas au "
                "phénomène.",
                icon="⚠️",
            )

        # L'avertissement sur les ruptures n'a de sens que pour les variables
        # réellement concernées. La rupture de 2021 (vide devenu zéro) ne touche
        # ni la consommation, ni le solaire, ni l'éolien : inutile de la signaler ici.
        if variable in ("solaire", "demande_nette", "demande_nette_solaire"):
            impact = impact_negatifs(base_region, "solaire")
            if impact["lignes"]:
                st.info(
                    "Avant 2020, RTE reportait la consommation propre des "
                    "installations, d'où des valeurs solaires négatives, supprimées "
                    f"depuis. Dans cette région : **{nombre(impact['lignes'])} relevés** "
                    f"({nombre(impact['part_periode_%'], 2)} % de la période affichée, "
                    f"{nombre(impact['part_avant_2020_%'], 2)} % des relevés d'avant "
                    "2020), de médiane "
                    f"**{nombre(impact['mediane'])} MW** et de minimum "
                    f"{nombre(impact['minimum'])} MW, soit environ "
                    f"**{nombre(impact['poids_relatif_%'], 3)} %** du niveau de "
                    "consommation. L'effet sur la courbe est donc négligeable, et les "
                    "valeurs sont conservées telles quelles plutôt que corrigées.",
                    icon="ℹ️",
                )
            else:
                st.caption(
                    "Cette région ne comporte aucune valeur solaire négative : "
                    "le changement de convention de 2020 est sans effet ici."
                )

        creux = profondeur_creux(base_annees, variable)
        st.dataframe(
            creux.round(0).rename(columns={
                "annee": "année", "creux_midi": "creux de mi-journée",
                "pic_soir": "pic du soir", "nuit": "niveau de nuit",
                "remontee": "remontée du soir", "creusement": "creusement à midi",
            }),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            "Creux mesuré entre 10 h et 16 h, pic du soir entre 18 h et 21 h, "
            "niveau de nuit entre 2 h et 5 h. Le creusement est l'écart entre la "
            "nuit et le creux de mi-journée."
        )

# ----------------------------------------------------------------------------
elif page == "Qualité des données":
    st.title("Qualité des données")
    st.info("Page à construire : complétude, valeurs négatives, ruptures temporelles.")
