# python
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List
from langchain_core.messages import ToolMessage, SystemMessage
import re
import unicodedata
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import os
import time
import random
import requests
import difflib
import re
import unicodedata
from data.categories import CATEGORIES

load_dotenv()



# =========================================================
# 1) CONFIG (EDIT ICI)
# =========================================================
MODEL = "gpt-4o-mini"
TEMP = 0.0

SYSTEM_MESSAGE = (
    "Tu es un assistant de collecte de données géographiques.\n"
    "Tu dois produire un fichier JSON via les tools.\n\n"

    "PROCÉDURE OBLIGATOIRE (À RESPECTER STRICTEMENT) :\n"
    "1) Identifie la ville et le type de lieu demandé par l’utilisateur.\n"
    "2) Si l’utilisateur n’a PAS précisé le périmètre de recherche, "
    "pose EXACTEMENT cette question et ATTENDS la réponse :\n"
    "   \"Souhaitez-vous être précis ou bien analyser les alentours aussi ?\"\n"
    "   - Si la réponse est \"précis\" : utiliser bbox_mode=\"strict\".\n"
    "   - Si la réponse est \"alentours\" : utiliser bbox_mode=\"around\".\n"
    "   - Ne PAS appeler fetch_places_to_json tant que cette réponse n’est pas connue.\n"
    "3) Appelle resolve_category_key(user_category=<type demandé>) pour obtenir une category_key valide.\n"
    "4) Appelle fetch_places_to_json avec les paramètres suivants :\n"
    "   - city=<ville>\n"
    "   - category_key=<category_key>\n"
    "   - bbox_mode selon la réponse (\"strict\" ou \"around\")\n"
    "   - expand_ratio=0.35 uniquement si bbox_mode=\"around\"\n\n"

    "RÈGLES STRICTES :\n"
    "- category_key doit être une clé de CATEGORIES (ex: bakery, pharmacy), "
    "jamais un tag OSM (ex: amenity/shop).\n"
    "- Tu ne dois JAMAIS appeler fetch_places_to_json sans avoir déterminé bbox_mode.\n"
    "- Tu ne dois PAS inventer de paramètres non supportés par les tools.\n\n"

    "SORTIE FINALE OBLIGATOIRE (ET RIEN D’AUTRE) :\n"
    "count=<nombre>\n"
    "file=<chemin_du_json>\n\n"

    "Si un tool échoue, répondre uniquement sous la forme :\n"
    "Erreur: <message>"
)







MAX_HISTORY = 20        # maîtrise la mémoire (coût / stabilité)
MAX_TOOL_STEPS = 30      # évite les boucles infinies tool -> tool -> tool



OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRRORS = (
    OVERPASS_URL,
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_MIRRORS = (
    NOMINATIM_URL,
    "https://nominatim.openstreetmap.fr/search",
)


# =========================================================
# 2) TOOLS (AJOUTE ICI TES OUTILS)
# =========================================================

# python
def _get_selector(cat: dict) -> tuple[str, str] | None:
    """
    Supporte 2 formats :
    - { selector: { type, value } }
    - { type, value }
    Retourne (key, value) ou None si invalide.
    """
    sel = cat.get("selector")
    if isinstance(sel, dict):
        k = sel.get("type")
        v = sel.get("value")
        if k and v:
            return k, v

    # fallback format plat
    k = cat.get("type")
    v = cat.get("value")
    if k and v:
        return k, v

    return None


def _parse_overpass_xml(xml_text: str) -> List[Dict[str, Any]]:
    """
    Parse XML Overpass et renvoie une liste MINIMALE et exploitable :
    - id, name, lat, lon
    - ignore les éléments sans name/lat/lon
    """
    root = ET.fromstring(xml_text)
    results: List[Dict[str, Any]] = []

    for node in root.findall("node"):
        node_id = node.attrib.get("id")
        lat = node.attrib.get("lat")
        lon = node.attrib.get("lon")

        # récupérer le tag name
        name = None
        for tag in node.findall("tag"):
            if tag.attrib.get("k") == "name":
                name = tag.attrib.get("v")
                break

        # On ignore si pas exploitable
        if not node_id or not name or not lat or not lon:
            continue

        results.append({
            "id": node_id,
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
        })

    return results




# python
@tool
def overpass_places_bbox(
    south: float,
    west: float,
    north: float,
    east: float,
    key: str,
    value: str,
    timeout_seconds: int = 25,
) -> Dict[str, Any]:
    """
    Récupère des POI dans une bbox selon un tag OSM key=value.
    Ajout: retry auto sur 504/503/502/429 + timeouts.
    """
    query = f"""
    [out:xml][timeout:{timeout_seconds}];
    (
      node[{key}={value}]({south},{west},{north},{east});
    );
    out;
    """.strip()

    response = None
    errors: List[str] = []
    for base_url in OVERPASS_MIRRORS:
        try:
            response = _request_with_retry(
                "POST",
                base_url,
                data={"data": query},
                headers={"Accept": "application/osm3s+xml"},
                timeout=timeout_seconds + 5,
                max_retries=4,
                base_delay=1.2,
            )
            break
        except Exception as exc:
            errors.append(f"{base_url}: {exc}")
            response = None

    if response is None:
        error_text = " ; ".join(errors) if errors else "Overpass indisponible"
        return {
            "ok": False,
            "error": f"HTTP error: {error_text}",
        }

    try:
        items = _parse_overpass_xml(response.text)
    except ET.ParseError as e:
        return {"ok": False, "error": f"XML parse error: {e}", "raw": response.text[:500]}

    return {"ok": True, "count": len(items), "items": items}



@tool
def city_to_bbox(city: str, country: str = "France", timeout_seconds: int = 10) -> Dict[str, Any]:
    """
    Convertit un nom de ville en bounding box (bbox) via Nominatim (OpenStreetMap).

    Retour (bbox utilisable par Overpass) :
      {
        "ok": True,
        "city": "...",
        "display_name": "...",
        "south": float,
        "west": float,
        "north": float,
        "east": float
      }

    Si erreur :
      {"ok": False, "error": "..."}
    """

    # 1) Construire la requête de géocodage
    # "q" = texte libre : ville + pays (évite les collisions)
    params = {
        "q": f"{city}, {country}",
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }

    # 2) Nominatim exige un User-Agent explicite (et idéalement un contact)
    headers = {
        "User-Agent": "MyAI-Agent/1.0 (contact: kylian.strub@icloud.com)"
    }

    data = None
    response = None
    errors: List[str] = []
    for base_url in NOMINATIM_MIRRORS:
        try:
            response = _request_with_retry(
                "GET",
                base_url,
                params=params,
                headers=headers,
                timeout=timeout_seconds,
                max_retries=3,
                base_delay=0.8,
            )
        except Exception as exc:
            errors.append(f"{base_url}: {exc}")
            response = None
            continue

        try:
            data = response.json()
        except ValueError as e:
            return {"ok": False, "error": f"JSON parse error: {e}"}
        break

    if response is None:
        error_text = " ; ".join(errors) if errors else "Nominatim indisponible"
        return {"ok": False, "error": f"HTTP error: {error_text}"}

    # 3) Vérifier qu'on a un résultat
    if not data:
        return {"ok": False, "error": f"Aucun résultat Nominatim pour '{city}, {country}'"}

    best = data[0]

    # 4) La bbox Nominatim est une liste de strings : [south, north, west, east]
    # (Oui l'ordre est chelou, on le remap proprement)
    try:
        bb = best["boundingbox"]
        south = float(bb[0])
        north = float(bb[1])
        west = float(bb[2])
        east = float(bb[3])
    except Exception as e:
        return {"ok": False, "error": f"boundingbox manquante ou invalide: {e}"}

    return {
        "ok": True,
        "city": city,
        "display_name": best.get("display_name"),
        "south": south,
        "west": west,
        "north": north,
        "east": east,
    }

# python
@tool
def write_json(filepath: str, data: dict) -> dict:
    """
    Écrit un dictionnaire Python dans un fichier JSON,
    toujours dans le dossier ./data.

    Retourne :
    - ok
    - filepath (chemin réel)
    - count (si data["items"] existe)
    """
    try:
        # 1) Dossier cible
        base_dir = "data/result"
        os.makedirs(base_dir, exist_ok=True)

        # 2) Nettoyage du nom de fichier (sécurité)
        filename = os.path.basename(filepath)
        full_path = os.path.join(base_dir, filename)

        # 3) Écriture JSON
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        count = len(data.get("items", [])) if isinstance(data, dict) else None

        return {
            "ok": True,
            "filepath": full_path,
            "count": count,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}"
        }


