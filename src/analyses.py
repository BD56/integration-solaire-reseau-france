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
    causale: bool = False,
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

    ✅ **VALIDÉ le 2026-07-28, mais SUPPLANTÉ. Utilisable, rarement utile.**

    ⚠️ Un premier verdict de **rejet** a été publié puis **retiré le même jour**
    après revue : il reposait sur une comparaison qui n'était pas à base
    identique (voir `indice_journalier`). L'indice était résumé en moyenne de
    rapports quand la référence k_t et le concurrent `tch_solaire` étaient tous
    deux des rapports de cumuls. L'écart mesuré était un artefact d'agrégation.

    Comparaison corrigée, Spearman à l'indice de clarté k_t d'ERA5, médiane sur
    les 12 régions, 2021-2024 (`notebooks/07_validation_indice.py`) :

        indice, enveloppe causale       0,820   -> l'emporte dans 11 régions / 12
        tch_solaire, mêmes créneaux     0,798

    Volet A du protocole : 0,820 ≥ 0,80, donc **validé**. Volet B : l'indice bat
    le concurrent trivial, donc **utile**. Le gain reste modeste, +0,022.

    ➡️ **Employer néanmoins `shortwave_radiation` d'ERA5** (via `src.meteo`, avec
    `irradiance_extraterrestre()` pour former k_t) dès qu'une source externe est
    acceptable. Non pas parce que l'indice serait mauvais, mais parce qu'il reste
    **circulaire pour l'explication** : dérivé de la production, il ne peut pas
    servir à l'expliquer. Sa niche est étroite : mesurer la nébulosité quand on
    n'a que la production, ce qui n'est plus le cas de ce projet.

    Trois tentatives de validation antérieures avaient échoué sans qu'aucune ne
    teste réellement l'enveloppe (journal du 2026-07-28, section 9) : la première
    confondait saisonnalité géométrique et météorologique, la deuxième était
    **circulaire** (l'enveloppe étant un quantile des mêmes données, environ 5 %
    des journées la dépassent par construction), la troisième reposait sur une
    inclinaison de panneaux supposée alors que le parc français est bimodal.

    Défaut de construction restant, mesuré à la revue : l'enveloppe par défaut
    (`causale=False`) **contient le jour évalué**, donc 4,69 % des créneaux
    dépassent leur propre enveloppe. Passer `causale=True` supprime cette fuite
    pour un coût nul (0,820 contre 0,823). **C'est indispensable pour tout usage
    prédictif**, où utiliser le jour évalué serait disqualifiant.

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

    def enveloppe(serie: pd.Series) -> pd.Series:
        glissante = serie.rolling(fenetre_jours, min_periods=fenetre_jours // 2)
        if causale:
            # `shift(1)` d'abord : la fenêtre porte alors sur les jours J-30 à
            # J-1, sans jamais contenir le jour évalué.
            return serie.shift(1).rolling(
                fenetre_jours, min_periods=fenetre_jours // 2
            ).quantile(quantile)
        return glissante.quantile(quantile)

    groupes = resultat.groupby(["libelle_region", "heure_decimale"], observed=True)["solaire"]
    resultat["enveloppe_ciel_clair"] = groupes.transform(enveloppe)

    exploitable = resultat["enveloppe_ciel_clair"] > seuil_enveloppe
    resultat["indice_ciel_clair"] = (
        resultat["solaire"].where(exploitable) / resultat["enveloppe_ciel_clair"]
    )
    return resultat


def indice_journalier(donnees: pd.DataFrame, methode: str = "cumuls") -> pd.DataFrame:
    """Résumé journalier de l'indice de ciel clair, par région.

    Deux conventions d'agrégation, et le choix n'est pas anodin :

    - `"cumuls"` (par défaut) : **rapport des cumuls**, `Σ solaire / Σ enveloppe`
      sur les créneaux exploitables. C'est la convention standard des indices de
      clarté, et celle appliquée à l'indice de clarté k_t auquel on compare.
    - `"moyenne"` : **moyenne des rapports** créneau par créneau. Conservée
      uniquement pour rejouer les résultats antérieurs au 2026-07-28.

    ⚠️ La convention `"moyenne"` était le défaut jusqu'au 2026-07-28, et c'est
    **elle qui a produit un verdict de rejet erroné** : elle donne un poids égal
    aux créneaux d'aube et de crépuscule, où le rapport est très bruité, alors
    que la référence k_t et le concurrent `tch_solaire` sont tous deux des
    rapports de cumuls. La comparaison n'était donc pas à base identique. Sur
    2021-2024, la médiane passe de 0,763 (moyenne) à 0,823 (cumuls), et le
    nombre de régions où l'indice l'emporte de 0 sur 12 à 11 sur 12.
    """
    exploitables = donnees.dropna(subset=["indice_ciel_clair"])
    groupes = exploitables.groupby(["libelle_region", "date"], observed=True)

    if methode == "moyenne":
        resume = groupes.agg(indice=("indice_ciel_clair", "mean"),
                             creneaux=("indice_ciel_clair", "size"))
        return resume.reset_index()

    if methode != "cumuls":
        raise ValueError(f"méthode inconnue : {methode!r} (attendu 'cumuls' ou 'moyenne')")

    resume = groupes.agg(solaire=("solaire", "sum"),
                         enveloppe=("enveloppe_ciel_clair", "sum"),
                         creneaux=("indice_ciel_clair", "size"))
    resume["indice"] = resume["solaire"] / resume["enveloppe"]
    return resume.reset_index()[["libelle_region", "date", "indice", "creneaux"]]


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

    # Périmètre du niveau de référence : AVANT 2020 également, pas toute la
    # période. Comparer une médiane d'avant 2020 à un niveau calculé sur
    # 2013-2026 mélangeait deux périmètres pour rien (corrigé le 2026-07-28).
    niveau = avant["consommation"].median()

    # Deux parts distinctes, parce que les confondre a déjà induit en erreur :
    # `part_avant_2020_%` rapporte aux seuls relevés d'avant 2020, tandis que
    # `part_periode_%` rapporte à l'ensemble affiché. La première vaut environ le
    # double de la seconde, et c'est la seconde que l'on veut quand on écrit
    # « de la période » (corrigé le 2026-07-28).
    return {
        "lignes": len(negatives),
        "part_avant_2020_%": round(100 * len(negatives) / len(serie), 2) if len(serie) else 0.0,
        "part_periode_%": round(100 * len(negatives) / len(donnees), 2) if len(donnees) else 0.0,
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


# ---------------------------------------------------------------------------
# Sous-question 3 : équilibrage. Ces fonctions sont partagées entre
# `notebooks/04_equilibrage.py` et le tableau de bord, pour qu'un chiffre affiché
# soit toujours celui que le script produit.
# ---------------------------------------------------------------------------

MI_JOURNEE, NUIT, SOIREE = (11, 15), (2, 5), (16, 21)
SEUIL_VALIDE, SEUIL_REJETE = 0.7, 0.3

COLONNES_EQUILIBRAGE = ["solaire", "consommation", "demande_nette", "pompage",
                        "ech_physiques", "nucleaire", "hydraulique", "thermique"]


def trame_nationale(donnees: pd.DataFrame) -> pd.DataFrame:
    """Somme des 12 régions, pas de temps par pas de temps.

    À l'échelle régionale, `ech_physiques` ne mesure pas un équilibrage : une
    région n'a aucune obligation de s'équilibrer, elle évacue son solde chez la
    voisine. En additionnant les 12 régions, les flux interrégionaux s'annulent
    deux à deux et il ne reste que le solde de la France avec l'étranger.

    ⚠️ `sum()` de pandas ignore les `NaN` : un créneau où une région manque
    serait sommé sur 11 régions et non 12, ce qui fabriquerait un creux
    artificiel de plusieurs gigawatts. La `demande_nette` est donc mise à `NaN`
    sur ces créneaux (96 pas de temps de 2013, sans éolien).

    Le remède est appliqué **à cette seule colonne**. Un filtre global effacerait
    `pompage` et `nucleaire` sur toute la période antérieure à 2021, où une case
    vide ne signifie pas « mesure manquante » mais « pas de centrale ici ».
    """
    cles = ["date_heure", "date", "annee", "heure_decimale"]
    national = donnees.groupby(cles, as_index=False)[COLONNES_EQUILIBRAGE].sum()
    complet = (donnees.groupby(cles)["demande_nette"].count()
               == donnees["libelle_region"].nunique())
    national = national.merge(complet.rename("douze_regions").reset_index(), on=cles)
    national.loc[~national["douze_regions"], "demande_nette"] = np.nan
    return national


def profil_horaire_par_annee(trame: pd.DataFrame, colonne: str) -> pd.DataFrame:
    """Profil horaire moyen, une ligne par année, une colonne par demi-heure."""
    return trame.pivot_table(index="annee", columns="heure_decimale",
                             values=colonne, aggfunc="mean")


def moyenne_entre(profil: pd.DataFrame, bornes: tuple) -> pd.Series:
    """Moyenne d'un profil horaire sur une plage d'heures."""
    colonnes = [h for h in profil.columns if bornes[0] <= h <= bornes[1]]
    return profil[colonnes].mean(axis=1)


def rampe_du_soir(trame: pd.DataFrame, bornes: tuple = SOIREE,
                  colonne: str = "demande_nette") -> pd.Series:
    """Variation maximale par demi-heure en soirée, médiane par année.

    ⚠️ Le `.diff()` est calculé **par journée**. Appliqué à une trame déjà
    filtrée sur la fenêtre du soir, il enjamberait la nuit et comparerait le
    dernier créneau de la veille au premier du jour : un saut de dix-neuf heures,
    qui portait le maximum journalier dans 13,80 % des cas et inversait le
    verdict de l'hypothèse (journal du 2026-07-28, suite 8).
    """
    fenetre = trame[trame["heure_decimale"].between(*bornes)].sort_values("date_heure").copy()
    fenetre["variation"] = fenetre.groupby("date", observed=True)[colonne].diff()
    return fenetre.groupby(["annee", "date"])["variation"].max().groupby("annee").median()


def verdicts_equilibrage(trame: pd.DataFrame) -> pd.DataFrame:
    """Les quatre hypothèses de la sous-question 3, avec leur critère préenregistré.

    Chaque critère a été écrit **avant** tout calcul : validée si |r| > 0,7 dans
    le sens prédit, rejetée si |r| < 0,3 ou si le sens est contraire. Les
    hypothèses rejetées sont conservées, un rejet étant un résultat.
    """
    pompage = profil_horaire_par_annee(trame, "pompage").abs()
    part_midi = moyenne_entre(pompage, MI_JOURNEE) / pompage.mean(axis=1)

    echanges = moyenne_entre(profil_horaire_par_annee(trame, "ech_physiques"), MI_JOURNEE)

    nucleaire = profil_horaire_par_annee(trame, "nucleaire")
    rapport = moyenne_entre(nucleaire, MI_JOURNEE) / moyenne_entre(nucleaire, NUIT)

    rampe = rampe_du_soir(trame)

    lignes = []
    for libelle, serie, sens in [
        ("H1, le pompage se déplace vers la mi-journée", part_midi, +1),
        ("H2, les échanges évacuent le surplus de midi", echanges, -1),
        ("H3, le nucléaire module", rapport, -1),
        ("H4, la remontée du soir s'accélère", rampe, +1),
    ]:
        r = float(np.corrcoef(serie.index, serie.values)[0, 1])
        bon_sens = np.sign(r) == sens
        if abs(r) > SEUIL_VALIDE and bon_sens:
            etat = "validée"
        elif abs(r) < SEUIL_REJETE or not bon_sens:
            etat = "rejetée"
        else:
            etat = "indécise"
        lignes.append({"hypothese": libelle, "r": round(r, 3), "etat": etat})
    return pd.DataFrame(lignes)


def temoin_saisonnier(trame: pd.DataFrame) -> pd.DataFrame:
    """Le même effet est-il présent en été et absent en hiver ?

    H1, H3 et H4 sont des corrélations contre l'année sur treize points : elles
    établissent une régularité, pas une cause. Ce témoin n'est pas une
    corrélation contre l'année : si le solaire est bien la cause, l'effet doit
    être fort en été et faible en hiver. C'est un test qui peut échouer, et H1
    échoue effectivement.
    """
    mois_trame = pd.to_datetime(trame["date"]).dt.month
    lignes = []
    for saison, mois in [("été", [6, 7, 8]), ("hiver", [12, 1, 2])]:
        part = trame[mois_trame.isin(mois)]
        pompage = profil_horaire_par_annee(part, "pompage").abs()
        midi = moyenne_entre(pompage, MI_JOURNEE)
        nucleaire = profil_horaire_par_annee(part, "nucleaire")
        rapport = moyenne_entre(nucleaire, MI_JOURNEE) / moyenne_entre(nucleaire, NUIT)
        rampe = rampe_du_soir(part)
        conso = rampe_du_soir(part, colonne="consommation")
        lignes.append({
            "saison": saison,
            "pompage de mi-journée": f"×{midi.iloc[-1] / midi.iloc[0]:.2f}",
            "rapport nucléaire midi/nuit": f"{rapport.iloc[0]:.4f} → {rapport.iloc[-1]:.4f}",
            "rampe du soir (r)": round(float(np.corrcoef(rampe.index, rampe.values)[0, 1]), 3),
            "témoin consommation (r)": round(float(np.corrcoef(conso.index, conso.values)[0, 1]), 3),
        })
    return pd.DataFrame(lignes)


def sensibilite_rampe(trame: pd.DataFrame) -> pd.DataFrame:
    """Le verdict de H4 tient-il quand on fait varier la fenêtre du soir ?

    Règle de méthode du projet : une mesure qui dépend de bornes choisies à la
    main doit voir ses bornes varier avant publication.
    """
    lignes = []
    for bornes in [(16, 21), (17, 22), (15, 21), (16, 22), (17, 21), (18, 22), (14, 23)]:
        serie = rampe_du_soir(trame, bornes)
        lignes.append({
            "fenêtre du soir": f"{bornes[0]} h à {bornes[1]} h",
            "r": round(float(np.corrcoef(serie.index, serie.values)[0, 1]), 3),
        })
    return pd.DataFrame(lignes)


def creneaux_par_jour(donnees: pd.DataFrame) -> pd.DataFrame:
    """Nombre de créneaux par journée et par région, pour vérifier les bascules d'heure.

    Une journée normale compte **48** créneaux de 30 minutes. Deux écarts sont
    attendus et légitimes, tout autre écart serait un trou de données :

    - **46** le dimanche de mars, où l'horloge saute de 02:00 à 03:00 et où le
      jour ne dure que 23 heures. Les deux étiquettes fictives ont été retirées
      au chargement ;
    - **47** le tout premier jour de la série, qui commence à 00:30.

    Octobre ne produit **pas** d'anomalie ici : la source publie bien 48
    étiquettes locales, c'est du côté UTC qu'il manque une heure.
    """
    par_jour = donnees.groupby(["libelle_region", "date"], observed=True).size()
    distribution = par_jour.value_counts().sort_index()
    explications = {
        46: "dimanche de passage à l'heure d'été, journée de 23 heures",
        47: "premier jour de la série, qui commence à 00:30",
        48: "journée complète",
    }
    return pd.DataFrame({
        "creneaux": distribution.index,
        "journees_x_regions": distribution.values,
        "explication": [explications.get(n, "⚠️ inattendu, à investiguer")
                        for n in distribution.index],
    })


def valeurs_impossibles(donnees: pd.DataFrame) -> pd.DataFrame:
    """Valeurs qui sortent des bornes physiques de leur définition.

    Un taux de charge est une production rapportée à la puissance installée : il
    ne peut pas dépasser 100 %. Quand il le fait, c'est la **référence de
    puissance installée qui est en retard** sur le parc réel, pas la production
    qui est aberrante. Conséquence pratique : `capacite_installee()` inverse
    cette variable, ses valeurs sont donc sous-estimées aux mêmes endroits.

    Le taux de couverture, lui, peut légitimement dépasser 100 % : une région
    peu consommatrice et bien ensoleillée exporte son surplus.
    """
    lignes = []
    for colonne in [c for c in donnees.columns if c.startswith("tch_")]:
        serie = donnees[colonne].dropna()
        if serie.empty:
            continue
        hors = serie[serie > 100]
        if hors.empty:
            continue
        concernees = donnees.loc[hors.index, "libelle_region"].value_counts()
        lignes.append({
            "variable": colonne,
            "lignes_au_dessus_de_100_%": len(hors),
            "part_%": round(100 * len(hors) / len(serie), 4),
            "maximum_%": round(float(serie.max()), 2),
            "regions_concernees": ", ".join(
                f"{r} ({n})" for r, n in concernees.head(4).items()
            ),
        })
    return pd.DataFrame(lignes)


def part_reconstruite(donnees: pd.DataFrame) -> pd.DataFrame:
    """Part des taux de couverture recalculés par le projet, année par année.

    Avant 2020, RTE ne publiait pas les `tco_`. Le projet les reconstruit par
    `100 × filière / consommation`, formule vérifiée sur la période où les deux
    coexistent (erreur médiane de 0,003 point). Cette table existe pour qu'aucun
    lecteur ne confonde une valeur publiée par RTE et une valeur du projet.
    """
    if "tco_reconstruit" not in donnees.columns:
        return pd.DataFrame(columns=["annee", "part_reconstruite_%", "origine"])
    part = donnees.groupby("annee")["tco_reconstruit"].mean().mul(100).round(1)
    return pd.DataFrame({
        "annee": part.index,
        "part_reconstruite_%": part.values,
        "origine": ["reconstruit par le projet" if p > 50 else "publié par RTE"
                    for p in part.values],
    })


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
