"""Calculs d'analyse, indépendants de tout affichage.

Les fonctions de ce module renvoient des tableaux, jamais des figures. Elles
sont appelées aussi bien par les scripts de `notebooks/` que par le tableau de
bord, ce qui évite que les deux divergent.
"""

from __future__ import annotations

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
