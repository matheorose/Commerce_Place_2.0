"""LLM-driven coordinator that decides which backend tools to run."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Sequence, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..models.domain import AgentPayload, PipelineArtifacts
from .agent_adapter import AgentAdapter
from .pipeline import PipelineService


logger = logging.getLogger(__name__)


CITY_REGEX = re.compile(r"(?:\b(?:a|à|sur|dans|pour|en)\s+)([a-zàâçéèêëîïôûùüÿñ' -]{3,})", re.IGNORECASE)
CATEGORY_STOP_TOKENS = (" à ", " a ", " dans ", " sur ", " pour ", " vers ", "\n", ".", ",", ";", "!", "?")
CATEGORY_KEYWORDS = (
    "commerce",
    "commerces",
    "restaurant",
    "restaurants",
    "pharmacie",
    "pharmacies",
    "boulangerie",
    "boulangeries",
    "boucherie",
    "boucheries",
    "supermarché",
    "supermarches",
    "supermarchés",
    "supérette",
    "superette",
    "supérettes",
    "bars",
    "bar",
    "café",
    "cafés",
    "coiffeur",
    "coiffeurs",
    "coiffure",
    "pressing",
    "pressings",
    "épicerie",
    "epicerie",
    "épiceries",
    "epiceries",
    "bazar",
    "boutique",
    "boutiques",
    "magasin",
    "magasins",
    "garage",
    "garages",
    "hotel",
    "hôtel",
    "hotels",
    "hôtels",
)


class ToolAction(BaseModel):
    """Represents a single step selected by the planner LLM."""

    tool: Literal["fetch_commerces", "analyze_city", "respond_direct"]
    reason: str


class ToolPlan(BaseModel):
    """Structured answer coming from the planner LLM."""

    actions: List[ToolAction] = Field(
        default_factory=list,
        description="Suite d'actions à exécuter dans l'ordre.",
    )


@dataclass
class AgentOutcome:
    answer: str
    fetch: Optional[AgentPayload]
    analysis: Optional[PipelineArtifacts]
    map_file: Optional[Path]
    intent: ConversationIntent


class ConversationIntent(str, Enum):
    """High-level intent extracted from the latest user request."""

    GENERAL = "general"
    LISTING = "listing"
    ANALYSIS = "analysis"


PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Tu es un orchestrateur qui décide quand utiliser trois actions :
- fetch_commerces : interroger l'agent historique avec la dernière requête utilisateur (ville + type) afin d'obtenir un JSON de commerces.
- analyze_city : utiliser le fichier JSON le plus récent pour lancer l'analyse INSEE + KMeans et produire des zones recommandées et une carte.
- respond_direct : répondre toi-même quand la demande est purement conversationnelle ou ne nécessite pas de données réelles.

Procédure :
1. Analyse UNIQUEMENT le dernier message pour déterminer l'intention ; l'historique ne sert que si cohérent avec la demande actuelle.
2. Liste au maximum deux actions ordonnées. Si une action est inutile, ne l'inclus pas.
3. N'ajoute analyze_city que si l'utilisateur demande explicitement une recommandation d'implantation, une analyse, une carte ou une comparaison habitants/commerces.
4. Utilise respond_direct pour les questions générales, les précisions ou lorsqu'aucun outil n'est nécessaire.
5. Indique en une phrase la raison de chaque action en reprenant les éléments concrets de la demande.

Intention détectée : {intent}
Historique (du plus récent au plus ancien) :
{history}
""".strip(),
        ),
        ("human", "{message}"),
    ]
)


RESPONSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Tu es CityInsights, expert en stratégie commerciale.
Priorité absolue : répondre au DERNIER message utilisateur. Si l'historique contredit la requête actuelle, suis la requête actuelle et ignore l'ancienne consigne.

Tu disposes éventuellement de données structurées :
- Informations sur les commerces (ville, catégorie, nombre total, exemples).
- Analyse habitants + zones (population estimée, concurrence, carte générée).

