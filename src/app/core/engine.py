import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from .models import Agent

load_dotenv()


# Define State
class AgentState(TypedDict):
    """The state of the agent graph."""

    messages: list[BaseMessage]


class AgentEngine:
    """The core engine that runs agents via LangGraph."""

    llm: BaseChatModel

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

        # Use agent-specific provider if set, otherwise use global env
        env_provider = os.getenv("AI_PROVIDER", "ollama") or "ollama"
        raw_provider = agent.ai_provider or env_provider
        provider = raw_provider.lower()

        if provider == "ollama":
            self.llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3"),
                temperature=0.7,
            )
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found and provider is 'openai'")

            self.llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                api_key=api_key,  # type: ignore[arg-type]
                temperature=0.7,
            )
        else:
            # Fallback to Gemini
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found and provider is 'gemini'")

            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.7,
            )

        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(AgentState)

        # Define the Node
        def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
            messages = state["messages"]
            system_prompt = SystemMessage(
                content=f"Role: {self.agent.role}\nInstructions: {self.agent.instructions}"
            )

            # LangChain models take a list. We'll merge system + history.
            prompt_messages: list[BaseMessage] = [system_prompt] + messages
            response = self.llm.invoke(prompt_messages)
            return {"messages": [response]}

        workflow.add_node("agent", call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        return workflow.compile()

    async def ainvoke(self, message: str) -> str:
        """Runs the graph with a single user message."""
        inputs = {"messages": [HumanMessage(content=message)]}
        result = await self.graph.ainvoke(inputs)
        last_message: BaseMessage = result["messages"][-1]
        return str(last_message.content)