# python
def _expand_bbox(bbox: Dict[str, float], ratio: float = 0.35) -> Dict[str, float]:
    """
    Agrandit une bbox en % autour de son centre.
    ratio=0.35 => +35% en hauteur et largeur (de chaque côté).
    """
    ratio = max(0.0, min(float(ratio), 1.0))  # clamp 0..1 (sécurité)

    south, west, north, east = bbox["south"], bbox["west"], bbox["north"], bbox["east"]

    height = north - south
    width = east - west

    # si bbox trop petite (cas bizarre) -> on évite division/0
    if height <= 0 or width <= 0:
        return bbox

    pad_h = height * ratio
    pad_w = width * ratio

    new_south = max(-90.0, south - pad_h)
    new_north = min(90.0, north + pad_h)
    new_west = max(-180.0, west - pad_w)
    new_east = min(180.0, east + pad_w)

    return {"south": new_south, "west": new_west, "north": new_north, "east": new_east}



def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


@tool
def fetch_places_to_json(
    city: str,
    category_key: str,
    filepath: str = "places.json",
    bbox_mode: str = "strict",      # "strict" | "around"
    expand_ratio: float = 0.35,     # utilisé si around
) -> dict:
    """
    Génère un fichier JSON de lieux (POI) pour une ville et une catégorie.

    bbox_mode:
      - "strict": bbox Nominatim telle quelle (comportement actuel)
      - "around": bbox élargie de expand_ratio (ville + alentours)
    
    ✅ RÈGLE ABSOLUE :
    - Le fichier de sortie est FORCÉ : <ville>_<category_key>.json (slugifié)
    - Le paramètre `filepath` est IGNORÉ (le LLM ne contrôle pas le nom)
    """

    # ---------- 1) catégorie ----------
    cat = _find_category(category_key)
    if not cat:
        return {"ok": False, "error": f"Catégorie inconnue: {category_key}"}

    sel = _get_selector(cat)
    if not sel:
        return {"ok": False, "error": f"Catégorie mal définie pour: {category_key}"}

    key, value = sel

    # ---------- 2) bbox Nominatim ----------
    bbox_res = city_to_bbox.invoke({"city": city})
    if not bbox_res.get("ok"):
        return {"ok": False, "error": f"Nominatim: {bbox_res.get('error')}"}

    bbox = {k: float(bbox_res[k]) for k in ("south", "west", "north", "east")}

    # ---------- 3) élargissement si around ----------
    mode = (bbox_mode or "strict").strip().lower()
    if mode == "around":
        bbox = _expand_bbox(bbox, ratio=expand_ratio)

    # ---------- 4) Overpass ----------
    res = overpass_places_bbox.invoke({
        "south": bbox["south"],
        "west": bbox["west"],
        "north": bbox["north"],
        "east": bbox["east"],
        "key": key,
        "value": value,
    })
    if not res.get("ok"):
        return {"ok": False, "error": f"Overpass: {res.get('error')}"}

    payload = {
        "city": city,
        "category": {"key": category_key, "label": cat.get("label"), "osm": f"{key}={value}"},
        "bbox": bbox,
        "bbox_mode": mode,
        "expand_ratio": float(expand_ratio) if mode == "around" else 0.0,
        "count": res.get("count"),
        "items": res.get("items", []),
    }
    
    forced_filename = f"{_slugify(city)}_{_slugify(category_key)}.json"

    w = write_json.invoke({"filepath": forced_filename, "data": payload})

    if not w.get("ok"):
        return {"ok": False, "error": f"write_json: {w.get('error')}"}

    return {
        "ok": True,
        "city": city,
        "category_key": category_key,
        "count": payload["count"],
        "filepath": w["filepath"],
    }


