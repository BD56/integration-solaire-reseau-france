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
    MI_JOURNEE,
    NUIT,
    SANS_AGREGATION_NATIONALE,
    agreger_national,
    annees_incompletes,
    completude_par_annee,
    creneaux_par_jour,
    grille_horaire,
    impact_negatifs,
    moyenne_entre,
    part_reconstruite,
    profil_horaire_par_annee,
    profils_par_annee,
    profils_saisonniers,
    profondeur_creux,
    rampe_du_soir,
    sensibilite_rampe,
    temoin_saisonnier,
    trame_nationale,
    valeurs_impossibles,
    valeurs_negatives,
    verdicts_equilibrage,
)
from src.graphiques import (  # noqa: E402
    carte_chaleur,
    courbes_profil,
    indicateur_annuel,
    normaliser,
    plafond_couleur,
    plage_commune,
    profil_horaire_annees,
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
    ["Cartes de chaleur", "Profils saisonniers", "Équilibrage", "Qualité des données"],
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
            width="stretch",
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
                width="stretch",
            )
        with droite:
            st.plotly_chart(
                carte_chaleur(grille_b, region_b, unite_affichee, plafond_b, hauteur=420),
                width="stretch",
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
                    width="stretch",
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
            width="stretch",
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
            width="stretch", hide_index=True,
        )
        st.caption(
            "Creux mesuré entre 10 h et 16 h, pic du soir entre 18 h et 21 h, "
            "niveau de nuit entre 2 h et 5 h. Le creusement est l'écart entre la "
            "nuit et le creux de mi-journée."
        )

