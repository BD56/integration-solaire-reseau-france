# ☀️⚡ Intégration du solaire dans le réseau électrique français

Analyse de l'intégration de la production solaire (et éolienne) dans le réseau
électrique français, à partir des données **officielles** de RTE / Enedis.

L'essor du photovoltaïque bouleverse l'équilibre du réseau : la production
solaire est intermittente et concentrée en milieu de journée, ce qui creuse la
fameuse **« duck curve »** (courbe en canard) de la demande nette. Ce projet
explore ce phénomène à l'échelle des régions françaises : quand et où le solaire
pèse-t-il le plus, comment la demande nette se déforme-t-elle, et quel rôle
jouent le stockage et les échanges entre régions lorsque le soleil se couche ?

## 📡 Données

- **Source** : [Open Data Réseaux Énergies (ODRE)](https://opendata.reseaux-energies.fr) — plateforme officielle de RTE, Enedis et GRDF.
- **Jeu de données** : `eco2mix-regional-cons-def` (éCO2mix régional, consolidé définitif).
- **Contenu** : consommation + production par filière (solaire, éolien terrestre/offshore,
  nucléaire, hydraulique, thermique, bioénergies, pompage), stockage batterie et
  échanges physiques — au **pas de 30 minutes**, pour les **12 régions métropolitaines**.
- **Période** : depuis fin 2012, mise à jour en continu (~2,8 millions de lignes).
- **Licence** : [Licence Ouverte / Etalab](https://www.etalab.gouv.fr/licence-ouverte-open-licence).

> Les données ne sont **pas versionnées** dans ce dépôt (voir `.gitignore`).
> Elles se régénèrent en une commande via le script de téléchargement.

## 🚀 Reproduction

Prérequis : [uv](https://docs.astral.sh/uv/).

```bash
# 1. Installer l'environnement (Python + dépendances, versions verrouillées)
uv sync

# 2. Télécharger les données depuis l'API ODRE (~60 Mo, écrit dans data/)
uv run python src/download.py
```

## 🗂️ Structure

```
integration-solaire-reseau-france/
├── data/                 # données téléchargées (non versionnées)
├── src/
│   └── download.py       # récupération des données via l'API ODRE
├── notebooks/            # analyses exploratoires (à venir)
├── pyproject.toml        # dépendances (gérées par uv)
├── uv.lock               # versions verrouillées (reproductibilité)
└── README.md
```

## 🎯 Pistes d'analyse

- Reconstruire la **demande nette** (`consommation − solaire − éolien`) et visualiser la *duck curve*.
- Mesurer la **pénétration du solaire** (taux de couverture) et sa saisonnalité.
- Comparer les **contrastes régionaux** (Sud ensoleillé vs Nord).
- Étudier le rôle du **stockage** et des **échanges** aux moments de bascule (coucher du soleil).

## 📌 Statut

🚧 En cours — pipeline de données en place. Analyse exploratoire à suivre.
