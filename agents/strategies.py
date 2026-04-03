"""Reasoning strategies."""

from __future__ import annotations

from ..core.models import AgentRequest, ToolUse
from ..core.services import Services
from ..core.context import ContextWindow


def _prompt(prefix: str, message: str) -> str:
    return f"{prefix}\nUser: {message}"


class ChatStrategy:
    def respond(
        self, request: AgentRequest, services: Services
    ) -> tuple[str, list[str], list[ToolUse]]:
        text = services.llm.complete(
            _prompt("Answer clearly and directly.", request.message)
        )
        return text, ["chat:completed"], []


class ReactStrategy:
    def respond(
        self, request: AgentRequest, services: Services
    ) -> tuple[str, list[str], list[ToolUse]]:
        tool_calls: list[ToolUse] = []
        if request.tool_plan:
            observations: list[str] = []
            for planned in request.tool_plan:
                output = services.tools.call(planned.name, planned.input)
                tool_calls.append(
                    ToolUse(name=planned.name, input=planned.input, output=output)
                )
                observations.append(f"{planned.name}: {output}")
            observation = "\n".join(observations)
        else:
            output = services.tools.call("echo", request.message)
            tool_calls.append(
                ToolUse(name="echo", input=request.message, output=output)
            )
            observation = output

        text = services.llm.complete(
            "Use the observation to answer the user.\n"
            f"Observation: {observation}\n"
            f"Question: {request.message}"
        )
        return text, ["react:tool_observation", "react:completed"], tool_calls


class ReflectStrategy:
    def respond(
        self, request: AgentRequest, services: Services
    ) -> tuple[str, list[str], list[ToolUse]]:
        draft = services.llm.complete(
            _prompt("Draft a first-pass answer.", request.message)
        )
        refined = services.llm.complete(
            f"Improve this draft for correctness and readability.\nDraft: {draft}"
        )
        return refined, ["reflect:draft", "reflect:refined"], []


class PlanExecuteStrategy:
    def respond(
        self, request: AgentRequest, services: Services
    ) -> tuple[str, list[str], list[ToolUse]]:
        plan = services.llm.complete(
            f"Create a concise numbered plan.\nTask: {request.message}"
        )
        answer = services.llm.complete(
            "Execute the plan and return final answer.\n"
            f"Plan: {plan}\n"
            f"Task: {request.message}"
        )
        return answer, ["plan_execute:planned", "plan_execute:executed"], []


class RAGStrategy:
    """Retrieval-Augmented Generation strategy."""

    def __init__(self, retriever) -> None:
        self.retriever = retriever

    def respond(
        self, request: AgentRequest, services: Services
    ) -> tuple[str, list[str], list[ToolUse]]:
        # Retrieve relevant documents
        documents = self.retriever.retrieve(request.message, top_k=3)
        context_text = "\n\n".join(f"[Doc {i+1}] {doc}" for i, doc in enumerate(documents))

        # Generate answer with retrieved context
        text = services.llm.complete(
            f"Answer using the retrieved documents as context.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {request.message}"
        )
        return text, ["rag:retrieved", "rag:completed"], []