# python
def _normalize_text(s: str) -> str:
    """Normalise texte FR pour matching robuste (accents, ponctuation, espaces)."""
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\s_-]+", " ", s)   # garde lettres/chiffres/espaces/_/-
    s = s.replace("-", " ").replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _singularize_fr(word: str) -> str:
    """
    Heuristique simple pluriel -> singulier.
    - boulangeries -> boulangerie
    - boucheries -> boucherie
    - pharmacies -> pharmacie
    - supermarches -> supermarche (accent déjà retiré)
    """
    w = word.strip()
    if len(w) <= 3:
        return w

    # ies -> ie
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "ie"

    # aux -> al (chevaux->cheval) (rare ici mais safe)
    if w.endswith("aux") and len(w) > 4:
        return w[:-3] + "al"

    # s final (évite "bus" => "bu" : cas rare, mais on protège 3 lettres)
    if w.endswith("s") and len(w) > 4:
        return w[:-1]

    return w


def _best_fuzzy_match(query: str, candidates: List[tuple[str, str]], cutoff: float = 0.82) -> str | None:
    """
    candidates: list of (candidate_text, category_key)
    Retourne category_key si match fuzzy OK.
    """
    q = _normalize_text(query)
    # test aussi une variante "singularisée" mot par mot
    q_sing = " ".join(_singularize_fr(w) for w in q.split())

    # on tente sur q puis q_sing
    for q_try in (q, q_sing):
        texts = [c[0] for c in candidates]
        # meilleur match
        matches = difflib.get_close_matches(q_try, texts, n=1, cutoff=cutoff)
        if matches:
            best = matches[0]
            # retrouver la key
            for text, key in candidates:
                if text == best:
                    return key
    return None


