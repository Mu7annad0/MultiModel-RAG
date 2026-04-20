import logging
from typing import Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START

from backend.agents.state import AgentState
from backend.agents.nodes import AgentNodes
from backend.agents.tools import create_search_tool


logger = logging.getLogger(__name__)


def create_rag_agent(
    settings: Any, embedding_client: Any, vdb_client: Any, generation_client: Any = None
):
    logger.info("Creating RAG agent graph...")

    if generation_client is None:
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for agent")
        generation_llm = ChatOpenAI(api_key=api_key, model="gpt-5-mini")
    else:
        generation_llm = (
            generation_client.provider.client
            if hasattr(generation_client, "provider")
            and hasattr(generation_client.provider, "client")
            else generation_client
        )

    search_tool = create_search_tool(embedding_client, vdb_client, settings)

    agent_nodes = AgentNodes(generation_llm, search_tool)

    builder = StateGraph(AgentState)

    builder.add_node("analyze_query", agent_nodes.analyze_query)
    builder.add_node("search", agent_nodes.search_documents)
    builder.add_node("evaluate_results", agent_nodes.evaluate_results)
    builder.add_node("refine_query", agent_nodes.refine_query)
    builder.add_node("generate_response", agent_nodes.generate_response)

    builder.add_edge(START, "analyze_query")

    builder.add_conditional_edges(
        "analyze_query",
        agent_nodes.should_search,
        {"search": "search", "generate": "generate_response"},
    )

    builder.add_edge("search", "evaluate_results")

    builder.add_conditional_edges(
        "evaluate_results",
        agent_nodes.evaluate_and_route,
        {"refine": "refine_query", "generate": "generate_response"},
    )

    builder.add_edge("refine_query", "search")

    builder.add_edge("generate_response", END)

    agent = builder.compile()

    logger.info("RAG agent graph compiled successfully")

    return agent


__all__ = ["create_rag_agent", "AgentState"]