# ----------------------------------------------------------------------------
elif page == "Équilibrage":
    st.title("Comment le système absorbe le solaire")
    st.caption(
        "Le solaire crée un surplus à midi, puis disparaît le soir. "
        "Que fait le reste du système pour absorber l'un et compenser l'autre ?"
    )

    trame = trame_nationale(df[~df["annee"].isin(annees_incompletes(df))])

    st.subheader("Quatre hypothèses, leurs critères écrits avant tout calcul")
    verdicts = verdicts_equilibrage(trame)
    couleurs = {"validée": "✅", "rejetée": "❌", "indécise": "➖"}
    st.dataframe(
        verdicts.assign(etat=verdicts["etat"].map(lambda e: f"{couleurs.get(e, '')} {e}"))
        .rename(columns={"hypothese": "hypothèse", "etat": "verdict"}),
        width="stretch", hide_index=True,
    )
    st.caption(
        "Critère commun, fixé à l'avance : validée si |r| > 0,7 dans le sens "
        "prédit, rejetée si |r| < 0,3 ou si le sens est contraire. "
        "**L'hypothèse rejetée est conservée** : un rejet est un résultat, et "
        "n'afficher que ce qui marche reviendrait à choisir ses preuves."
    )

    onglet_stockage, onglet_nucleaire, onglet_soir = st.tabs(
        ["Le stockage change d'heure", "Le nucléaire module", "La remontée du soir"]
    )

    # ------------------------------------------------------------------
    with onglet_stockage:
        pompage = profil_horaire_par_annee(trame, "pompage")
        st.plotly_chart(
            profil_horaire_annees(
                pompage, "Pompage au fil de la journée, par année",
                "MW", valeur_absolue=True,
            ),
            width="stretch",
        )
        st.caption(
            "Le pompage est compté négativement dans la source, puisqu'il "
            "consomme : la courbe est retournée, donc **plus haut signifie que "
            "l'on pompe davantage**. Les années claires sont les plus anciennes."
        )
        midi = moyenne_entre(pompage.abs(), MI_JOURNEE)
        nuit = moyenne_entre(pompage.abs(), NUIT)
        premiere, derniere = midi.index[0], midi.index[-1]
        colonne_a, colonne_b, colonne_c = st.columns(3)
        colonne_a.metric(
            "Pompage de mi-journée",
            f"{nombre(midi.loc[derniere])} MW",
            f"×{midi.loc[derniere] / midi.loc[premiere]:.1f}".replace(".", ","),
        )
        colonne_b.metric(
            "Pompage de nuit",
            f"{nombre(nuit.loc[derniere])} MW",
            f"{nombre(nuit.loc[derniere] - nuit.loc[premiere])} MW",
        )
        colonne_c.metric("Heure du maximum", f"{pompage.abs().loc[derniere].idxmax():.0f} h",
                         "4 h 30 auparavant", delta_color="off")

        st.markdown(
            "On stockait la nuit, avec le surplus nucléaire. On stocke "
            "désormais **aussi à midi**, avec le surplus solaire. L'heure du "
            "maximum, à 4 h 30 dix années sur douze, bascule à **15 h en 2025**."
        )
        croisement = midi[midi > nuit]
        if not croisement.empty:
            st.markdown(
                f"**{croisement.index[0]} est la première année où l'on pompe "
                f"davantage à midi ({nombre(midi.loc[croisement.index[0]])} MW) "
                f"que la nuit ({nombre(nuit.loc[croisement.index[0]])} MW).** "
                "Les deux courbes se croisent, ce n'est plus seulement une "
                "tendance."
            )
        st.warning(
            "**Réserve à lire avec ce résultat.** Le basculement de l'heure du "
            "maximum repose sur la seule année **2025**, classée `Données "
            "consolidées` donc encore révisable. Et le déplacement se produit "
            "**aussi en hiver**, où le solaire ne peut presque rien : c'est "
            "l'hypothèse validée dont l'attribution au solaire est la **moins** "
            "établie. Voir le témoin saisonnier plus bas.",
            icon="⚠️",
        )

    # ------------------------------------------------------------------
    with onglet_nucleaire:
        nucleaire = profil_horaire_par_annee(trame, "nucleaire")
        rapport = (moyenne_entre(nucleaire, MI_JOURNEE)
                   / moyenne_entre(nucleaire, NUIT))
        gauche, droite = st.columns([3, 2])
        with gauche:
            st.plotly_chart(
                profil_horaire_annees(nucleaire, "Nucléaire au fil de la journée", "MW"),
                width="stretch",
            )
        with droite:
            st.plotly_chart(
                indicateur_annuel(
                    rapport, "Rapport mi-journée sur nuit", "", reference=1.0
                ),
                width="stretch",
            )
        st.markdown(
            "Au-dessus de 1, le nucléaire produit **plus** à midi que la nuit, "
            "ce qui est le comportement d'une production de base qui suit la "
            "consommation. En dessous, il **s'efface devant le solaire**. Le "
            "franchissement a lieu en 2024."
        )
        st.success(
            "C'est l'hypothèse la mieux étayée : elle passe le témoin "
            "saisonnier, c'est-à-dire que le nucléaire ne module **qu'en été**, "
            "là où le solaire agit, et pas en hiver.",
            icon="✅",
        )

    # ------------------------------------------------------------------
    with onglet_soir:
        st.plotly_chart(
            indicateur_annuel(
                rampe_du_soir(trame),
                "Variation maximale de demande nette en soirée, médiane par année",
                "MW par demi-heure",
            ),
            width="stretch",
        )
        st.markdown(
            "Quand le solaire s'efface en fin de journée, le reste du système "
            "doit remonter, et il doit le faire **de plus en plus vite** : de "
            "2 075 MW par demi-heure en 2013 à **2 674 MW en 2025**."
        )
        st.error(
            "**Ce résultat a d'abord été publié à l'envers.** Un calcul de "
            "variation enjambait la nuit et comparait deux journées "
            "différentes, ce qui donnait r = −0,45 et faisait conclure que la "
            "remontée ne s'accélérait pas. Corrigé, r vaut **+0,89**. L'erreur "
            "et sa correction sont consignées au journal du projet.",
            icon="🔧",
        )

        st.subheader("Sensibilité aux bornes")
        st.caption(
            "Une mesure qui dépend d'une fenêtre choisie à la main doit voir "
            "cette fenêtre varier avant d'être publiée."
        )
        st.dataframe(sensibilite_rampe(trame), width="stretch", hide_index=True)
        st.info(
            "Cinq fenêtres sur sept donnent exactement le même résultat et une "
            "le renforce, mais **la plus large change de signe**. Le résultat "
            "est solide sur la soirée proprement dite, il ne l'est pas si l'on "
            "étend la fenêtre jusqu'au creux de mi-journée.",
            icon="ℹ️",
        )

    st.divider()
    st.subheader("Le témoin qui départage : est-ce vraiment le solaire ?")
    st.caption(
        "Les verdicts ci-dessus sont des corrélations contre l'année sur treize "
        "points : ils établissent une régularité, pas une cause. Ce témoin, lui, "
        "n'est pas une corrélation contre l'année. Si le solaire est bien la "
        "cause, l'effet doit être **fort en été et faible en hiver**."
    )
    st.dataframe(temoin_saisonnier(trame), width="stretch", hide_index=True)
    st.markdown(
        "**Lecture.** Le nucléaire passe le test nettement : il ne module qu'en "
        "été. La remontée du soir aussi : elle accélère en été, tandis qu'en "
        "hiver demande nette et consommation évoluent de concert, donc sans "
        "effet propre du solaire. **Le pompage ne le passe pas** : il se déplace "
        "presque autant en hiver, ce qui suggère qu'une autre cause y contribue "
        "(évolution des prix de marché, gestion du parc hydraulique)."
    )

