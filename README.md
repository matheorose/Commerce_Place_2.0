# City Insights API

Service FastAPI propre qui orchestre l'agent IA historique et le pipeline d'analyse (carroyage INSEE, carte Folium, métriques K-Means). Le code source est organisé en modules clairs (`services`, `models`, `core`) et un seul fichier permet de lancer l'API (`python main.py`).

## Structure

- `main.py` – point d'entrée unique (wrap `uvicorn`).
- `pyproject.toml` – dépendances (FastAPI, LangChain, pandas, scikit-learn…).
- `data/` – ressources locales (catégories, résultats JSON, cartes Folium).
- `src/city_insights_api/`
  - `core/` – configuration centralisée (chemins, CORS, agent legacy).
  - `models/` – schémas Pydantic partagés (domain + API).
  - `services/` – logique métier (agent loader, carroyage, map builder, pipeline, métriques, agent conversationnel outillé).
  - `api/routes.py` – endpoints `/api/*`.
  - `app.py` – factory FastAPI utilisée par `uvicorn`.
- `template-chatbot-ang/` – frontend Angular prêt à l’emploi (copie de l’ancien front, configurée pour cette API).

## Pré-requis

- Python 3.10+.
- Dépendances installées :
  ```bash
  cd city_insights_api
  python -m venv .venv && source .venv/bin/activate  # optionnel
  pip install -e .
  ```
- Clef OpenAI exportée (`OPENAI_API_KEY`) pour que l'agent LangChain puisse fonctionner.
- Une base MongoDB accessible (par défaut `mongodb://localhost:27017`) pour stocker l'historique des conversations. Vous pouvez ajuster les variables `MONGO_DSN`, `MONGO_DB_NAME` et `MONGO_COLLECTION`.
- Jeu de données INSEE `carroyage-insee-metro-s2.csv` placé dans `city_insights_api/data/` **ou** conservé dans `../ia/data/` (détecté automatiquement).

## Lancement de l'API

```bash
cd city_insights_api
python main.py
# ou
uvicorn city_insights_api.app:app --reload --port 8000
```

- Endpoints disponibles :
  - `GET /api/health` – ping simple.
  - `POST /api/chat` – attend `{ "message": "..." , "session_id"?: "<id>" }`, renvoie la réponse IA, les fichiers générés **et** l'identifiant de session pour continuer un fil.
  - `GET /api/views/{filename}` – sert les cartes Folium stockées dans `data/views/`.
  - `GET /api/chat/sessions` – liste des conversations (titre choisi par l'IA + date de mise à jour).
  - `GET /api/chat/sessions/{id}` – messages d'une conversation pour relecture côté front.

Le JSON retourné conserve la mécanique précédente (`success`, `answer`, `parsed`, `data`).

## Frontend Angular inclus

Le dossier `template-chatbot-ang/` reprend l’interface de chat. Configuration minimale :

```bash
cd city_insights_api/template-chatbot-ang
npm install
npm run start   # lance http://localhost:4200
```

Le front enverra les requêtes à `http://localhost:8000/api` (modifiable via `src/environments/environment.ts`). Pensez à lancer le backend avant les tests pour éviter les erreurs réseau. Les cartes Folium sont accessibles depuis le bouton "Ouvrir la carte" qui pointe sur `GET /api/views/<fichier>`. Un panneau latéral gauche affiche désormais l'historique des conversations (titres générés par l'IA) et permet de reprendre n'importe quel fil.

## Variables d'environnement utiles

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | Clé API OpenAI requise par l'agent LangChain. |
| `API_ALLOWED_ORIGINS` | Liste d'origines CORS séparées par des virgules (défaut `http://localhost:4200`). |
| `LEGACY_AGENT_PATH` | Chemin personnalisé vers `Agent-Python-Donnes_de_commerces_a_partir_dune_ville.py` si le dossier `ia/` n'est pas voisin. |
| `MONGO_DSN` | Connexion MongoDB (défaut `mongodb://localhost:27017`). |
| `MONGO_DB_NAME` | Nom de la base utilisée pour l'historique (`cityinsights`). |
| `MONGO_COLLECTION` | Collection MongoDB pour les conversations (`chat_sessions`). |

## Pipeline réutilisé

1. L'agent legacy génère un fichier JSON commerce (`data/result/<ville>_<categorie>.json`).
2. `InseeCarroyageGenerator` filtre le CSV INSEE selon la bbox du JSON.
3. `MapBuilder` construit la carte Folium (`data/views/map_insee_<ville>_<categorie>.html`) avec heatmap, commerces et zones numérotées (bords en pointillés + étiquettes).
4. `KMeansEvaluator` calcule les métriques (Elbow / Silhouette / Davies-Bouldin) exposées dans la réponse API.
5. `PipelineService` déduit des **zones prioritaires** (population pondérée + nombre de commerces similaires déjà présents) pour guider les recommandations.
6. `CityInsightsAgent` orchestre les tools `fetch_commerces` et `analyze_city` pour que le modèle choisisse lui-même la bonne séquence d'actions avant de répondre.

Chaque étape est encapsulée dans un service testable, facilitant l'extension (nouveaux outils, nouvelles vues ou endpoints dédiés) et permettant à l'IA de réutiliser ces outils librement.
