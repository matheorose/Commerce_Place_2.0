"""LLM-driven coordinator that decides which backend tools to run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..models.domain import AgentPayload, PipelineArtifacts
from .agent_adapter import AgentAdapter
from .pipeline import PipelineService


class ToolAction(BaseModel):
    """Represents a single step selected by the planner LLM."""

    tool: Literal["fetch_commerces", "analyze_city"]
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


PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Tu es un orchestrateur qui programme l'utilisation de deux outils :
- fetch_commerces : interroger l'agent historique pour obtenir un fichier JSON des commerces (ville + type) à partir du message utilisateur.
- analyze_city : lancer l'analyse INSEE + KMeans en utilisant le dernier fichier JSON généré.

Ton but est de répondre aux besoins de l'utilisateur en listant les actions nécessaires.
Renvoie un plan contenant 1 à 2 actions maximum. Par exemple :
- Si la requête demande seulement les commerces -> fetch_commerces.
- Si l'utilisateur veut des conseils d'implantation, une carte ou une analyse -> fetch_commerces puis analyze_city.
N'ajoute une action analyze_city que si l'analyse de population est pertinente.
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

Rédige une réponse en français en expliquant clairement :
1. Les résultats de recherche (nombre de commerces, infos clés).
2. Si l'analyse est disponible, décris les zones recommandées sans employer le mot "cluster" (parle de « Zone 1 », etc.) et prends en compte la densité d'habitants et la concurrence déjà présente.
3. Explique pourquoi une zone est pertinente (ex : forte population mais peu de commerces) et invite à consulter la carte lorsque c'est utile.
""".strip(),
        ),
        ("human", "{message}"),
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

    def run(self, message: str) -> AgentOutcome:
        fetch_result: AgentPayload | None = None
        analysis_result: PipelineArtifacts | None = None

        plan = self.planner.invoke({"message": message})
        actions = plan.actions or [ToolAction(tool="fetch_commerces", reason="Par défaut")]  # type: ignore[arg-type]

        for action in actions:
            if action.tool == "fetch_commerces" and fetch_result is None:
                fetch_result = self.adapter.run_from_message(message)
            elif action.tool == "analyze_city":
                if not fetch_result:
                    fetch_result = self.adapter.run_from_message(message)
                analysis_result = self.pipeline.run_from_agent(fetch_result)

        if fetch_result is None:
            raise RuntimeError("Impossible d'obtenir les commerces depuis la requête utilisateur.")
        if analysis_result is None and any(a.tool == "analyze_city" for a in actions):
            analysis_result = self.pipeline.run_from_agent(fetch_result)

        context = self._build_context(fetch_result, analysis_result)
        response = self.responder.invoke({"message": message, "context": context})
        answer = getattr(response, "content", "Réponse générée.")

        return AgentOutcome(answer=answer, fetch=fetch_result, analysis=analysis_result)

    # ------------------------------------------------------------------
    def _build_context(
        self,
        fetch: AgentPayload,
        analysis: PipelineArtifacts | None,
    ) -> str:
        parts: List[str] = []
        parts.append(
            f"Ville: {fetch.city}\nCatégorie: {fetch.category_label or fetch.category_key}\n"
            f"Nombre total: {fetch.count}\nExemples: "
            + ", ".join(p.name or "(sans nom)" for p in fetch.places[:5])
        )
        if analysis:
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
        return "\n\n".join(parts)


__all__ = ["CityInsightsAgent", "AgentOutcome"]
