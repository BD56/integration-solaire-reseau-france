"""Téléchargement des données éCO2mix régionales depuis ODRE.

Source officielle : RTE / Enedis via Open Data Réseaux Énergies
(https://opendata.reseaux-energies.fr — miroir API sur odre.opendatasoft.com).

Dataset : `eco2mix-regional-cons-def` (consolidées définitives)
  - Consommation + production par filière (solaire, éolien, nucléaire, hydraulique,
    thermique, bioénergies, pompage), stockage batterie et échanges physiques.
  - Pas de temps : 30 minutes. 12 régions métropolitaines. Depuis fin 2012.

Usage :
    uv run python src/download.py           # télécharge si absent
    uv run python src/download.py --force    # force le re-téléchargement
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

API_BASE = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets"
DATASET = "eco2mix-regional-cons-def"
EXPORT_URL = f"{API_BASE}/{DATASET}/exports/parquet"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "eco2mix_regional.parquet"


def download_dataset(destination: Path, timeout: int = 600) -> None:
    """Télécharge l'intégralité du jeu de données au format Parquet.

    On exporte tout le jeu en une seule requête (endpoint `exports/parquet`
    d'Opendatasoft), sans filtre : plus simple et plus robuste qu'un
    découpage par région. Le flux est écrit directement sur le disque.
    """
    with requests.get(EXPORT_URL, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1 << 20):  # 1 Mo
                file.write(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharge même si le fichier de sortie existe déjà.",
    )
    args = parser.parse_args()

    if OUTPUT_FILE.exists() and not args.force:
        print(f"✓ Données déjà présentes : {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")
        print("  (utilisez --force pour re-télécharger)")
        return 0

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("Téléchargement du jeu complet depuis ODRE (éCO2mix régional) ...")
    download_dataset(OUTPUT_FILE)

    df = pd.read_parquet(OUTPUT_FILE)
    size_mo = OUTPUT_FILE.stat().st_size / (1 << 20)
    print()
    print(f"✓ {len(df):,} lignes écrites -> {OUTPUT_FILE.relative_to(PROJECT_ROOT)} ({size_mo:.0f} Mo)")
    print(f"  Période : {df['date_heure'].min()} -> {df['date_heure'].max()}")
    print(f"  Régions : {df['libelle_region'].nunique()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
