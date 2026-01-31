# Agent IA d’analyse géographique pour l’implantation de commerces

## Problématique du projet

Choisir l’emplacement optimal pour implanter un commerce est une décision complexe, qui nécessite généralement des compétences en analyse territoriale, en lecture de données démographiques et en interprétation de cartes.  
Dans la majorité des cas, ces analyses sont réservées à des experts ou à des cabinets spécialisés, ce qui rend la prise de décision difficile pour des porteurs de projet non techniques.

L’objectif de ce projet est de **rendre l’analyse géographique et démographique accessible à tous**, en s’appuyant sur un **agent IA capable d’agir comme un conseiller**, et non comme un simple outil technique.  
L’utilisateur reste le **décisionnaire**, tandis que l’agent IA met à sa disposition des **outils d’analyse**, les exécute automatiquement et **explique les résultats de manière exploitable**.

---

## Objectif global

Le projet vise à développer un **agent IA capable de guider un utilisateur, sans compétences en data ou en cartographie**, dans le choix de l’emplacement le plus pertinent pour implanter un commerce (pharmacie, boulangerie, etc.).

L’agent :
- comprend une demande formulée en langage naturel,
- collecte automatiquement des données territoriales fiables,
- les transforme et les analyse,
- produit des visualisations claires,
- accompagne l’utilisateur tout au long du processus de recherche et d’analyse afin de faciliter la prise de décision finale.

L’agent n’impose pas une réponse :  il **propose, justifie, compare**, et laisse l’utilisateur décider.

**Attention** : L’agent adapte dynamiquement son comportement aux demandes formulées par l’utilisateur. Il mobilise uniquement les outils et les analyses pertinents au regard de la requête exprimée, afin de fournir des réponses ciblées, efficaces et directement exploitables, sans surcharge d’information inutile.

---

## Fonctionnement général de l’agent IA

### 1. Compréhension de la demande utilisateur

L’agent s’appuie sur les modèles actuels d’OpenAI, ce qui lui permet de comprendre des requêtes formulées en langage naturel, notamment des demandes ciblées telles que :
> « Liste les pharmacies à Belfort »

À partir de ce type de requête, l’agent est capable d’identifier automatiquement :
- la ville cible,
- le type de commerce,
- les outils à mobiliser pour répondre à la demande de l’utilisateur

---

### 2. Collecte automatique des données 

L’agent orchestre de manière autonome des appels vers différentes sources de données afin de collecter les informations nécessaires à l’analyse :
- **Nominatim** pour convertir un nom de ville en coordonnées géographiques exploitables,
- **Overpass API** pour récupérer les commerces existants correspondant au type de commerce recherché.

Il extrait uniquement les informations pertinentes, telles que :
- nom,
- latitude,
- longitude,

puis génère automatiquement des fichiers JSON structurés, sans intervention manuelle de l’utilisateur.

En complément, l’agent est également capable d’effectuer des recherches contextuelles sur Internet, notamment via des services tels que Google Maps et Pappers, afin d’obtenir des informations plus précises sur des commerces spécifiques lorsque cela est nécessaire.

---

### 3. Exploitation des données de population (INSEE)

Pour analyser la répartition des habitants, l’agent utilise un fichier open data de l’INSEE décrivant la population sous forme de **carreaux réguliers de 200 m × 200 m**.

Ce fichier, très volumineux à l’origine, est :
- filtré selon la zone étudiée,
- transformé pour ne conserver que les coordonnées et le nombre d’habitants par carreau.

Afin de rendre ces données exploitables :
- la population totale est ramenée à un certain nombre de points,
- chaque point représente alors le nombre de personnes autour de celui-ci.

Cette approche permet de conserver les **proportions réelles de densité**, tout en restant lisible et performant.

---

### 4. Visualisation et mise en contexte

Les données sont ensuite visualisées à l’aide de **Folium** :
- carte de densité de population,
- superposition des commerces existants,
- légendes adaptées (échelle logarithmique, quantiles).

Ces cartes permettent à l’utilisateur de **voir immédiatement les zones sous-dotées ou saturées**, sans interprétation technique complexe.

---

### 5. Analyse par regroupement de zones (clustering)

Le projet utilise `scikit-learn` pour la partie **apprentissage non supervisé** du pipeline, afin de regrouper automatiquement les cellules INSEE en zones homogènes.

