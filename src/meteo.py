"""Téléchargement de la météo régionale depuis Open-Meteo (réanalyse ERA5).

Source : https://archive-api.open-meteo.com (API d'archive, gratuite, sans clé).
Les données proviennent de la réanalyse **ERA5** du centre européen (ECMWF) :
un modèle atmosphérique recalé sur des observations, dont des satellites.

Raison d'être : cette source est **extérieure aux données de production RTE**.
C'est ce qui permet de valider l'indice de ciel clair sans circularité, faute de
quoi le test vérifierait une propriété de sa propre définition (journal du
2026-07-28, suites 4 et 5).

Variables récupérées, au pas horaire et en **UTC** :

| Variable | Unité | Usage prévu |
|---|---|---|
| `shortwave_radiation` | W/m² | irradiance globale horizontale, sert à l'indice de clarté |
| `direct_radiation` | W/m² | part directe, contrôle |
| `diffuse_radiation` | W/m² | part diffuse, contrôle (direct + diffus ≈ global) |
| `cloud_cover` | % | nébulosité déclarée, référence secondaire |
| `temperature_2m` | °C | phase 2, pondérée par la population (chauffage) |

Le modèle est **épinglé explicitement** (`models=era5`), et ce n'est pas un
détail. Le modèle servi par défaut par l'API n'est pas documenté, il rend un
nœud de grille différent, et ses valeurs ne coïncident pas : mesuré sur
Nouvelle-Aquitaine en 2024, cumuls journaliers, la corrélation entre les deux
n'est que de **0,977** (Spearman) pour 6,7 % d'écart absolu médian. Une
référence de validation dont on ignore la provenance n'en est pas une.

Réserves à connaître, actées avant tout calcul :

- **ERA5 est une réanalyse, pas une observation.** Sa nébulosité est modélisée.
  Elle est externe aux données RTE, ce qui suffit à lever la circularité, mais
  elle ne constitue pas un étalon parfait.
- **Maille de 0,25°, soit environ 28 km.** Le point demandé est ramené au nœud
  le plus proche. Les coordonnées réellement servies sont conservées dans le
  fichier de sortie (`latitude_grille`, `longitude_grille`, `altitude_m`), pour
  que l'écart au point demandé soit vérifiable et non supposé.
- **La variabilité spatiale est réelle, et elle plafonne ce qu'une validation
  peut atteindre.** Deux nœuds distants d'environ 11 km ne s'accordent qu'à
  0,977 en cumul journalier. Attendre d'un indice régional qu'il corrèle bien
  au-delà à une irradiance ponctuelle n'aurait donc aucun sens.
- **Un point ne représente pas une région.** `CENTRES_REGIONS` associe une seule
  coordonnée à chaque région, alors qu'Auvergne-Rhône-Alpes va de la plaine de
  la Loire aux Alpes. C'est pourquoi `telecharger_meteo()` accepte un
  dictionnaire de points quelconque : le test multi-points prévu au protocole se
  fait sans réécrire quoi que ce soit.
- **Convention horaire.** Les flux d'irradiance sont des moyennes sur l'heure
  **précédant** l'horodatage. Sans incidence au pas journalier, qui est le pas
  du test principal ; à reprendre si un test horaire est mené ensuite.

Usage :
    uv run python src/meteo.py           # télécharge si absent
    uv run python src/meteo.py --force   # force le re-téléchargement
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# Exécuté directement (`python src/meteo.py`), seul `src/` est sur le chemin
# d'import : on y ajoute la racine du projet pour que `src.analyses` résolve,
# comme lorsque le module est importé depuis un notebook.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyses import CENTRES_REGIONS

API_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

# Épinglé volontairement : le défaut de l'API n'est pas documenté et ne rend pas
# les mêmes valeurs (voir l'en-tête du module).
MODELE = "era5"

VARIABLES = [
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "cloud_cover",
    "temperature_2m",
]

# Bornes calées sur le jeu ODRE (2012-12-31 -> 2026-04-30). Une journée de marge
# de chaque côté absorbe les décalages de fuseau lors des appariements.
DEBUT = "2012-12-30"
FIN = "2026-05-01"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FICHIER_SORTIE = PROJECT_ROOT / "data" / "meteo_regions.parquet"
DOSSIER_CACHE = PROJECT_ROOT / "data" / "meteo_cache"


def telecharger_point(
    nom: str,
    latitude: float,
    longitude: float,
    debut: str = DEBUT,
    fin: str = FIN,
    delai: int = 120,
    tentatives: int = 6,
    attente_quota: float = 65.0,
) -> pd.DataFrame:
    """Récupère la série horaire d'un point unique.

    Retourne un tableau à plat, avec les coordonnées **réellement servies** par
    l'API en plus de celles demandées : la grille ERA5 ramène le point au nœud le
    plus proche, et cet écart doit rester mesurable.

    L'API gratuite pondère chaque appel par la durée demandée et le nombre de
    variables. Treize ans au pas horaire dépasse le quota par minute, d'où la
    reprise sur code 429 : on attend et on retente plutôt que d'abandonner.
    """
    parametres = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": debut,
        "end_date": fin,
        "hourly": ",".join(VARIABLES),
        "timezone": "UTC",
        "models": MODELE,
    }

    for essai in range(1, tentatives + 1):
        reponse = requests.get(API_ARCHIVE, params=parametres, timeout=delai)
        if reponse.status_code != 429:
            break
        if essai == tentatives:
            reponse.raise_for_status()
        print(f"      quota atteint, attente de {attente_quota:.0f} s "
              f"(essai {essai}/{tentatives})", flush=True)
        time.sleep(attente_quota)

    reponse.raise_for_status()
    contenu = reponse.json()

    horaire = contenu["hourly"]
    tableau = pd.DataFrame(horaire)
    tableau["horodatage_utc"] = pd.to_datetime(tableau.pop("time"), utc=True)

    tableau.insert(0, "point", nom)
    tableau["latitude_demandee"] = latitude
    tableau["longitude_demandee"] = longitude
    tableau["latitude_grille"] = contenu["latitude"]
    tableau["longitude_grille"] = contenu["longitude"]
    tableau["altitude_m"] = contenu["elevation"]
    return tableau


def _nom_cache(nom: str) -> Path:
    """Chemin du cache d'un point, à partir d'un nom lisible."""
    sur = "".join(c if c.isalnum() else "_" for c in nom)
    return DOSSIER_CACHE / f"{sur}.parquet"


def telecharger_meteo(
    points: dict[str, tuple[float, float]] | None = None,
    debut: str = DEBUT,
    fin: str = FIN,
    pause: float = 20.0,
    cache: bool = True,
    bavard: bool = True,
) -> pd.DataFrame:
    """Récupère la série horaire de plusieurs points, un appel par point.

    `points` est un dictionnaire `nom -> (latitude, longitude)`. Par défaut, les
    douze centres régionaux. En passer un autre permet le test multi-points prévu
    au protocole, sans modifier ce module.

    Chaque point est **mis en cache séparément** dans `data/meteo_cache/`. Un
    échec de quota en cours de route ne fait donc rien reperdre : relancer
    reprend là où ça s'était arrêté. Une pause sépare les appels, l'API étant
    gratuite et sans clé.
    """
    if points is None:
        points = CENTRES_REGIONS

    if cache:
        DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)

    morceaux = []
    for numero, (nom, (latitude, longitude)) in enumerate(points.items(), start=1):
        chemin = _nom_cache(nom)
        if cache and chemin.exists():
            if bavard:
                print(f"  [{numero}/{len(points)}] {nom} : déjà en cache", flush=True)
            morceaux.append(pd.read_parquet(chemin))
            continue

        if bavard:
            print(f"  [{numero}/{len(points)}] {nom} ...", flush=True)
        morceau = telecharger_point(nom, latitude, longitude, debut, fin)
        if cache:
            morceau.to_parquet(chemin, index=False)
        morceaux.append(morceau)

        if numero < len(points):
            time.sleep(pause)

    return pd.concat(morceaux, ignore_index=True)


def charger_meteo(chemin: Path = FICHIER_SORTIE) -> pd.DataFrame:
    """Relit le fichier météo téléchargé.

    Pendant symétrique de `preparation.charger_donnees()` : tout code d'analyse
    passe par ici plutôt que de relire le Parquet à la main.
    """
    if not chemin.exists():
        raise FileNotFoundError(
            f"Fichier météo absent : {chemin}. Lancer d'abord "
            "`uv run python src/meteo.py`."
        )
    return pd.read_parquet(chemin)


def resume_grille(meteo: pd.DataFrame) -> pd.DataFrame:
    """Écart entre le point demandé et le nœud de grille servi, en kilomètres.

    Sert à documenter la précision spatiale réelle plutôt qu'à la supposer.
    """
    import numpy as np

    points = meteo.drop_duplicates("point").set_index("point")
    latitude_moyenne = np.radians(
        (points["latitude_demandee"] + points["latitude_grille"]) / 2
    )
    delta_lat = (points["latitude_grille"] - points["latitude_demandee"]) * 111.0
    delta_lon = (
        (points["longitude_grille"] - points["longitude_demandee"])
        * 111.0
        * np.cos(latitude_moyenne)
    )
    return pd.DataFrame(
        {
            "latitude_grille": points["latitude_grille"],
            "longitude_grille": points["longitude_grille"],
            "altitude_m": points["altitude_m"],
            "ecart_km": np.hypot(delta_lat, delta_lon).round(1),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Téléchargement météo Open-Meteo.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharge même si le fichier de sortie existe déjà.",
    )
    arguments = parser.parse_args()

    if FICHIER_SORTIE.exists() and not arguments.force:
        print(f"✓ Météo déjà présente : {FICHIER_SORTIE.relative_to(PROJECT_ROOT)}")
        print("  (utiliser --force pour re-télécharger)")
        return 0

    FICHIER_SORTIE.parent.mkdir(parents=True, exist_ok=True)

    print(f"Téléchargement Open-Meteo (ERA5), {DEBUT} -> {FIN}, "
          f"{len(CENTRES_REGIONS)} points :")
    meteo = telecharger_meteo()
    meteo.to_parquet(FICHIER_SORTIE, index=False)

    taille_mo = FICHIER_SORTIE.stat().st_size / (1 << 20)
    print()
    print(f"✓ {len(meteo):,} lignes écrites -> "
          f"{FICHIER_SORTIE.relative_to(PROJECT_ROOT)} ({taille_mo:.1f} Mo)")
    print(f"  Période : {meteo['horodatage_utc'].min()} -> {meteo['horodatage_utc'].max()}")
    print(f"  Points  : {meteo['point'].nunique()}")
    print()
    print("Écart entre point demandé et nœud de grille ERA5 :")
    print(resume_grille(meteo).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
