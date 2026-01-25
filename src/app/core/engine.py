import os
from dotenv import load_dotenv
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from .models import Agent
from langchain_ollama import ChatOllama

# Define State
class AgentState(TypedDict):
    messages: List[BaseMessage]

class AgentEngine:
    def __init__(self, agent: Agent):
        self.agent = agent
        
        provider = os.getenv("AI_PROVIDER", "gemini").lower()
        
        if provider == "ollama":
            self.llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3"),
                temperature=0.7
            )
        else:
            # Fallback to Gemini
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                # If no key, default to ollama to be safe? No, raise error if gemini requested.
                raise ValueError("GEMINI_API_KEY not found and provider is 'gemini'")
                
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.7
            )

        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Define the Node
        def call_model(state: AgentState):
            messages = state["messages"]
            # Prepend System Prompt if not present (simple check)
            # ideally we manage history better, but for MVP:
            system_prompt = SystemMessage(content=f"Role: {self.agent.role}\nInstructions: {self.agent.instructions}")
            
            # If the first message isn't system, add it contextually (or just pass it to Invoke)
            # LangChain models take a list. We'll merge system + history.
            response = self.llm.invoke([system_prompt] + messages)
            return {"messages": [response]}

        workflow.add_node("agent", call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        return workflow.compile()

    async def ainvoke(self, message: str):
        """Runs the graph with a single user message."""
        inputs = {"messages": [HumanMessage(content=message)]}
        # We use ainvoke for async execution
        result = await self.graph.ainvoke(inputs)
        # Extract last message content
        return result["messages"][-1].content
