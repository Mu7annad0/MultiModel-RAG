import json
import logging
from typing import Dict, Any, List, Literal
from langchain_core.runnables import RunnableConfig

from backend.agents.state import AgentState
from backend.agents.prompts import (
    ANALYZE_QUERY_PROMPT,
    EVALUATE_RESULTS_PROMPT,
    REFINE_QUERY_PROMPT,
    SYSTEM_PROMPT,
    DOCUMENT_PROMPT,
    FOOTER_PROMPT,
)
from backend.clients.vdb import RetrievedDocument


logger = logging.getLogger(__name__)


def format_chat_history(chat_history: List[Dict[str, str]]) -> str:
    if not chat_history:
        return "No previous conversation."

    formatted = []
    for msg in chat_history[-10:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role.upper()}: {content}")

    return "\n".join(formatted)


def format_chunks(chunks: List[RetrievedDocument]) -> str:
    if not chunks:
        return "No chunks retrieved."

    formatted = []
    for i, chunk in enumerate(chunks):
        formatted.append(f"Chunk {i} (Score: {chunk.score:.3f}):\n{chunk.text}\n")

    return "\n".join(formatted)


def parse_json_response(content: str) -> Dict:
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except (json.JSONDecodeError, IndexError) as e:
        logger.error(f"Error parsing JSON response: {str(e)}")
        return {}