# python
@tool
def resolve_category_key(user_category: str) -> dict:
    """
    Mappe un texte utilisateur vers une category_key valide (CATEGORIES),
    en utilisant key/label/synonyms.
    Ajout: interprétation légère (normalisation + pluriel + fuzzy).
    """
    raw = (user_category or "").strip()
    if not raw:
        return {"ok": False, "error": "Catégorie vide"}

    q = raw.lower()

    # ---------- 1) Match strict sur key ----------
    for c in CATEGORIES:
        k = (c.get("key") or "").strip().lower()
        if k and k == q:
            return {"ok": True, "category_key": c["key"], "match": "strict:key"}

    # ---------- 2) Match strict sur label ----------
    for c in CATEGORIES:
        lab = (c.get("label") or "").strip().lower()
        if lab and lab == q:
            return {"ok": True, "category_key": c["key"], "match": "strict:label"}

    # ---------- 3) Match strict sur synonyms ----------
    for c in CATEGORIES:
        syns = c.get("synonyms") or []
        syns_norm = [(s or "").strip().lower() for s in syns]
        if q in syns_norm:
            return {"ok": True, "category_key": c["key"], "match": "strict:synonym"}

    # ---------- 4) Interprétation légère (normalisation + pluriel) ----------
    q_norm = _normalize_text(raw)
    q_sing = " ".join(_singularize_fr(w) for w in q_norm.split())

    # Essai direct normalisé sur label/synonyms
    for c in CATEGORIES:
        if _normalize_text(c.get("key") or "") == q_norm or _normalize_text(c.get("key") or "") == q_sing:
            return {"ok": True, "category_key": c["key"], "match": "norm:key"}

        if _normalize_text(c.get("label") or "") == q_norm or _normalize_text(c.get("label") or "") == q_sing:
            return {"ok": True, "category_key": c["key"], "match": "norm:label"}

        syns = c.get("synonyms") or []
        syns_norm = [_normalize_text(s) for s in syns if s]
        if q_norm in syns_norm or q_sing in syns_norm:
            return {"ok": True, "category_key": c["key"], "match": "norm:synonym"}

    # ---------- 5) Fuzzy match (dernier recours) ----------
    # On construit des candidats normalisés (label + key + synonyms)
    candidates: List[tuple[str, str]] = []
    for c in CATEGORIES:
        key = c.get("key")
        if not key:
            continue
        candidates.append((_normalize_text(key), key))
        if c.get("label"):
            candidates.append((_normalize_text(c["label"]), key))
        for s in (c.get("synonyms") or []):
            if s:
                candidates.append((_normalize_text(s), key))

    fuzzy_key = _best_fuzzy_match(raw, candidates, cutoff=0.82)
    if fuzzy_key:
        return {"ok": True, "category_key": fuzzy_key, "match": "fuzzy"}

    # debug utile
    keys = [c.get("key") for c in CATEGORIES if c.get("key")]
    return {"ok": False, "error": f"Catégorie inconnue: {user_category}", "available_keys": keys}




# python
def _find_category(category_key: str) -> dict | None:
    if not category_key:
        return None
    key_norm = category_key.strip().lower()

    for c in CATEGORIES:
        if (c.get("key") or "").strip().lower() == key_norm:
            return c
    return None


# python
@tool
def list_categories() -> dict:
    """
    Retourne les catégories disponibles (key + label).
    """
    out = []
    for c in CATEGORIES:
        k = c.get("key")
        if not k:
            continue
        out.append({"key": k, "label": c.get("label")})
    return {"ok": True, "categories": out}