Historique (du plus récent au plus ancien) :
{history}

Règles de réponse :
1. Commence par reformuler brièvement la demande ou rappeler les paramètres (ville, catégorie) pour montrer que tu as compris la consigne actuelle.
2. Lorsque seule la liste des commerces est demandée, concentre-toi sur les volumes, exemples et éventuelles limites ; n'ajoute pas de recommandation d'implantation.
3. Lorsque l'analyse est disponible ou demandée, décris les zones en parlant de « Zone 1 », « Zone 2 », etc. Mentionne population, niveau de concurrence et ce que cela implique pour la stratégie.
4. Invite à consulter la carte lorsqu'elle est disponible et pertinente (ex : « Consulte la carte jointe... »).
5. Si aucune donnée structurée n'est fournie, apporte une réponse générale en te basant sur ton expertise et propose une question de clarification si nécessaire.
""".strip(),
        ),
        ("human", "{message}"),
        ("human", "Instructions additionnelles : {instructions}"),
        (
            "human",
            "Contexte structuré :\n{context}\nCompose ta réponse :",
        ),
    ]
)


TITLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Tu reçois un échange utilisateur/assistant et tu dois proposer un titre très court (5 mots max). "
            "Le titre doit être descriptif et écrit en français.",
        ),
        (
            "human",
            "Message utilisateur : {user}\n"
            "Réponse de l'assistant : {agent}\n"
            "Titre suggéré :",
        ),
    ]
)


class CityInsightsAgent:
    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ) -> None:
        self.adapter = AgentAdapter()
        self.pipeline = PipelineService()
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.planner = PLANNER_PROMPT | self.llm.with_structured_output(ToolPlan)
        self.responder = RESPONSE_PROMPT | self.llm
        self.titler = TITLE_PROMPT | self.llm

    def run(
        self,
        message: str,
        *,
        session_id: str,
        prior_turns: Sequence[Tuple[str, str]],
        prior_user_messages: Sequence[str],
    ) -> AgentOutcome:
        logger.debug("Processing session %s with new message", session_id)
        try:
            outcome = self._execute_turn(
                message,
                prior_turns=prior_turns,
                prior_user_messages=prior_user_messages,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent error while processing message")
            answer = self.build_error_answer(message, exc)
            return AgentOutcome(
                answer=answer,
                fetch=None,
                analysis=None,
                map_file=None,
                intent=ConversationIntent.GENERAL,
            )
        return outcome

    def _execute_turn(
        self,
        message: str,
        *,
        prior_turns: Sequence[Tuple[str, str]],
        prior_user_messages: Sequence[str],
    ) -> AgentOutcome:
        fetch_result: AgentPayload | None = None
        analysis_result: PipelineArtifacts | None = None
        map_path: Path | None = None
        fallback_notice: Optional[str] = None

        history_text = self._format_history(prior_turns)
        intent = self._detect_intent(message)
        city_hint, category_hint, qualifier_hint = self._infer_parameters(
            prior_user_messages,
            latest_message=message,
        )
        adapter_message = self._build_adapter_message(
            message,
            prior_user_messages=prior_user_messages,
            city_hint=city_hint,
            category_hint=category_hint,
            qualifier=qualifier_hint,
            include_qualifier=True,
        )
        fallback_adapter_message = (
            self._build_adapter_message(
                message,
                prior_user_messages=prior_user_messages,
                city_hint=city_hint,
                category_hint=category_hint,
                qualifier=None,
                include_qualifier=False,
            )
            if qualifier_hint
            else None
        )
        plan = self.planner.invoke(
            {
                "message": message,
                "history": history_text,
                "intent": self._describe_intent(intent),
            }
        )
        actions = plan.actions or [ToolAction(tool="fetch_commerces", reason="Par défaut")]  # type: ignore[arg-type]
        analysis_required = intent == ConversationIntent.ANALYSIS
        if analysis_required and not any(a.tool == "analyze_city" for a in actions):
            if not any(a.tool == "fetch_commerces" for a in actions):
                actions.insert(
                    0,
                    ToolAction(tool="fetch_commerces", reason="Analyse requise pour recommander un emplacement."),
                )
            actions.append(ToolAction(tool="analyze_city", reason="Analyse requise pour recommander un emplacement."))
        if intent == ConversationIntent.LISTING and not any(a.tool == "fetch_commerces" for a in actions):
            actions.insert(
                0,
                ToolAction(tool="fetch_commerces", reason="L'utilisateur demande un recensement précis des commerces."),
            )

        needs_fetch = any(a.tool in {"fetch_commerces", "analyze_city"} for a in actions)
        wants_analysis = analysis_required or any(a.tool == "analyze_city" for a in actions)

        for action in actions:
            if action.tool == "fetch_commerces" and fetch_result is None:
                fetch_result, note = self._run_fetch_with_fallback(
                    adapter_message,
                    fallback_message=fallback_adapter_message,
                    category_hint=category_hint,
                    qualifier=qualifier_hint,
                )
                if note:
                    fallback_notice = fallback_notice or note
            elif action.tool == "analyze_city":
                if not fetch_result:
                    fetch_result, note = self._run_fetch_with_fallback(
                        adapter_message,
                        fallback_message=fallback_adapter_message,
                        category_hint=category_hint,
                        qualifier=qualifier_hint,
                    )
                    if note:
                        fallback_notice = fallback_notice or note
                analysis_result = self.pipeline.run_from_agent(fetch_result)
                map_path = analysis_result.map_file
            elif action.tool == "respond_direct":
                continue

        if needs_fetch and fetch_result is None:
            raise RuntimeError("Impossible d'obtenir les commerces depuis la requête utilisateur.")

        if fetch_result and fetch_result.places and not wants_analysis:
            map_path = self.pipeline.build_points_map(fetch_result)

        context = self._build_context(
            fetch_result,
            analysis_result,
            map_file=map_path,
            include_analysis_details=wants_analysis,
            intent=intent,
        )
        instructions = self._build_instructions(intent, fallback_notice=fallback_notice)
        if fallback_notice:
            context += "\n\nNote : " + fallback_notice
        response = self.responder.invoke(
            {
                "message": message,
                "context": context,
                "history": history_text,
                "instructions": instructions,
            }
        )
        answer = getattr(response, "content", "Réponse générée.")
        return AgentOutcome(
            answer=answer,
            fetch=fetch_result,
            analysis=analysis_result,
            map_file=map_path,
            intent=intent,
        )

    # ------------------------------------------------------------------
    def _build_context(
        self,
        fetch: AgentPayload | None,
        analysis: PipelineArtifacts | None,
        *,
        map_file: Path | None,
        include_analysis_details: bool,
        intent: ConversationIntent,
    ) -> str:
        parts: List[str] = []
        if fetch:
            base = (
                f"Ville: {fetch.city}\nCatégorie: {fetch.category_label or fetch.category_key}\n"
                f"Nombre total: {fetch.count}"
            )
            if intent == ConversationIntent.LISTING and fetch.places:
                examples = ", ".join(p.name or "(sans nom)" for p in fetch.places[:5])
                base += f"\nExemples: {examples}"
            parts.append(base)
        else:
            parts.append(
                "Aucune donnée structurée extraite. Réponds librement en t'appuyant sur tes connaissances générales."
            )
        if analysis and fetch:
            if include_analysis_details:
                zone_lines = [
                    (
                        f"Zone {z.zone_id}: population≈{int(z.population)} habitants, "
                        f"commerces existants={z.existing_commerces}, "
                        f"centre lat={z.lat:.4f}, lon={z.lon:.4f}"
                    )
                    for z in analysis.zones[:5]
                ]
                parts.append(
                    "Carte: " + str(analysis.map_file)
                    + "\nHabitants: " + str(analysis.inhabitants_file)
                    + "\nZones recommandées:\n" + "\n".join(zone_lines)
                )
            else:
                parts.append("Carte générée: " + str(analysis.map_file))
        elif map_file:
            parts.append("Carte simple: " + str(map_file))
        return "\n\n".join(parts)

    def _format_history(self, prior_turns: Sequence[Tuple[str, str]]) -> str:
        if not prior_turns:
            return "Aucun échange précédent."
        lines: List[str] = []
        for idx, (user, agent) in enumerate(reversed(prior_turns), start=1):
            lines.append(f"{idx}. Utilisateur : {user}")
            lines.append(f"   Agent : {agent}")
        return "\n".join(lines)

    def _build_instructions(self, intent: ConversationIntent, *, fallback_notice: Optional[str]) -> str:
        notice = ""
        if fallback_notice:
            notice = (
                " Mentionne en introduction que la recherche précise n'a rien donné "
                "et que tu fournis la catégorie plus générale conformément à la note."
            )
        if intent == ConversationIntent.ANALYSIS:
            return (
                "L'utilisateur attend une analyse stratégique (zones, habitants, concurrence). "
                "Présente les zones numérotées, explique pourquoi elles sont pertinentes, suggère la consultation de la carte et ne répète pas la liste détaillée des commerces."
                + notice
            )
        if intent == ConversationIntent.LISTING:
            return (
                "L'utilisateur souhaite uniquement un recensement des commerces (nombre total, exemples). "
                "Reste factuel : pas de recommandation d'implantation, pas de carte si elle n'est pas demandée."
                + notice
            )
        return (
            "La demande est conversationnelle ou porte sur des précisions générales. "
            "Réponds de façon claire en t'appuyant sur le contexte structuré quand il existe et propose, si utile, une clarification simple."
            + notice
        )

    def _detect_intent(self, message: str) -> ConversationIntent:
        normalized = message.lower().replace("’", "'")
        analysis_keywords = (
            "implanter",
            "implantation",
            "emplacement",
            "où placer",
            "ou placer",
            "où installer",
            "ou installer",
            "où ouvrir",
            "ou ouvrir",
            "où implanter",
            "ou implanter",
            "où se situer",
            "ou se situer",
            "conseil",
            "conseils",
            "stratégie",
            "strategie",
            "analyse",
            "analyser",
            "carte",
            "zones recommand",
            "zone recommand",
            "densité",
            "densite",
            "quartier idéal",
            "quartier ideal",
            "population",
        )
        listing_keywords = (
            "liste",
            "list ",
            "quels sont",
            "combien",
            "nombre",
            "compte",
            "compter",
            "donne",
            "donner",
            "affiche",
            "afficher",
            "montre",
            "montrer",
            "recense",
            "recenser",
            "inventaire",
        )
        if any(keyword in normalized for keyword in analysis_keywords):
            return ConversationIntent.ANALYSIS
        if any(keyword in normalized for keyword in listing_keywords):
            return ConversationIntent.LISTING
        return ConversationIntent.GENERAL

    def _describe_intent(self, intent: ConversationIntent) -> str:
        if intent == ConversationIntent.ANALYSIS:
            return "Analyse stratégique / recommandations d'implantation"
        if intent == ConversationIntent.LISTING:
            return "Demande de liste ou de comptage de commerces existants"
        return "Échange général ou question qualitative"

    def _build_adapter_message(
        self,
        message: str,
        *,
        prior_user_messages: Sequence[str],
        city_hint: Optional[str],
        category_hint: Optional[str],
        qualifier: Optional[str],
        include_qualifier: bool,
    ) -> str:
        """Construit une requête claire pour l'agent legacy en réutilisant les infos implicites."""
        recent_users = [user.strip() for user in prior_user_messages if user.strip()]
        tail = recent_users[-2:]
        hints: List[str] = []
        if category_hint:
            category_text = category_hint
            hints.append(f"type de commerce : {category_text}")
            if include_qualifier and qualifier and qualifier not in category_text:
                hints[-1] += f" (préférence : {qualifier})"
        if city_hint:
            hints.append(f"ville ciblée : {city_hint}")

        sections: List[str] = []
        if hints:
            sections.append("Paramètres déduits -> " + " ; ".join(hints))
        sections.append(f"Instruction utilisateur : {message.strip()}")
        if tail:
            sections.append("Historique pertinent : " + " | ".join(tail))
        return "\n".join(sections)

    def _infer_parameters(
        self,
        prior_user_messages: Sequence[str],
        *,
        latest_message: str,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Analyse les derniers messages utilisateur pour déduire ville et catégorie."""
        city: Optional[str] = None
        category: Optional[str] = None
        qualifier: Optional[str] = None
        history = list(prior_user_messages) + [latest_message]
        for raw_text in reversed(history):
            text = raw_text.strip()
            if not text:
                continue
            if city is None:
                city = self._extract_city_hint(text)
            if category is None:
                cat, qual = self._extract_category_hint(text)
                if cat:
                    category = cat
                    qualifier = qual
            elif qualifier is None:
                _, qual = self._extract_category_hint(text)
                if qual:
                    qualifier = qual
            if city and category:
                break
        return city, category, qualifier

    def _run_fetch_with_fallback(
        self,
        primary_message: str,
        *,
        fallback_message: Optional[str],
        category_hint: Optional[str],
        qualifier: Optional[str],
    ) -> tuple[AgentPayload, Optional[str]]:
        try:
            return self.adapter.run_from_message(primary_message), None
        except Exception as exc:  # noqa: BLE001
            if not fallback_message or not qualifier or not self._should_retry_with_general(exc):
                raise
            logger.info("Retrying commerce fetch with generalized parameters: %s", exc)
            payload = self.adapter.run_from_message(fallback_message)
            notice = self._build_fallback_notice(category_hint, qualifier)
            return payload, notice

    def _should_retry_with_general(self, error: Exception) -> bool:
        message = str(error).lower()
        keywords = (
            "catégorie inconnue",
            "categorie inconnue",
            "aucun résultat",
            "aucun resultat",
            "aucun commerce",
            "introuvable",
        )
        return any(keyword in message for keyword in keywords)

    def _build_fallback_notice(self, category_hint: Optional[str], qualifier: Optional[str]) -> str:
        if category_hint and qualifier:
            return (
                f"Impossible de trouver des {category_hint} correspondant à la demande précise « {qualifier} ». "
                f"Présente les {category_hint} disponibles."
            )
        return "Impossible de trouver la version spécifique demandée. Présente les résultats les plus proches."

    def _extract_city_hint(self, text: str) -> Optional[str]:
        match = CITY_REGEX.search(text.lower())
        if not match:
            return None
        candidate = match.group(1).strip(" ,;.!?'\"")
        if not candidate:
            return None
        return candidate

    def _extract_category_hint(self, text: str) -> tuple[Optional[str], Optional[str]]:
        lowered = text.lower()
        for keyword in CATEGORY_KEYWORDS:
            pattern = rf"\b{re.escape(keyword)}\b"
            match = re.search(pattern, lowered)
            if not match:
                continue
            qualifier = self._extract_qualifier(lowered[match.end() :])
            normalized = self._normalize_category(keyword)
            return normalized, qualifier
        return None, None

    def _extract_qualifier(self, suffix: str) -> Optional[str]:
        fragment = suffix
        for stop in CATEGORY_STOP_TOKENS:
            idx = fragment.find(stop)
            if idx != -1:
                fragment = fragment[:idx]
                break
        qualifier = fragment.strip(" -,:;'\"")
        return qualifier or None

    def _normalize_category(self, keyword: str) -> str:
        singular_map = {
            "restaurant": "restaurants",
            "restaurants": "restaurants",
            "pharmacie": "pharmacies",
            "pharmacies": "pharmacies",
            "boulangerie": "boulangeries",
            "boulangeries": "boulangeries",
            "boucherie": "boucheries",
            "boucheries": "boucheries",
            "supermarché": "supermarchés",
            "supermarchés": "supermarchés",
            "supermarches": "supermarchés",
            "supérette": "supérettes",
            "superette": "supérettes",
            "supérettes": "supérettes",
            "bars": "bars",
            "bar": "bars",
            "café": "cafés",
            "cafés": "cafés",
            "coiffeur": "coiffeurs",
            "coiffeurs": "coiffeurs",
            "coiffure": "coiffure",
            "pressing": "pressing",
            "pressings": "pressing",
            "épicerie": "épiceries",
            "épiceries": "épiceries",
            "epicerie": "épiceries",
            "epiceries": "épiceries",
            "bazar": "bazar",
            "boutique": "boutiques",
            "boutiques": "boutiques",
            "magasin": "magasins",
            "magasins": "magasins",
            "garage": "garages",
            "garages": "garages",
            "hotel": "hôtels",
            "hotels": "hôtels",
            "hôtel": "hôtels",
            "hôtels": "hôtels",
            "commerce": "commerces",
            "commerces": "commerces",
        }
        return singular_map.get(keyword, keyword)

    def build_title(self, user_message: str, agent_answer: str) -> str:
        try:
            response = self.titler.invoke({"user": user_message, "agent": agent_answer})
            title = getattr(response, "content", "").strip()
        except Exception:  # noqa: BLE001
            title = ""
        if not title:
            title = user_message.strip().capitalize()[:60] or "Conversation"
        return title

    def build_error_answer(self, user_message: str, error: Exception | None = None) -> str:
        detail = self._friendly_error_reason(error)
        question = self._followup_question(user_message)
        base = "Je rencontre un souci pour récupérer les données demandées."
        if detail:
            base += f" {detail}"
        return f"{base} {question} Je prendrai en compte ta réponse pour la prochaine itération."

    def _friendly_error_reason(self, error: Exception | None) -> str:
        if error is None:
            return ""
        message = str(error).strip()
        if not message:
            return ""
        lower = message.lower()
        if "catégorie inconnue" in lower:
            return "Le type de commerce demandé n'est pas reconnu par nos données."
        if "préciser la ville" in lower or "preciser la ville" in lower:
            return "J'ai besoin que tu confirmes la ville visée."
        if "overpass" in lower or "timeout" in lower or "504" in lower:
            return "Le service cartographique externe ne répond pas pour l'instant."
        if "http error" in lower or "client" in lower or "gateway" in lower:
            return "Le service externe a refusé ou interrompu la requête."
        return "Je dois relancer la recherche avec quelques précisions supplémentaires."

    def _followup_question(self, user_message: str) -> str:
        normalized = user_message.lower().replace("’", "'")
        has_city_hint = any(
            marker in normalized for marker in (" ville", "commune", "quartier", " à ", " a ", " sur ", " dans ")
        )
        has_category_hint = any(
            marker in normalized
            for marker in (
                "commerce",
                "commerces",
                "magasin",
                "boutique",
                "restaurant",
                "categorie",
                "catégorie",
                "type",
                "activité",
                "activite",
            )
        )
        if not has_city_hint and not has_category_hint:
            return "Peux-tu me confirmer la ville et le type de commerce que tu souhaites analyser afin que je relance la recherche ?"
        if not has_city_hint:
            return "Peux-tu me préciser la ville concernée pour que je relance la recherche ?"
        if not has_category_hint:
            return "Peux-tu préciser le type de commerce recherché pour que j'interroge les bonnes données ?"
        return "As-tu d'autres précisions utiles (budget, quartier cible, contraintes) pour que j'affine la prochaine réponse ?"

__all__ = ["CityInsightsAgent", "AgentOutcome", "ConversationIntent"]