class AgentNodes:
    def __init__(self, llm, search_tool=None):
        self.llm = llm
        self.search_tool = search_tool

    def should_search(self, state: AgentState) -> Literal["search", "generate"]:
        if state.get("needs_search", True):
            return "search"
        return "generate"

    def evaluate_and_route(self, state: AgentState) -> Literal["refine", "generate"]:
        result = state.get("evaluation_result", "sufficient")
        iterations = state.get("search_iterations", 0)
        max_iterations = state.get("max_iterations", 3)

        if result == "sufficient" or iterations >= max_iterations:
            return "generate"
        return "refine"

    async def analyze_query(
        self, state: AgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        logger.info("Analyzing query to determine search necessity...")

        prompt = ANALYZE_QUERY_PROMPT.substitute(
            query=state["original_query"],
            chat_history=format_chat_history(state["chat_history"]),
        )

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content
            if not isinstance(content, str):
                content = str(content) if content else ""

            decision = parse_json_response(content)

            needs_search = decision.get("needs_search", True)
            reasoning = decision.get("reasoning", "No reasoning provided")

            logger.info(
                f"Query analysis: needs_search={needs_search}, reasoning={reasoning}"
            )

            return {
                "needs_search": needs_search,
                "search_reasoning": reasoning,
                "current_query": state["original_query"],
                "use_split": state.get("use_split", False),
                "use_filter": state.get("use_filter", False),
                "limit": state.get("limit", 6),
            }

        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}")
            return {
                "needs_search": True,
                "search_reasoning": f"Analysis failed: {str(e)}. Defaulting to search.",
                "current_query": state["original_query"],
                "use_split": state.get("use_split", False),
                "use_filter": state.get("use_filter", False),
                "limit": state.get("limit", 6),
            }

    async def search_documents(
        self, state: AgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        logger.info("Searching documents...")

        if not self.search_tool:
            logger.error("Search tool not initialized")
            return {
                "retrieved_chunks": [],
                "total_chunks_found": 0,
                "queries_used": [],
                "error": "Search tool not available",
            }

        try:
            result_json = await self.search_tool.ainvoke(
                {
                    "query": state["current_query"],
                    "document_id": state["document_id"],
                    "use_split": state.get("use_split", False),
                    "use_filter": state.get("use_filter", False),
                    "limit": state.get("limit", 6),
                }
            )

            if isinstance(result_json, str):
                result = json.loads(result_json)
            else:
                result = result_json

            chunks_data = result.get("chunks", [])
            retrieved_chunks = [
                RetrievedDocument(
                    text=chunk.get("text", ""),
                    score=chunk.get("score", 0.0),
                    metadata=chunk.get("metadata", {}),
                )
                for chunk in chunks_data
            ]

            logger.info(f"Search completed. Found {len(retrieved_chunks)} chunks")

            return {
                "retrieved_chunks": retrieved_chunks,
                "total_chunks_found": result.get("total_found", 0),
                "queries_used": result.get("queries_used", [state["current_query"]]),
            }

        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return {
                "retrieved_chunks": [],
                "total_chunks_found": 0,
                "queries_used": [state["current_query"]],
                "error": str(e),
            }

    async def evaluate_results(
        self, state: AgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        logger.info("Evaluating search results...")

        if state["search_iterations"] >= state["max_iterations"]:
            logger.info(
                f"Max iterations ({state['max_iterations']}) reached. Accepting results."
            )
            return {
                "evaluation_result": "sufficient",
                "refinement_reason": "Maximum search iterations reached",
            }

        chunks = state.get("retrieved_chunks", [])
        if not chunks:
            logger.info("No chunks retrieved. Marking as insufficient.")
            return {
                "evaluation_result": "insufficient",
                "refinement_reason": "No relevant documents found",
            }

        prompt = EVALUATE_RESULTS_PROMPT.substitute(
            query=state["current_query"],
            chunks=format_chunks(chunks),
            chat_history=format_chat_history(state["chat_history"]),
        )

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content
            if not isinstance(content, str):
                content = str(content) if content else ""

            evaluation = parse_json_response(content)

            result = evaluation.get("result", "sufficient")
            reason = evaluation.get("reason", "No reason provided")

            logger.info(f"Evaluation: {result}, reason: {reason}")

            return {
                "evaluation_result": result,
                "refinement_reason": reason,
                "search_iterations": state["search_iterations"] + 1,
            }

        except Exception as e:
            logger.error(f"Error evaluating results: {str(e)}")
            return {
                "evaluation_result": "sufficient",
                "refinement_reason": f"Evaluation error: {str(e)}",
            }

    async def refine_query(
        self, state: AgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        logger.info("Refining query based on evaluation...")

        prompt = REFINE_QUERY_PROMPT.substitute(
            original_query=state["current_query"],
            previous_results=format_chunks(state.get("retrieved_chunks", [])),
            reason=state.get("refinement_reason", "Results were insufficient"),
        )

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content
            if not isinstance(content, str):
                content = str(content) if content else ""

            refined = parse_json_response(content)

            new_query = refined.get("refined_query", state["current_query"])
            sub_queries = refined.get("sub_queries")

            logger.info(
                f"Query refined from '{state['current_query']}' to '{new_query}'"
            )
            if sub_queries:
                logger.info(f"Sub-queries: {sub_queries}")

            return {"current_query": new_query, "sub_queries": sub_queries}

        except Exception as e:
            logger.error(f"Error refining query: {str(e)}")
            modified_query = f"{state['current_query']} (detailed information)"
            return {"current_query": modified_query, "sub_queries": None}

    async def generate_response(
        self, state: AgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        logger.info("Preparing generation prompt...")

        chunks = state.get("retrieved_chunks", [])
        chat_history = state.get("chat_history", [])

        if chunks:
            documents_prompt = "\n".join(
                DOCUMENT_PROMPT.substitute(doc_no=idx + 1, doc_content=chunk.text)
                for idx, chunk in enumerate(chunks)
            )

            system_content = SYSTEM_PROMPT.substitute()
            footer = FOOTER_PROMPT.substitute(query=state["original_query"])

            prompt = f"{system_content}\n\n{documents_prompt}\n\n{footer}"

            logger.info(f"Prepared prompt with {len(chunks)} context chunks")
        else:
            system_content = SYSTEM_PROMPT.substitute()
            history_context = format_chat_history(chat_history)

            prompt = f"""{system_content}

Based on our conversation history:
{history_context}

Answer this question: {state["original_query"]}

If you cannot answer based on the conversation history, please state that clearly.
"""
            logger.info("Prepared prompt from chat history only")

        return {
            "generation_prompt": prompt,
            "final_answer": "",
            "chat_history": chat_history,
        }