def _request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int = 4,
    base_delay: float = 1.0,
    timeout: int = 30,
    retry_statuses: set[int] = {429, 500, 502, 503, 504},
    **kwargs,
) -> requests.Response:
    """
    Effectue une requête HTTP avec retry + exponential backoff + jitter.
    - Retry sur timeouts + erreurs réseau + certains status HTTP (dont 504).
    - Lève l'exception finale si tous les essais échouent.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.request(method, url, timeout=timeout, **kwargs)

            # Si status à retry (ex: 504), on déclenche une exception contrôlée
            if resp.status_code in retry_statuses:
                raise requests.HTTPError(
                    f"{resp.status_code} {resp.reason}",
                    response=resp,
                )

            resp.raise_for_status()
            return resp

        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            last_exc = e

            # Dernier essai => on remonte l'erreur
            if attempt == max_retries:
                raise

            # backoff exponentiel + jitter
            delay = base_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, 0.25 * delay)
            time.sleep(delay)

    # Sécurité (ne devrait jamais arriver)
    raise last_exc if last_exc else RuntimeError("Retry failed with unknown error")



















TOOLS = [city_to_bbox, overpass_places_bbox, write_json, fetch_places_to_json, list_categories, resolve_category_key]

# Registry: nom -> objet tool (permet d'exécuter sans if/elif)
TOOL_REGISTRY: Dict[str, Any] = {t.name: t for t in TOOLS}


# =========================================================
# 3) LLM
# =========================================================
llm = ChatOpenAI(model=MODEL, temperature=TEMP).bind_tools(TOOLS)


# =========================================================
# 4) RUNNER SOLIDE (scalable)
# =========================================================






# -------------------------------------------------------------------
# run_agent (après tes modifs)
# -------------------------------------------------------------------
# python
def run_agent(user_input: str, history: List[BaseMessage]) -> AIMessage:
    """
    Agent tool-calling robuste (toujours piloté par le LLM) :
    - Le LLM décide des tools à appeler
    - Les résultats de tools sont renvoyés "tels quels" (pas de double wrapper)
    - Si un tool renvoie ok=False => on stop et on renvoie Erreur: ...
    - Limite MAX_TOOL_STEPS conservée pour éviter les boucles infinies
    """

    messages: List[BaseMessage] = (
        [SystemMessage(content=SYSTEM_MESSAGE)]
        + history
        + [HumanMessage(content=user_input)]
    )

    for _ in range(MAX_TOOL_STEPS):
        response = llm.invoke(messages)

        # Réponse finale
        if not response.tool_calls:
            return response

        # On conserve le message assistant qui contient les tool_calls
        messages.append(response)

        # Exécuter les tool_calls
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            tool_obj = TOOL_REGISTRY.get(tool_name)
            if tool_obj is None:
                return AIMessage(content=f"Erreur: Tool inconnu: {tool_name}")

            try:
                result = tool_obj.invoke(tool_args)
            except Exception as e:
                return AIMessage(content=f"Erreur: {type(e).__name__}: {e}")

            # Si le tool a une convention {"ok": False, "error": "..."} => stop immédiat
            if isinstance(result, dict) and result.get("ok") is False:
                return AIMessage(content=f"Erreur: {result.get('error')}")

            # IMPORTANT : renvoyer le résultat BRUT au modèle (pas de wrapper)
            messages.append(
                ToolMessage(
                    tool_call_id=tool_call_id,
                    content=json.dumps(result, ensure_ascii=False),
                )
            )

    return AIMessage(content="Erreur: limite d'étapes d'outils atteinte (MAX_TOOL_STEPS).")


def _load_result_payload(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_agent_result(filepath: Path) -> Dict[str, Any]:
    data = _load_result_payload(filepath)
    category = data.get("category", {})

    return {
        "city": data.get("city"),
        "category_key": category.get("key"),
        "category_label": category.get("label"),
        "bbox": data.get("bbox", {}),
        "bbox_mode": data.get("bbox_mode"),
        "expand_ratio": data.get("expand_ratio"),
        "count": data.get("count", 0),
        "places": data.get("items", []),
        "result_file": str(filepath),
        "result_filename": filepath.name,
        "payload": data,
    }


def _normalize_mode(value: str | None) -> str:
    v = (value or "strict").strip().lower()
    return "around" if v == "around" else "strict"


def run_agent_from_params(
    city: str,
    user_category: str,
    *,
    bbox_mode: str = "strict",
    expand_ratio: float | None = None,
    radius_km: float | None = None,
) -> Dict[str, Any]:
    """
    Version appelable sans interaction de l'agent.
    - Mappe la catégorie utilisateur via resolve_category_key
    - Génère le JSON via fetch_places_to_json
    - Retourne les données utiles + chemin du fichier généré
    """

    if not city or not user_category:
        raise ValueError("city et user_category sont obligatoires")

    mode = _normalize_mode(bbox_mode)

    # ratio : priorité à la valeur explicite > radius > défaut
    ratio = expand_ratio
    if ratio is None and radius_km is not None:
        ratio = min(0.9, max(0.05, float(radius_km) / 10.0))
    if ratio is None:
        ratio = 0.35 if mode == "around" else 0.0

    cat_res = resolve_category_key.invoke({"user_category": user_category})
    if not cat_res.get("ok"):
        raise RuntimeError(cat_res.get("error") or "Impossible de déterminer la catégorie")

    category_key = cat_res["category_key"]

    fetch_payload = fetch_places_to_json.invoke({
        "city": city,
        "category_key": category_key,
        "bbox_mode": mode,
        "expand_ratio": float(ratio),
    })

    if not fetch_payload.get("ok"):
        raise RuntimeError(fetch_payload.get("error") or "fetch_places_to_json a échoué")

    filepath = Path(fetch_payload["filepath"])
    result = _build_agent_result(filepath)

    # fallback si le JSON ne contient pas la clé attendue
    if not result.get("city"):
        result["city"] = city
    if not result.get("category_key"):
        result["category_key"] = category_key
    if result.get("bbox_mode") is None:
        result["bbox_mode"] = mode
    if result.get("expand_ratio") is None:
        result["expand_ratio"] = ratio

    return result


def _parse_final_message(content: str) -> tuple[int | None, str] | None:
    count: int | None = None
    filepath: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("count="):
            value = line.split("=", 1)[1].strip()
            try:
                count = int(value)
            except ValueError:
                count = None
        elif line.lower().startswith("file="):
            filepath = line.split("=", 1)[1].strip()

    if filepath:
        return count, filepath
    return None


def run_agent_from_message(
    message: str,
    *,
    default_bbox_mode: str = "strict",
) -> Dict[str, Any]:
    """Lance l'agent complet à partir d'un message en langage naturel."""

    message = (message or "").strip()
    if not message:
        raise ValueError("message vide")

    mode = _normalize_mode(default_bbox_mode)
    default_answer = "précis" if mode == "strict" else "alentours"

    history: List[BaseMessage] = []
    current_input = message

    for _ in range(5):
        response = run_agent(current_input, history)
        history += [HumanMessage(content=current_input), response]

        content = (response.content or "").strip()
        if not content:
            continue

        parsed = _parse_final_message(content)
        if parsed is not None:
            _, filepath_str = parsed
            filepath = Path(filepath_str)
            if not filepath.exists():
                raise FileNotFoundError(f"fichier introuvable: {filepath}")
            return _build_agent_result(filepath)

        normalized = unicodedata.normalize("NFKD", content).lower()
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        normalized = normalized.strip()
        if "souhaitez vous etre precis" in normalized:
            current_input = default_answer
            continue

        raise RuntimeError(f"Agent n'a pas fourni de résultat exploitable: {content}")

    raise RuntimeError("Agent n'a pas renvoyé de résultat après plusieurs tentatives")

# =========================================================
# 5) CLI
# =========================================================
def _interactive_cli() -> None:
    print("Agent scalable tools | 'exit' pour quitter\n")
    print("[DEBUG] cwd =", os.getcwd())

    history: List[BaseMessage] = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Bye.")
            break
        if user_input == "":
            continue

        response = run_agent(user_input, history)
        print("Agent:", response.content, "\n")

        history += [HumanMessage(content=user_input), response]
        history = history[-MAX_HISTORY:]


def main_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Agent IA pour récupérer des commerces par ville.\n"
        "Utilisation interactive par défaut, ou bien --city/--category pour un appel direct."
    )
    parser.add_argument("--city", help="Ville ciblée")
    parser.add_argument("--category", help="Commerce ou catégorie demandée")
    parser.add_argument(
        "--bbox-mode",
        choices=["strict", "around"],
        default="strict",
        help="Utiliser la bbox stricte (défaut) ou élargie",
    )
    parser.add_argument(
        "--expand-ratio",
        type=float,
        default=None,
        help="Ratio d'expansion (si around)",
    )
    parser.add_argument(
        "--radius-km",
        type=float,
        default=None,
        help="Distance indicative autour de la ville (km)",
    )
    args = parser.parse_args()

    if args.city and args.category:
        try:
            result = run_agent_from_params(
                args.city,
                args.category,
                bbox_mode=args.bbox_mode,
                expand_ratio=args.expand_ratio,
                radius_km=args.radius_km,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Erreur: {exc}")
            raise SystemExit(1) from exc

        print(f"count={result['count']}")
        print(f"file={result['result_filename']}")
        return

    _interactive_cli()


if __name__ == "__main__":
    main_cli()
