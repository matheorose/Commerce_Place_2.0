"""LLM-driven coordinator that decides which backend tools to run."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, List, Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..models.domain import AgentPayload, PipelineArtifacts
from .agent_adapter import AgentAdapter
from .pipeline import PipelineService


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


PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Tu es un orchestrateur qui programme l'utilisation de deux outils :
- fetch_commerces : interroger l'agent historique pour obtenir un fichier JSON des commerces (ville + type) à partir du message utilisateur.
- analyze_city : lancer l'analyse INSEE + KMeans en utilisant le dernier fichier JSON généré.
Tu peux aussi répondre directement (« respond_direct ») quand une question est simple et ne nécessite pas de récupération de données réelles.

Ton but est de répondre aux besoins de l'utilisateur en listant les actions nécessaires.
Renvoie un plan contenant 1 à 2 actions maximum. Par exemple :
- Si la requête demande seulement les commerces -> fetch_commerces.
- Si l'utilisateur veut des conseils d'implantation, une carte ou une analyse -> fetch_commerces puis analyze_city.
Si l'utilisateur pose une question générale ou demande un échange qui ne dépend pas des outils, renvoie seulement respond_direct.
N'ajoute une action analyze_city que si l'analyse de population est pertinente.

Historique des 5 derniers échanges (du plus ancien au plus récent) pour te donner du contexte :
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
Tu es CityInsights, un expert en stratégie commerciale.
Tu disposes des données suivantes obtenues automatiquement :
- Informations sur les commerces (ville, catégorie, nombre de lieux, exemples).
- Analyse habitants + zones issues de KMeans (chaque zone contient la population estimée et le nombre de commerces similaires).

Historique des 5 derniers échanges (du plus ancien au plus récent) :
{history}

Suis attentivement les instructions fournies pour chaque réponse.

Rédige une réponse en français en expliquant clairement :
1. Les résultats de recherche (nombre de commerces, infos clés).
2. Si l'analyse est disponible, décris les zones recommandées sans employer le mot "cluster" (parle de « Zone 1 », etc.) et prends en compte la densité d'habitants et la concurrence déjà présente.
3. Explique pourquoi une zone est pertinente (ex : forte population mais peu de commerces) et invite à consulter la carte lorsque c'est utile.
4. Si aucune donnée structurée n'est fournie, réponds simplement à la question de l'utilisateur en t'appuyant sur ton expertise générale.
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
        self.memory: Deque[tuple[str, str]] = deque(maxlen=5)
        self.user_history: Deque[str] = deque(maxlen=5)

    def run(self, message: str) -> AgentOutcome:
        fetch_result: AgentPayload | None = None
        analysis_result: PipelineArtifacts | None = None
        map_path: Path | None = None

        self._remember_user(message)
        history_text = self._format_history()
        plan = self.planner.invoke({"message": message, "history": history_text})
        actions = plan.actions or [ToolAction(tool="fetch_commerces", reason="Par défaut")]  # type: ignore[arg-type]
        adapter_message = self._build_adapter_message(message)
        analysis_required = self._requires_analysis(adapter_message)
        if analysis_required and not any(a.tool == "analyze_city" for a in actions):
            if not any(a.tool == "fetch_commerces" for a in actions):
                actions.insert(
                    0,
                    ToolAction(tool="fetch_commerces", reason="Analyse requise pour recommander un emplacement."),
                )
            actions.append(ToolAction(tool="analyze_city", reason="Analyse requise pour recommander un emplacement."))

        needs_fetch = any(a.tool in {"fetch_commerces", "analyze_city"} for a in actions)
        wants_analysis = analysis_required or any(a.tool == "analyze_city" for a in actions)

        for action in actions:
            if action.tool == "fetch_commerces" and fetch_result is None:
                fetch_result = self.adapter.run_from_message(adapter_message)
            elif action.tool == "analyze_city":
                if not fetch_result:
                    fetch_result = self.adapter.run_from_message(adapter_message)
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
        )
        instructions = self._build_instructions(message, wants_analysis)
        response = self.responder.invoke(
            {
                "message": message,
                "context": context,
                "history": history_text,
                "instructions": instructions,
            }
        )
        answer = getattr(response, "content", "Réponse générée.")
        self._remember(message, answer)

        return AgentOutcome(answer=answer, fetch=fetch_result, analysis=analysis_result, map_file=map_path)

    # ------------------------------------------------------------------
    def _build_context(
        self,
        fetch: AgentPayload | None,
        analysis: PipelineArtifacts | None,
        *,
        map_file: Path | None,
        include_analysis_details: bool,
    ) -> str:
        parts: List[str] = []
        if fetch:
            parts.append(
                f"Ville: {fetch.city}\nCatégorie: {fetch.category_label or fetch.category_key}\n"
                f"Nombre total: {fetch.count}\nExemples: "
                + ", ".join(p.name or "(sans nom)" for p in fetch.places[:5])
            )
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

    def _format_history(self) -> str:
        if not self.memory:
            return "Aucun échange précédent."
        return "\n\n".join(
            f"Utilisateur : {user}\nAgent : {agent}"
            for user, agent in self.memory
        )

    def _remember(self, user_message: str, agent_answer: str) -> None:
        self.memory.append((user_message, agent_answer))

    def _remember_user(self, user_message: str) -> None:
        self.user_history.append(user_message)

    def _build_instructions(self, message: str, wants_analysis: bool) -> str:
        if wants_analysis:
            return (
                "L'utilisateur a demandé des recommandations d'implantation ou une analyse détaillée. "
                "Tu dois décrire les zones et conseiller l'utilisateur."
            )
        return (
            "L'utilisateur souhaite uniquement obtenir les commerces existants (par exemple le nombre). "
            "Réponds en te concentrant sur le comptage et la description des commerces, "
            "sans ajouter d'analyse stratégique ou de recommandation de zone."
        )

    def _build_adapter_message(self, message: str) -> str:
        """Enrichit le message envoyé à l'agent legacy avec le dernier contexte utilisateur pertinent."""
        # On exclut le message courant (déjà stocké en dernière position).
        historical = list(self.user_history)[:-1]
        recent_users = [user for user in historical if user.strip()]
        if not recent_users:
            return message
        tail = recent_users[-2:]
        tail = [text for text in tail if text.strip()]
        if not tail:
            return message
        history = " ".join(part.strip().rstrip("?") for part in tail)
        combined = f"{history} {message}".strip()
        return combined

    def _requires_analysis(self, message: str) -> bool:
        normalized = message.lower()
        keywords = ("placer", "implanter", "installer", "où puis-je", "ou puis-je", "emplacement")
        return any(keyword in normalized for keyword in keywords)

__all__ = ["CityInsightsAgent", "AgentOutcome"]
