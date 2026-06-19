"""LangGraph pipeline definition.

Three-node graph: intent → requirements → response.
Compiled once at import time and shared across requests.
"""

from langgraph.graph import END, StateGraph

from app.agents.intent_agent import intent_agent
from app.agents.requirements_agent import requirements_agent
from app.agents.response_agent import response_agent
from app.state import shortlistState

graph = StateGraph(shortlistState)

graph.add_node("intent", intent_agent)
graph.add_node("requirements", requirements_agent)
graph.add_node("response", response_agent)

graph.set_entry_point("intent")
graph.add_edge("intent", "requirements")
graph.add_edge("requirements", "response")
graph.add_edge("response", END)

compiled_graph = graph.compile()