# ----------------------------------------------------------------------------
elif page == "Qualité des données":
    st.title("Qualité des données")
    st.caption(
        "Ce que ces données ne disent pas, et les pièges qu'elles tendent. "
        "Tout ce qui suit est mesuré sur le jeu réellement chargé, pas recopié "
        "d'une documentation."
    )

    st.warning(
        "**Le piège principal de ce jeu.** Plusieurs variables passent de "
        "« case vide » à « zéro » en 2021. Une moyenne calculée sur les 12 "
        "régions plonge alors brutalement, sans qu'aucun phénomène physique ne "
        "se soit produit. La moyenne du nucléaire chute ainsi de **37,1 %** en "
        "2021, alors qu'elle **augmente de 7,9 %** sur les 7 régions qui ont "
        "réellement une centrale.",
        icon="⚠️",
    )

    onglet_completude, onglet_bornes, onglet_temps = st.tabs(
        ["Complétude et ruptures", "Valeurs suspectes", "Temps et reconstruction"]
    )

    # ------------------------------------------------------------------
    with onglet_completude:
        st.subheader("Taux de remplissage, année par année")
        st.caption(
            "Une colonne qui passe brutalement de 0 à 100 % signale un "
            "changement de méthode chez RTE, pas un changement du réseau. "
            "C'est ici qu'on les repère."
        )
        COLONNES_SUIVIES = [
            "consommation", "solaire", "eolien", "nucleaire", "pompage",
            "hydraulique", "thermique", "bioenergies",
            "tco_solaire", "tch_solaire", "eolien_terrestre", "stockage_batterie",
        ]
        remplissage = completude_par_annee(df, COLONNES_SUIVIES)
        st.dataframe(
            remplissage.style.format("{:.1f}").background_gradient(
                cmap="RdYlGn", vmin=0, vmax=100, axis=None
            ),
            width="stretch",
        )

        gauche, droite = st.columns(2)
        with gauche:
            st.markdown(
                "**2020 : changement de convention.** Apparition des taux de "
                "couverture et de charge, et disparition simultanée de toutes "
                "les valeurs négatives. Frontière à respecter dans toute série "
                "solaire longue."
            )
        with droite:
            st.markdown(
                "**2021 : vide devenu zéro.** Nucléaire, pompage, éolien "
                "terrestre et batteries. Ne jamais moyenner sur les 12 régions "
                "sans vérifier le remplissage : restreindre aux régions "
                "réellement concernées."
            )

        st.subheader("Colonnes inexploitables")
        st.markdown(
            "- `stockage_batterie` et `destockage_batterie` sont **toujours à "
            "zéro** sur toute la période. Aucune analyse ne peut s'appuyer "
            "dessus ; le seul stockage observable est le `pompage`.\n"
            "- `column_30` était entièrement vide, elle est supprimée au "
            "chargement."
        )

    # ------------------------------------------------------------------
    with onglet_bornes:
        st.subheader("Productions négatives")
        st.caption(
            "Une production négative est physiquement réelle : l'installation "
            "consomme (auxiliaires, onduleurs la nuit). Le problème n'est pas "
            "la valeur, c'est qu'elle est **déclarée de façon incohérente**."
        )
        negatives = valeurs_negatives(
            df, ["solaire", "eolien", "hydraulique", "nucleaire", "bioenergies"]
        )
        st.dataframe(
            negatives.rename(columns={
                "filiere": "filière", "lignes_negatives": "lignes négatives",
                "part_%": "part (%)", "minimum": "minimum (MW)",
                "mediane_negatifs": "médiane des négatifs (MW)",
            }),
            width="stretch", hide_index=True,
        )
        st.info(
            "Le solaire négatif est à **99,8 % en Nouvelle-Aquitaine**, entre "
            "2015 et 2019. C'est une pratique de déclaration régionale, pas un "
            "phénomène physique : **ne jamais comparer les régions sur cette "
            "base**. Ces valeurs ne sont pas corrigées, parce que les ramener à "
            "zéro détruirait l'information d'autoconsommation.",
            icon="ℹ️",
        )

        st.subheader("Valeurs physiquement impossibles")
        st.caption(
            "Un taux de charge rapporte une production à la puissance "
            "installée : il ne peut pas dépasser 100 %. Quand il le fait, c'est "
            "la référence de puissance installée qui est en retard sur le parc "
            "réel."
        )
        impossibles = valeurs_impossibles(df)
        if impossibles.empty:
            st.success("Aucun taux de charge au-dessus de 100 % sur ce périmètre.")
        else:
            st.dataframe(
                impossibles.rename(columns={
                    "variable": "variable",
                    "lignes_au_dessus_de_100_%": "lignes > 100 %",
                    "part_%": "part (%)", "maximum_%": "maximum (%)",
                    "regions_concernees": "régions concernées",
                }),
                width="stretch", hide_index=True,
            )
            st.warning(
                "L'ampleur varie énormément selon la filière : le solaire "
                "plafonne à 172 %, mais l'**hydraulique atteint 2 575 %** et "
                "les bioénergies 719 %. Ces filières ont un parc régional très "
                "petit, où toute erreur de référence explose en pourcentage. "
                "Conséquence directe : la puissance installée dérivée en "
                "inversant le taux de charge est **sous-estimée** aux mêmes "
                "endroits.",
                icon="⚠️",
            )

    # ------------------------------------------------------------------
    with onglet_temps:
        st.subheader("Changements d'heure")
        st.caption(
            "La source publie toujours 48 créneaux par jour, y compris les "
            "jours de bascule. Cela produit deux anomalies de nature opposée."
        )
        st.dataframe(
            creneaux_par_jour(df).rename(columns={
                "creneaux": "créneaux dans la journée",
                "journees_x_regions": "journées × régions",
            }),
            width="stretch", hide_index=True,
        )
        st.markdown(
            "**Mars** : les créneaux locaux 02:00 et 02:30 n'existent pas mais "
            "sont publiés quand même. Ils sont **retirés** au chargement (336 "
            "au total), pas dédupliqués au hasard.\n\n"
            "**Octobre** : l'inverse, une heure réelle **manque** (312 "
            "créneaux). Elle n'apparaît pas dans le tableau ci-dessus parce que "
            "le trou est du côté UTC, pas du côté des étiquettes locales."
        )
        st.warning(
            "**À traiter avant tout modèle de série temporelle.** À cause du "
            "trou d'octobre, la série UTC **n'est pas une grille régulière** : "
            "un saut de 1 h 30 une fois par an et par région.\n\n"
            "Ce n'est **pas une perte d'information** : le créneau absent est "
            "nocturne, le solaire y vaut 0,07 MW et la consommation est à son "
            "plancher. C'est un défaut d'**indexation** : reculer de 48 lignes "
            "pour viser « la même heure hier » ramène 25 heures en arrière sur "
            "les lignes qui suivent le trou.\n\n"
            "Mesuré : **7 488 lignes sur 2 803 620 (0,267 %)**, erreur médiane "
            "de 135 MW soit 3,33 % du niveau médian. Écarter les treize "
            "journées concernées coûte 0,03 % des données.",
            icon="🚧",
        )

        st.subheader("Ce que RTE publie, et ce que le projet reconstruit")
        st.caption(
            "Avant 2020, RTE ne publiait pas les taux de couverture. Le projet "
            "les recalcule par `100 × filière / consommation`, formule vérifiée "
            "sur la période où les deux coexistent : erreur médiane de 0,003 "
            "point."
        )
        st.dataframe(
            part_reconstruite(df).rename(columns={
                "annee": "année", "part_reconstruite_%": "part reconstruite (%)",
            }),
            width="stretch", hide_index=True,
        )
        st.caption(
            "La colonne `tco_reconstruit` marque ces lignes dans les données, "
            "pour qu'aucune analyse ne confonde une valeur publiée par RTE et "
            "une valeur recalculée ici."
        )

        st.subheader("Nature des données")
        st.markdown(
            "La colonne `nature` distingue **données définitives** (jusqu'à "
            "2024) et **données consolidées** (2025 et 2026, encore "
            "révisables). Ce n'est pas un doublon mais un découpage temporel. "
            "Un résultat qui reposerait sur la seule année 2025 doit le "
            "signaler."
        )
