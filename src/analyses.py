"""Calculs d'analyse, indépendants de tout affichage.

Les fonctions de ce module renvoient des tableaux, jamais des figures. Elles
sont appelées aussi bien par les scripts de `notebooks/` que par le tableau de
bord, ce qui évite que les deux divergent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.preparation import SAISONS


def grille_horaire(
    donnees: pd.DataFrame, variable: str = "solaire"
) -> pd.DataFrame:
    """Tableau heure locale x date, une case par relevé.

    Aucune agrégation : une région compte autant de relevés que la grille a de
    cases. C'est la vue la plus fidèle possible, utilisée par les cartes de
    chaleur.
    """
    grille = donnees.pivot_table(
        index="heure_decimale", columns="date", values=variable, aggfunc="mean"
    )
    return grille.reindex(sorted(grille.columns), axis=1)


#: Variables dont l'agrégation nationale ne peut pas être une somme.
#: Additionner des pourcentages de 12 régions n'a aucun sens : le taux de
#: couverture national vaut la somme des productions rapportée à la somme des
#: consommations, et non la somme des taux.
RATIOS = {"tco_solaire": ("solaire", "consommation")}

#: Variables pour lesquelles aucune agrégation nationale n'est possible ici.
#: `tch_solaire` rapporte la production à la puissance installée, qui n'est pas
#: une colonne du jeu : on ne peut donc pas la sommer entre régions.
SANS_AGREGATION_NATIONALE = {"tch_solaire"}


def agreger_national(donnees: pd.DataFrame, variable: str) -> pd.DataFrame:
    """Série nationale d'une variable, avec l'agrégation qui lui convient.

    Les puissances (MW) s'additionnent. Les taux ne s'additionnent pas : ils se
    recalculent à partir des sommes de leur numérateur et de leur dénominateur.
    """
    if variable in SANS_AGREGATION_NATIONALE:
        raise ValueError(
            f"{variable} ne peut pas être agrégée nationalement : elle se rapporte "
            "à la puissance installée, qui n'est pas fournie par le jeu de données."
        )
    cles = ["date", "heure_decimale"]
    if variable in RATIOS:
        numerateur, denominateur = RATIOS[variable]
        somme = donnees.groupby(cles, as_index=False)[[numerateur, denominateur]].sum()
        somme[variable] = 100 * somme[numerateur] / somme[denominateur].replace(0, pd.NA)
        return somme[cles + [variable]]
    return donnees.groupby(cles, as_index=False)[variable].sum()


def profils_saisonniers(
    donnees: pd.DataFrame, variable: str = "demande_nette"
) -> pd.DataFrame:
    """Moyenne, médiane et quantiles de `variable` par saison et heure locale.

    Les quantiles portent l'information utile pour un réseau, qui se dimensionne
    sur le jour le plus contraignant et non sur le jour moyen.
    """
    groupes = donnees.groupby(["saison", "heure_decimale"], observed=True)
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


def profils_par_annee(
    donnees: pd.DataFrame, variable: str = "demande_nette"
) -> pd.DataFrame:
    """Profil journalier médian, une ligne par année et par heure locale.

    Sert à voir le creux de mi-journée se former à mesure que le parc solaire
    grandit (sous-question 2).
    """
    groupes = donnees.groupby(["annee", "heure_decimale"], observed=True)
    return groupes[variable].agg(mediane="median", effectif="size").reset_index()


def profondeur_creux(donnees: pd.DataFrame, variable: str = "demande_nette") -> pd.DataFrame:
    """Creux de mi-journée et remontée du soir, année par année.

    Résume en un point par an la déformation mesurée par `profils_par_annee`.
    """
    par_annee = profils_par_annee(donnees, variable)
    lignes = []
    for annee, p in par_annee.groupby("annee"):
        creux = p[p["heure_decimale"].between(10, 16)]["mediane"].min()
        pic = p[p["heure_decimale"].between(18, 21)]["mediane"].max()
        nuit = p[p["heure_decimale"].between(2, 5)]["mediane"].median()
        lignes.append({"annee": annee, "creux_midi": creux, "pic_soir": pic,
                       "nuit": nuit, "remontee": pic - creux,
                       "creusement": nuit - creux})
    return pd.DataFrame(lignes)


#: Centres approximatifs des régions métropolitaines (latitude, longitude).
CENTRES_REGIONS = {
    "Auvergne-Rhône-Alpes": (45.4, 4.6),
    "Bourgogne-Franche-Comté": (47.2, 4.8),
    "Bretagne": (48.2, -2.9),
    "Centre-Val de Loire": (47.5, 1.7),
    "Grand Est": (48.7, 5.6),
    "Hauts-de-France": (49.9, 2.7),
    "Normandie": (49.1, 0.1),
    "Nouvelle-Aquitaine": (45.2, 0.2),
    "Occitanie": (43.7, 2.0),
    "Pays de la Loire": (47.5, -0.8),
    "Provence-Alpes-Côte d'Azur": (43.9, 6.1),
    "Île-de-France": (48.7, 2.5),
}


def hauteur_solaire(
    horodatage_utc: pd.Series, latitude: float, longitude: float
) -> pd.Series:
    """Sinus de la hauteur du soleil, calculé par pure géométrie.

    Aucune donnée météorologique n'intervient : seuls la date, l'heure UTC et
    les coordonnées comptent. Le résultat vaut 1 au zénith, 0 à l'horizon, et
    devient négatif la nuit.

    Le calcul part de l'heure **UTC** et non de l'heure locale, ce qui écarte
    d'emblée le piège du changement d'heure : 13 h locale ne désigne pas la même
    position du soleil en hiver et en été.
    """
    jour = horodatage_utc.dt.dayofyear
    heure = horodatage_utc.dt.hour + horodatage_utc.dt.minute / 60

    # Déclinaison du soleil, qui varie de -23,45 à +23,45 degrés dans l'année.
    declinaison = np.radians(23.45 * np.sin(2 * np.pi * (284 + jour) / 365))

    # Équation du temps : écart entre midi solaire et midi de l'horloge, en minutes.
    angle_jour = 2 * np.pi * (jour - 81) / 364
    equation_temps = (9.87 * np.sin(2 * angle_jour)
                      - 7.53 * np.cos(angle_jour)
                      - 1.5 * np.sin(angle_jour))

    temps_solaire = heure + longitude / 15 + equation_temps / 60
    angle_horaire = np.radians(15 * (temps_solaire - 12))

    lat = np.radians(latitude)
    return (np.sin(lat) * np.sin(declinaison)
            + np.cos(lat) * np.cos(declinaison) * np.cos(angle_horaire))


def ciel_clair_theorique(
    horodatage_utc: pd.Series, latitude: float, longitude: float
) -> pd.Series:
    """Irradiance théorique par ciel parfaitement clair, en W/m².

    Modèle de Haurwitz (1945), qui ne dépend que de la hauteur du soleil :

        irradiance = 1098 × sin(hauteur) × exp(-0,059 / sin(hauteur))

    Le terme exponentiel traduit l'épaisseur d'atmosphère traversée, plus grande
    quand le soleil est bas. C'est une référence **purement géométrique**, sans
    aucune mesure de nuage : exactement ce qu'il faut pour juger si l'enveloppe
    empirique suit bien la course du soleil.
    """
    sinus = hauteur_solaire(horodatage_utc, latitude, longitude)
    sinus_positif = sinus.where(sinus > 0.01)
    return 1098 * sinus_positif * np.exp(-0.059 / sinus_positif)


def irradiance_extraterrestre(
    horodatage_utc: pd.Series, latitude: float, longitude: float
) -> pd.Series:
    """Irradiance sur un plan horizontal **au sommet de l'atmosphère**, en W/m².

    C'est le dénominateur de l'**indice de clarté** de Liu et Jordan (1960) :

        k_t = irradiance mesurée au sol / irradiance extraterrestre

    Contrairement à `ciel_clair_theorique`, aucun modèle d'atmosphère n'entre en
    jeu, seulement de l'astronomie : la constante solaire, la légère variation de
    la distance Terre-Soleil dans l'année, et la hauteur du soleil.

        irradiance = 1361 × (1 + 0,033 × cos(2π n / 365)) × sin(hauteur)

    Le terme en cosinus vaut l'excentricité de l'orbite : la Terre est environ
    3,3 % plus proche du soleil début janvier. Nul la nuit, par convention.
    """
    jour = horodatage_utc.dt.dayofyear
    correction_distance = 1 + 0.033 * np.cos(2 * np.pi * jour / 365)
    sinus = hauteur_solaire(horodatage_utc, latitude, longitude)
    return (1361 * correction_distance * sinus).clip(lower=0)


def ciel_clair_incline(
    horodatage_utc: pd.Series,
    latitude: float,
    longitude: float,
    inclinaison: float = 30.0,
) -> pd.Series:
    """Irradiance théorique par ciel clair sur un plan **incliné**, en W/m².

    Les panneaux ne sont pas posés à plat mais inclinés, en général vers 30° au
    sud en France. Un plan incliné capte bien mieux le soleil bas de l'hiver
    qu'une surface horizontale, ce qui déforme fortement le profil saisonnier.

    Simplification géométrique utilisée : pour un plan **orienté plein sud**,
    l'angle d'incidence du rayonnement direct se calcule comme la hauteur du
    soleil que verrait une surface horizontale située à la latitude
    `latitude - inclinaison`. Cela évite la formule complète à cinq termes.

    Le modèle sépare deux composantes, comme il est d'usage :

    - le **direct**, dominant par ciel clair, projeté sur le plan incliné ;
    - le **diffus**, supposé isotrope, dont le plan ne voit qu'une fraction
      `(1 + cos(inclinaison)) / 2` puisqu'une partie du ciel lui est masquée.

    Reste une approximation : l'albédo du sol est négligé, et le diffus réel
    n'est pas isotrope. Suffisant pour comparer des **formes saisonnières**,
    insuffisant pour prédire une production en valeur absolue.
    """
    sinus_hauteur = hauteur_solaire(horodatage_utc, latitude, longitude)
    sinus_positif = sinus_hauteur.where(sinus_hauteur > 0.01)

    # Masse d'air traversée, puis rayonnement direct normal (modèle de Meinel).
    masse_air = 1 / sinus_positif
    direct_normal = 1367 * 0.7 ** (masse_air ** 0.678)

    # Global horizontal (Haurwitz), d'où l'on déduit le diffus par différence.
    global_horizontal = 1098 * sinus_positif * np.exp(-0.059 / sinus_positif)
    diffus_horizontal = (global_horizontal - direct_normal * sinus_positif).clip(lower=0)

    # Un plan sud incliné voit le soleil comme une surface horizontale
    # placée à la latitude décalée de l'inclinaison.
    cos_incidence = hauteur_solaire(
        horodatage_utc, latitude - inclinaison, longitude
    ).clip(lower=0)

    facteur_ciel = (1 + np.cos(np.radians(inclinaison))) / 2
    return direct_normal * cos_incidence + diffus_horizontal * facteur_ciel


def indice_ciel_clair(
    donnees: pd.DataFrame,
    fenetre_jours: int = 30,
    quantile: float = 0.95,
    seuil_enveloppe: float = 10.0,
) -> pd.DataFrame:
    """Indicateur de nébulosité déduit de la production solaire seule.

    La production dépend de trois choses : la course du soleil (déterministe),
    la taille du parc (lente) et la couverture nuageuse (seule vraiment variable
    au jour le jour). En estimant ce que le parc produirait **par ciel clair**,
    le rapport isole la nébulosité :

        indice = production observée / production par ciel clair

    Proche de 1, le ciel était dégagé. Proche de 0,3, il était très couvert.

    L'enveloppe de ciel clair est estimée **sans aucune donnée météorologique**,
    par un quantile haut glissant calculé à créneau horaire fixé : sur trente
    jours, il se trouve forcément quelques journées dégagées. La fenêtre étant
    glissante, elle suit automatiquement la croissance du parc, ce qui rend les
    années comparables entre elles.

    Réglages figés avant construction (journal du 2026-07-28), à ne pas ajuster
    au vu des résultats de validation, faute de quoi l'outil serait calé sur son
    propre examen :

    - `fenetre_jours` = 30 : assez long pour contenir des journées dégagées,
      assez court pour suivre la course saisonnière du soleil ;
    - `quantile` = 0,95 : approche le maximum atteignable sans se caler sur une
      valeur aberrante isolée ;
    - maille **créneau horaire × région** : la course du soleil et le parc
      diffèrent selon l'heure et le lieu ;
    - `seuil_enveloppe` : en deçà, le rapport n'a pas de sens et diverge. Écarte
      les créneaux nocturnes.

    ⚠️ **NON VALIDÉ à ce jour. Ne pas s'en servir comme arbitre.**

    Trois tentatives de validation ont échoué sans qu'aucune ne teste réellement
    l'enveloppe (journal du 2026-07-28, section 9) : la première confondait
    saisonnalité géométrique et météorologique, la deuxième était **circulaire**
    (l'enveloppe étant un quantile des mêmes données, environ 5 % des journées la
    dépassent par construction), la troisième reposait sur une inclinaison de
    panneaux supposée alors que le parc français est bimodal, moitié toitures et
    moitié centrales au sol.

    Deux tests propres, indépendants de tout modèle, restent en sa faveur : la
    cohérence spatiale (corrélation entre régions décroissant avec la distance,
    r = −0,945) et le comportement des journées extrêmes.

    Sa validation exige une **source météorologique externe**. Tant qu'elle n'est
    pas faite, cet indice ne doit pas servir à départager quoi que ce soit.

    Limites, connues d'avance :

    - l'indice capte **tout ce qui réduit la production**, pas seulement les
      nuages : écrêtement, neige, pannes, maintenance ;
    - il est **circulaire pour l'explication**. Dérivé de la production, il ne
      peut pas servir à l'expliquer. C'est un instrument de validation, jamais
      une variable explicative ;
    - il est **instable en hiver** : dans un mois durablement couvert,
      l'enveloppe se cale trop bas et une éclaircie fait exploser le rapport,
      jusqu'à 3,75 observé en janvier.

    Returns
    -------
    Les données d'entrée, enrichies de `enveloppe_ciel_clair` et de `indice_ciel_clair`.
    """
    resultat = donnees.sort_values(["libelle_region", "heure_decimale", "date_heure"]).copy()

    groupes = resultat.groupby(["libelle_region", "heure_decimale"], observed=True)["solaire"]
    resultat["enveloppe_ciel_clair"] = groupes.transform(
        lambda serie: serie.rolling(fenetre_jours, min_periods=fenetre_jours // 2)
        .quantile(quantile)
    )

    exploitable = resultat["enveloppe_ciel_clair"] > seuil_enveloppe
    resultat["indice_ciel_clair"] = (
        resultat["solaire"].where(exploitable) / resultat["enveloppe_ciel_clair"]
    )
    return resultat


def indice_journalier(donnees: pd.DataFrame) -> pd.DataFrame:
    """Moyenne journalière de l'indice de ciel clair, par région.

    Résume la nébulosité d'une journée en un nombre, en agrégeant les créneaux
    exploitables. Sert aux tests de validation.
    """
    exploitables = donnees.dropna(subset=["indice_ciel_clair"])
    return (
        exploitables.groupby(["libelle_region", "date"], observed=True)
        .agg(indice=("indice_ciel_clair", "mean"),
             creneaux=("indice_ciel_clair", "size"))
        .reset_index()
    )


def annees_incompletes(donnees: pd.DataFrame, seuil_jours: int = 350) -> list[int]:
    """Années couvrant moins de `seuil_jours` jours distincts.

    Une année tronquée n'est pas comparable aux autres : si elle s'arrête en
    avril, elle ne contient que des mois froids et sa consommation moyenne paraît
    anormalement élevée. Ce n'est pas une rupture de méthode mais un effet de
    saison, et c'est plus trompeur encore parce que rien ne le signale.
    """
    jours = donnees.groupby("annee")["date"].nunique()
    return sorted(jours[jours < seuil_jours].index.tolist())


def impact_negatifs(donnees: pd.DataFrame, filiere: str = "solaire") -> dict:
    """Poids réel des valeurs négatives de production, pour le dire plutôt que le corriger.

    Les valeurs négatives disparaissent à partir de 2020 (changement de convention
    RTE). Plutôt que d'harmoniser en les ramenant à zéro, ce qui détruirait
    l'information d'autoconsommation, on mesure leur poids et on l'affiche.
    """
    avant = donnees[donnees["annee"] < 2020]
    serie = avant[filiere]
    negatives = serie[serie < 0]
    niveau = donnees["consommation"].median()
    return {
        "lignes": len(negatives),
        "part_%": round(100 * len(negatives) / len(serie), 2) if len(serie) else 0.0,
        "mediane": float(negatives.median()) if len(negatives) else 0.0,
        "minimum": float(serie.min()) if len(serie) else 0.0,
        "poids_relatif_%": round(abs(negatives.median()) / niveau * 100, 3)
        if len(negatives) and niveau else 0.0,
    }


def indicateurs_creux(profils: pd.DataFrame, colonne: str = "mediane") -> pd.DataFrame:
    """Creux de mi-journée (10 h à 16 h) et remontée jusqu'au pic du soir (18 h à 21 h)."""
    lignes = []
    for saison in SAISONS:
        p = profils[profils["saison"] == saison]
        if p.empty:
            continue
        creux = p[p["heure_decimale"].between(10, 16)][colonne].min()
        pic = p[p["heure_decimale"].between(18, 21)][colonne].max()
        lignes.append({"saison": saison, "creux_midi": creux,
                       "pic_soir": pic, "remontee": pic - creux})
    return pd.DataFrame(lignes)


def completude_colonnes(donnees: pd.DataFrame) -> pd.DataFrame:
    """Taux de remplissage de chaque colonne, en pourcentage."""
    taux = donnees.notna().mean().mul(100).sort_values(ascending=False)
    return taux.rename("completude").reset_index(names="colonne")


def completude_par_annee(donnees: pd.DataFrame, colonnes: list[str]) -> pd.DataFrame:
    """Taux de remplissage année par année, pour repérer les ruptures de méthode."""
    resultat = donnees.groupby("annee")[colonnes].apply(lambda x: x.notna().mean().mul(100))
    return resultat.round(1)


def valeurs_negatives(donnees: pd.DataFrame, filieres: list[str]) -> pd.DataFrame:
    """Compte et ampleur des productions négatives, qui traduisent une consommation."""
    lignes = []
    for filiere in filieres:
        serie = donnees[filiere]
        negatives = serie[serie < 0]
        lignes.append({
            "filiere": filiere,
            "lignes_negatives": len(negatives),
            "part_%": round(100 * len(negatives) / serie.notna().sum(), 2),
            "minimum": serie.min(),
            "mediane_negatifs": negatives.median() if len(negatives) else None,
        })
    return pd.DataFrame(lignes)
