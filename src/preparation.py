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
4. Suppression des créneaux locaux 02:00 et 02:30 du dimanche de passage à
   l'heure d'été. Voir la section sur les changements d'heure ci-dessous.
5. Ajout d'un horodatage en **heure locale** (Europe/Paris).

Point de vigilance sur le fuseau horaire
----------------------------------------
`date_heure` est en **UTC**, alors que les colonnes `date` et `heure` sont en
heure locale. Les deux repères ne sont pas interchangeables, et il faut savoir
lequel on veut.

Mesuré (Nouvelle-Aquitaine, 2023-2025, heure du maximum du profil moyen) :

| Repère | Juin | Décembre |
|---|---|---|
| UTC | 12 h | 12 h |
| Heure locale | **14 h** | **13 h** |

C'est **l'UTC qui est stationnaire**, et l'heure locale qui se déplace d'une
heure : le midi solaire ne bouge pas, c'est l'horloge civile qui saute au
changement d'heure.

Le projet raisonne néanmoins en **heure locale**, et c'est un choix délibéré :
l'objet d'étude est la **demande humaine**, qui suit l'horloge et non le soleil.
Les profils journaliers utilisent donc `heure_decimale`. Pour tout ce qui relève
de la géométrie solaire (hauteur du soleil, ciel clair, irradiance théorique),
c'est l'inverse : `src/analyses.py` calcule en UTC, précisément parce que c'est
le repère stable.

⚠️ Cette section affirmait exactement le contraire jusqu'au 2026-07-28 (« le pic
tombe à 13 h dans les deux cas en heure locale »). L'erreur avait été retractée
au journal dès le 2026-07-26 mais n'était jamais redescendue jusqu'ici, dans le
module qui fait pourtant référence. Aucun résultat n'en dépendait, la convention
retenue étant la bonne pour de meilleures raisons que celles invoquées.

Changements d'heure : un doublon en mars, un trou en octobre
------------------------------------------------------------
La source publie **toujours 48 créneaux de 30 minutes par jour**, y compris les
jours de bascule, ce qui produit deux anomalies de nature opposée.