- Un module (ex. `metrics.py`) teste plusieurs valeurs de `K` et calcule des métriques de qualité (inertie / méthode du coude, silhouette, Davies–Bouldin) afin d’aider à choisir un nombre de zones pertinent.
- Un autre module (ex. `pipeline.py`) applique ensuite `KMeans` (`fit_predict`), avec une pondération par population, pour attribuer une étiquette de cluster à chaque cellule INSEE et produire les zones finales.

Il s’agit bien d’un **algorithme d’apprentissage**, mais de type **clustering classique** : pas de réseau de neurones, pas de deep learning.
L’algorithme s’entraine en quelques millisecondes à partir de coordonnées et de populations, puis renvoie l’étiquette de cluster de chaque cellule et regroupe donc les cellules en quartiers cohérents.

Le clustering n’est pas une finalité : il sert à structurer la lecture du territoire (quartiers), comparer population et concurrence, et fournir à l’utilisateur des zones claires pour prendre la décision finale.

---

## Rôle de l’agent IA dans la prise de décision

L’agent agit comme :
- un **intermédiaire intelligent** entre les données et l’utilisateur,
- un **conseiller analytique**, capable de mobiliser plusieurs outils,
- un **facilitateur de décision**.

Il ne remplace pas le jugement humain : il fournit des analyses claires, contextualisées et explicables, afin que **l’utilisateur décide en connaissance de cause**.

---



## Installation rapide

### 1. Récupération du projet
Dans un gitbash : 

```bash
git clone https://github.com/matheorose/Commerce_Place_2.0.git
cd Commerce_Place_2.0
```

### 2. Base de données et configuration (.env)  
Lancer une instance MongoDB locale.

Créer, à la racine du projet, un fichier .env contenant les variables suivantes :

```bash
OPENAI_API_KEY="VOTRE_CLE_API"
MONGO_DSN="mongodb://localhost:27017"
MONGO_DB_NAME="city_insights"
MONGO_COLLECTION="chat_sessions"
```

### 3. Backend – Agent IA (Python)
Dans un premier terminal :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```


### 4. Frontend – Interface utilisateur (Angular)
Dans un second terminal :

```bash
cd template-chatbot-ang
npm install
npm start
```

---

## Exemples de prompts
Voici quelques exemples de requêtes pouvant être adressées à l’agent :

- **"Liste les boulangeries à Thann"** : L’agent retourne la liste des boulangeries présentes à Thann, avec pour chacune le nom, la latitude et la longitude.

- **"C’est quoi Fanny’s Café ? Fais une recherche"** : L’agent réalise une recherche approfondie sur Internet et transmet à l’utilisateur des informations pertinentes sur l’établissement (activité, localisation, éléments contextuels).

- **"Où est-il le plus pertinent d’implanter une pharmacie à Belfort ?"** : L’agent fournit une analyse des différentes zones de Belfort, en tenant compte de la répartition des pharmacies existantes et des données démographiques.

---

## Conclusion
Cet agent d’intelligence artificielle s’appuie sur les modèles actuels d’OpenAI, reconnus pour leurs capacités avancées de compréhension et de raisonnement en langage naturel. Il en exploite pleinement le potentiel tout en allant au-delà d’un simple agent conversationnel, grâce à l’intégration d’outils spécifiques orientés vers l’analyse territoriale et commerciale.

L’agent permet ainsi à l’utilisateur de réaliser des recherches ciblées sur des commerces à partir d’une ville donnée. Il est capable de collecter et de croiser différentes sources de données afin de produire une visualisation cartographique interactive, intégrant à la fois l’implantation des commerces, la répartition démographique et le découpage du territoire en zones cohérentes (clusters).

Au-delà de la visualisation, l’agent propose également une analyse approfondie des zones identifiées. Il met en évidence leurs principales caractéristiques et fournit des indicateurs comparables, permettant à l’utilisateur d’évaluer les avantages et les limites de chaque zone en fonction de ses propres critères.

L’agent se positionne ainsi comme un outil d’aide à la décision, combinant intelligence artificielle, analyse de données et représentation spatiale, tout en laissant à l’utilisateur la maîtrise finale des choix stratégiques liés à l’implantation commerciale.