# ☀️⚡ Intégration du solaire dans le réseau électrique français

Analyse de l'intégration de la production solaire (et éolienne) dans le réseau
électrique français, à partir des données **officielles** de RTE / Enedis.

L'essor du photovoltaïque bouleverse l'équilibre du réseau : la production
solaire est intermittente et concentrée en milieu de journée. Elle creuse la
**demande nette** (la consommation moins la production renouvelable) au milieu du
jour, puis la laisse remonter brutalement le soir. Ce projet analyse cette
dynamique à l'échelle du système électrique français : comment la demande nette
se déforme-t-elle au fil de la journée et des saisons, comment ce creux évolue-t-il
à mesure que le parc solaire grandit, et comment le système s'adapte-t-il à cette
intermittence ?

## 📡 Données

- **Source** : [Open Data Réseaux Énergies (ODRE)](https://opendata.reseaux-energies.fr) — plateforme officielle de RTE, Enedis et GRDF.
- **Jeu de données** : `eco2mix-regional-cons-def` (éCO2mix régional, consolidé définitif).
- **Contenu** : consommation + production par filière (solaire, éolien, nucléaire,
  hydraulique, thermique, bioénergies), pompage-turbinage et échanges physiques
  (imports/exports) — au **pas de 30 minutes**, pour les **12 régions métropolitaines**.
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

## 🎯 Problématique

> **Comment la montée du solaire transforme-t-elle la demande nette d'électricité
> en France, et comment le système s'adapte-t-il à son intermittence ?**

Le projet est mené en deux phases.

**Phase 1 — dynamique temporelle** (échelle du système : 12 régions, pas de 30 min)
1. **Dynamique journalière** — la demande nette (`consommation − solaire − éolien`),
   son creux de mi-journée et sa remontée du soir, et sa déformation selon la saison.
2. **Évolution pluriannuelle** — ce creux se creuse-t-il à mesure que le parc solaire
   grandit (2013 → 2026) ?
3. **Équilibrage** — comment le système fait-il de la place au solaire montant
   (matin/midi), puis compense-t-il sa chute (soir) : pompage-turbinage, échanges
   (imports/exports) et filières flexibles.

**Phase 2 — dimension géographique** (amélioration future)
- Contrastes régionaux du solaire et leur explication (ensoleillement), en croisant
  avec une source météo externe et, à terme, des données à maille plus fine (Enedis).

### Périmètre assumé

Analyse à l'échelle du système (12 régions, pas de 30 minutes). Les écarts locaux,
plus marqués, ne sont pas capturés ici — ils relèvent de la phase 2.

## 📌 Statut

🚧 En cours — pipeline de données en place. Analyse exploratoire à suivre.