**Mars** (l'horloge saute de 02:00 à 03:00, le jour dure 23 heures). Les
créneaux locaux 02:00 et 02:30 n'existent pas, mais sont publiés quand même et
retombent sur les mêmes instants UTC que 03:00 et 03:30. Aucune donnée ne
manque : le jour compte bien 46 horodatages UTC distincts, soit sa durée réelle.
On retire donc les deux étiquettes fictives. Combler quoi que ce soit ici
reviendrait à inventer des observations pour un moment qui n'a pas existé.

**Octobre** (l'horloge recule de 03:00 à 02:00, le jour dure 25 heures).
L'heure locale 02:00 à 02:59 a lieu deux fois, mais n'est publiée qu'une seule
fois, pour la seconde occurrence. La première n'est enregistrée nulle part :
il manque une heure réelle (créneaux 00:00 et 00:30 UTC), soit **312** créneaux
sur l'ensemble du jeu (0,011 %), pour 13 bascules d'octobre présentes dans les
données (2013 à 2025) × 12 régions × 2 créneaux.

Ne pas confondre avec le compte de **mars**, qui vaut 336 : les bascules de mars
sont au nombre de 14 (2013 à 2026), le jeu s'arrêtant fin avril 2026.

⚠️ **À traiter pour un futur volet de modélisation ou de prévision.** À cause du
trou d'octobre, la série UTC n'est **pas une grille régulière** : on y observe un
saut de 1 h 30 une fois par an et par région.

Ce que cela coûte, mesuré plutôt qu'estimé. Le problème n'est **pas** une perte
d'information : le créneau absent est nocturne, le solaire y vaut 0,07 MW en
moyenne, et la consommation y est à son plancher. Le problème est
l'**indexation** : un décalage construit par position (reculer de 48 lignes pour
viser « la même heure hier ») ramène 25 heures en arrière et non 24, sur les
lignes qui suivent le trou.

    lignes concernées        7 488 sur 2 803 620, soit 0,267 %
    erreur de consommation   médiane 135 MW, moyenne 170 MW, maximum 1 381 MW
                             soit 3,33 % du niveau médian

Ce n'est donc pas bloquant, et l'appeler ainsi serait exagéré. C'est un piège
silencieux, qui ne fait pas échouer un calcul mais le laisse dériver sans
prévenir, et certaines bibliothèques de séries temporelles exigeront de toute
façon un index à pas constant.

Trois traitements possibles : **écarter** les treize journées concernées (le plus
propre, coût 0,03 % des données), **raisonner en heure locale** où la grille est
régulière, ou **interpoler** ces créneaux (erreur médiane mesurée à 65 MW, soit
3,2 % du niveau nocturne) **à condition de marquer les lignes imputées par une
colonne dédiée**, pour qu'aucune analyse ne confonde une valeur observée et une
valeur reconstruite.

La leçon générale dépasse ce trou précis : **vérifier la régularité d'une grille
avant de la supposer**, plutôt que de mémoriser cette anomalie-ci.

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

# Filières pour lesquelles RTE publie un taux de couverture (TCO).
FILIERES_TCO = ["solaire", "eolien", "hydraulique", "thermique", "bioenergies", "nucleaire"]

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

    # 4. Créneaux locaux fictifs du passage à l'heure d'été (02:00 et 02:30 de mars).
    # Parmi deux lignes partageant le même instant UTC, l'étiquette locale la plus
    # petite est celle de l'heure supprimée par la bascule : c'est celle qu'on retire.
    doublons = df.duplicated(subset=["libelle_region", "date_heure"], keep=False)
    etiquette_minimale = df.groupby(["libelle_region", "date_heure"])["heure"].transform("min")
    df = df[~(doublons & (df["heure"] == etiquette_minimale))]
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

    # Deux définitions, calculées côte à côte plutôt que d'en imposer une.
    # `demande_nette` suit la convention du secteur : on soustrait toute la
    # production renouvelable non pilotable, solaire et éolien confondus.
    # `demande_nette_solaire` isole l'objet d'étude du projet. L'écart entre les
    # deux mesure précisément ce qu'apporte l'éolien, au lieu de le mélanger.
    # `demande_nette` reste indéfinie là où l'éolien manque (96 lignes) : on ne
    # comble pas artificiellement, le trou doit rester visible.
    df["demande_nette"] = df["consommation"] - df["solaire"] - df["eolien"]
    df["demande_nette_solaire"] = df["consommation"] - df["solaire"]

    # Reconstruction des taux de couverture absents avant 2020 (voir completer_tco).
    df = completer_tco(df)

    df = df.sort_values(["libelle_region", "date_heure"]).reset_index(drop=True)

    if verbeux:
        print(f"Lignes chargées          : {lignes_initiales:>10,}")
        print(f"  sans consommation      : {lignes_initiales - apres_vides:>10,} retirées")
        print(f"  créneaux fictifs mars  : {apres_vides - apres_doublons:>10,} retirés")
        print(f"Lignes retenues          : {len(df):>10,}")
        print(f"Période (heure locale)   : {df['date_heure_locale'].min()} "
              f"-> {df['date_heure_locale'].max()}")
        indefinies = int(df["demande_nette"].isna().sum())
        print(f"Demande nette indéfinie  : {indefinies:>10,} (éolien manquant)")
        reconstruites = int(df["tco_reconstruit"].sum())
        print(f"Taux de couverture       : {reconstruites:>10,} lignes reconstruites "
              f"(marquées par 'tco_reconstruit')")

    return df


def completer_tco(df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruit les taux de couverture absents de 2013 à 2019.

    RTE ne publie les colonnes `tco_` qu'à partir de 2020 (0 % renseigné avant,
    100 % ensuite). Or le taux de couverture est une fonction déterministe de
    colonnes disponibles sur toute la période :

        tco_filiere = 100 x filiere / consommation

    La formule a été vérifiée sur les valeurs publiées : l'écart absolu médian
    est de 0,003 point et le maximum de 0,01, soit de l'arrondi. La
    reconstruction n'est donc pas une approximation.

    Deux garde-fous :

    - on ne remplit que les valeurs manquantes, jamais par-dessus une valeur
      publiée par RTE ;
    - les lignes complétées sont marquées par la colonne booléenne
      `tco_reconstruit`, pour qu'aucune analyse ne confonde une valeur publiée
      et une valeur recalculée.

    Attention : cela n'apporte aucune information nouvelle, seulement une
    colonne utilisable sur toute la période. `tco_nucleaire` reste limité par
    la disponibilité de `nucleaire` (environ 75 %).
    """
    resultat = df.copy()
    # Une consommation nulle rendrait le taux infini : on ne remplit pas ces lignes.
    consommation = resultat["consommation"].where(resultat["consommation"] > 0)

    a_reconstruire = pd.Series(False, index=resultat.index)
    for filiere in FILIERES_TCO:
        colonne = f"tco_{filiere}"
        if colonne not in resultat.columns:
            continue
        manquant = resultat[colonne].isna() & resultat[filiere].notna() & consommation.notna()
        resultat.loc[manquant, colonne] = (
            100 * resultat.loc[manquant, filiere] / consommation[manquant]
        )
        a_reconstruire |= manquant

    resultat["tco_reconstruit"] = a_reconstruire
    return resultat


def capacite_installee(
    df: pd.DataFrame, filiere: str = "solaire", seuil_tch: float = 5.0
) -> pd.DataFrame:
    """Déduit la puissance installée par région et par mois, en inversant le TCH.

    Le taux de charge vaut `100 x production / puissance installée`, donc :

        puissance installée = 100 x production / tch

    La puissance installée n'est pas fournie par le jeu de données : c'est donc
    une information réellement nouvelle, contrairement à la reconstruction du
    TCO. Elle sert notamment à mesurer la croissance du parc (sous-question 2).

    Deux limites à garder en tête :

    - le TCH n'existe qu'à partir de **2020**, donc la puissance installée
      n'est déductible que sur 2020-2026. L'extrapoler à rebours sur les sept
      années précédentes serait hasardeux ; une source externe (registre des
      installations d'ODRE) serait plus honnête ;
    - le rapport explose quand le taux de charge est proche de zéro (la nuit).
      On ne retient donc que les pas de temps où il dépasse `seuil_tch`, et on
      résume par la médiane mensuelle, la puissance installée évoluant lentement.
    """
    colonne_tch = f"tch_{filiere}"
    retenu = df[df[colonne_tch] > seuil_tch].copy()
    retenu["capacite"] = 100 * retenu[filiere] / retenu[colonne_tch]
    # On retire le fuseau avant de regrouper par mois : seul le calendrier importe ici.
    sans_fuseau = retenu["date_heure_locale"].dt.tz_localize(None)
    retenu["mois_date"] = sans_fuseau.dt.to_period("M").dt.to_timestamp()

    resume = (
        retenu.groupby(["libelle_region", "mois_date"])["capacite"]
        .agg(capacite_mw="median", pas_de_temps="size")
        .reset_index()
    )
    return resume


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
