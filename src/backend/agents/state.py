from typing import TypedDict, List, Optional
from backend.clients.vdb import RetrievedDocument


class AgentState(TypedDict):
    document_id: str
    original_query: str
    chat_history: List[dict]

    needs_search: bool
    search_reasoning: str

    use_split: bool
    use_filter: bool
    limit: int

    search_iterations: int
    max_iterations: int

    current_query: str
    sub_queries: Optional[List[str]]

    retrieved_chunks: List[RetrievedDocument]
    total_chunks_found: int
    queries_used: List[str]

    evaluation_result: str
    refinement_reason: Optional[str]

    generation_prompt: Optional[str]

    final_answer: str
    error: Optional[str]
