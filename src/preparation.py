"""Chargement et nettoyage des données éCO2mix régionales.

Ce module est la **source unique** du nettoyage : tous les scripts d'analyse
appellent `charger_donnees()` plutôt que de refaire leurs propres corrections.
Toute règle de nettoyage se décide donc ici, une seule fois.

Nettoyages appliqués (chacun justifié par une vérification sur les données) :

1. Suppression de `column_30`, colonne parasite entièrement vide.
2. Conversion de `eolien` (stockée en texte) en numérique ; les marqueurs
   `'ND'` et `'-'` deviennent des valeurs manquantes.
3. Suppression des lignes sans `consommation` (début de série de janvier 2013,
   entièrement vides, sans information exploitable).
4. Déduplication sur (région, horodatage). Les 672 lignes concernées tombent
   toutes sur les 14 dates de passage à l'heure d'été (dernier dimanche de
   mars, de 2013 à 2026), où l'heure locale est ambiguë.
5. Ajout d'un horodatage en **heure locale** (Europe/Paris).

Point de vigilance sur le fuseau horaire
----------------------------------------
`date_heure` est en **UTC**, alors que les colonnes `date` et `heure` sont en
heure locale. Raisonner sur l'heure UTC fabriquerait une fausse déformation
saisonnière : le pic solaire moyen y tombe à 11 h en juin contre 12 h en
décembre, un décalage dû au seul changement d'heure. En heure locale il tombe
à 13 h dans les deux cas. Les profils journaliers doivent donc utiliser
`heure_decimale`, dérivée de l'heure locale.

Note sur la colonne `nature`
----------------------------
`nature` distingue les données définitives (jusqu'à 2024, validées) des données
consolidées (2025 et 2026, susceptibles de révision). Ce n'est pas un doublon
mais un découpage temporel. On conserve les deux : les filtrer supprimerait les
années les plus riches en solaire. La fonction `resume_nature()` permet de
vérifier cette répartition.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RACINE_PROJET = Path(__file__).resolve().parent.parent
CHEMIN_DEFAUT = RACINE_PROJET / "data" / "eco2mix_regional.parquet"

FUSEAU_LOCAL = "Europe/Paris"

# Saisons météorologiques : mois -> libellé.
_SAISON_PAR_MOIS = {
    12: "Hiver", 1: "Hiver", 2: "Hiver",
    3: "Printemps", 4: "Printemps", 5: "Printemps",
    6: "Été", 7: "Été", 8: "Été",
    9: "Automne", 10: "Automne", 11: "Automne",
}
SAISONS = ["Hiver", "Printemps", "Été", "Automne"]


def charger_donnees(chemin: Path | str | None = None, verbeux: bool = True) -> pd.DataFrame:
    """Charge les données éCO2mix et applique le nettoyage de référence.

    Parameters
    ----------
    chemin : chemin du fichier Parquet. Par défaut `data/eco2mix_regional.parquet`.
    verbeux : si True, affiche un compte rendu de ce qui a été retiré.

    Returns
    -------
    DataFrame nettoyé, enrichi des colonnes `date_heure_locale`,
    `heure_decimale`, `annee`, `mois`, `saison`, `jour_semaine` et
    `demande_nette`.
    """
    chemin = Path(chemin) if chemin is not None else CHEMIN_DEFAUT
    if not chemin.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {chemin}\n"
            "Lance d'abord : uv run python src/download.py"
        )

    df = pd.read_parquet(chemin)
    lignes_initiales = len(df)

    # 1. Colonne parasite entièrement vide.
    df = df.drop(columns=["column_30"], errors="ignore")

    # 2. 'eolien' est stockée en texte ; 'ND' et '-' signalent une absence de mesure.
    df["eolien"] = pd.to_numeric(df["eolien"], errors="coerce")

    # 3. Lignes sans consommation : aucune information exploitable.
    df = df.dropna(subset=["consommation"])
    apres_vides = len(df)

    # 4. Doublons d'horodatage (changements d'heure de mars).
    df = df.drop_duplicates(subset=["libelle_region", "date_heure"], keep="first")
    apres_doublons = len(df)

    # 5. Heure locale : indispensable pour comparer les saisons sans biais de fuseau.
    df["date_heure_locale"] = df["date_heure"].dt.tz_convert(FUSEAU_LOCAL)
    locale = df["date_heure_locale"].dt
    df["heure_decimale"] = locale.hour + locale.minute / 60
    df["annee"] = locale.year
    df["mois"] = locale.month
    df["jour_semaine"] = locale.dayofweek
    df["saison"] = pd.Categorical(
        df["mois"].map(_SAISON_PAR_MOIS), categories=SAISONS, ordered=True
    )

    # Variable centrale du projet. Reste indéfinie là où l'éolien manque :
    # on ne comble pas artificiellement, le trou doit rester visible.
    df["demande_nette"] = df["consommation"] - df["solaire"] - df["eolien"]

    df = df.sort_values(["libelle_region", "date_heure"]).reset_index(drop=True)

    if verbeux:
        print(f"Lignes chargées          : {lignes_initiales:>10,}")
        print(f"  sans consommation      : {lignes_initiales - apres_vides:>10,} retirées")
        print(f"  doublons d'horodatage  : {apres_vides - apres_doublons:>10,} retirées")
        print(f"Lignes retenues          : {len(df):>10,}")
        print(f"Période (heure locale)   : {df['date_heure_locale'].min()} "
              f"-> {df['date_heure_locale'].max()}")
        indefinies = int(df["demande_nette"].isna().sum())
        print(f"Demande nette indéfinie  : {indefinies:>10,} (éolien manquant)")

    return df


def resume_nature(df: pd.DataFrame) -> pd.DataFrame:
    """Répartition des natures de données par année (définitives / consolidées)."""
    return pd.crosstab(df["annee"], df["nature"])


def filtrer(
    df: pd.DataFrame,
    regions: list[str] | None = None,
    annees: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """Restreint le jeu à certaines régions et à une plage d'années incluse."""
    resultat = df
    if regions is not None:
        resultat = resultat[resultat["libelle_region"].isin(regions)]
    if annees is not None:
        debut, fin = annees
        resultat = resultat[resultat["annee"].between(debut, fin)]
    return resultat.copy()
