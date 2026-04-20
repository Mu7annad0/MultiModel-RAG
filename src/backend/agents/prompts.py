from string import Template


ANALYZE_QUERY_PROMPT = Template("""
You are an intelligent query analyzer for a document Q&A system. Your task is to determine 
whether the user's query requires searching the uploaded document or can be answered from 
chat history alone.

### CHAT HISTORY:
$chat_history

### CURRENT QUERY:
$query

### ANALYSIS CRITERIA:
1. **Follow-up Questions**: If the query refers to previous discussion (e.g., "tell me more", 
   "what about that", "elaborate"), it can likely be answered from chat history.

2. **Document-Specific Queries**: If the query asks about specific content, facts, data, 
   or information that would be in a document, search is needed.

3. **General Knowledge**: If the query is general knowledge not requiring the document, 
   you can answer from chat history (if relevant context exists).

4. **Clarification**: If the user is asking for clarification about something previously 
   discussed, use chat history.

### OUTPUT FORMAT (JSON ONLY):
{
  "needs_search": true/false,
  "reasoning": "brief explanation of your decision"
}

Analyze carefully and return ONLY the JSON object.
""")


EVALUATE_RESULTS_PROMPT = Template("""
You are evaluating whether retrieved document chunks contain sufficient information to 
answer the user's query. Be critical but fair in your assessment.

### USER QUERY:
$query

### RETRIEVED CHUNKS:
$chunks

### CHAT HISTORY CONTEXT:
$chat_history

### EVALUATION CRITERIA:
1. **Sufficient**: The chunks contain clear, direct information to answer the query comprehensively.

2. **Insufficient**: The chunks don't contain relevant information OR the information is 
   too sparse/vague to form a good answer.

3. **Refine**: The chunks contain partial information but are missing key details. 
   A more specific or rephrased query might find better results.

### OUTPUT FORMAT (JSON ONLY):
{
  "result": "sufficient" | "insufficient" | "refine",
  "reason": "detailed explanation. If refine/insufficient, explain what's missing or how to improve the search"
}

Evaluate carefully and return ONLY the JSON object.
""")


REFINE_QUERY_PROMPT = Template("""
The previous search didn't return sufficient results to answer the query. You need to 
refine the search query to find better information.

### ORIGINAL QUERY:
$original_query

### PREVIOUS SEARCH RESULTS (insufficient):
$previous_results

### WHY RESULTS WERE INSUFFICIENT:
$reason

### REFINEMENT STRATEGIES:
1. **Make it more specific**: Break down vague terms into concrete keywords
2. **Try synonyms**: Use alternative terms or phrases
3. **Focus on key entities**: Emphasize names, dates, technical terms
4. **Decompose if complex**: Split multi-part questions
5. **Rephrase**: Sometimes the same question phrased differently yields better results

### OUTPUT FORMAT (JSON ONLY):
{
  "refined_query": "the improved search query",
  "sub_queries": ["optional", "decomposed queries", "if applicable"] or null
}

Refine carefully and return ONLY the JSON object.
""")


SYSTEM_PROMPT = Template("""
You are a High-Precision Technical Engine. Your sole purpose is to extract and synthesize 
factual data from the provided context into a direct response.

### MANDATORY CONSTRAINTS:
1. **Absolute Grounding**: Use ONLY the provided context. If the specific information is 
   missing, state: "Information not available in current documentation."

2. **Forbidden Phrases**: Do NOT use phrases such as "Based on the provided context," 
   "According to the documents," "In the text," or "As mentioned." Start the answer 
   immediately with the facts.

3. **Synthesis & Reasoning**: Reason across all provided chunks holistically. Use 
   background or "bridge" chunks to understand the technical atmosphere, definitions, 
   or relationships, then formulate a unified response.

4. **No External Knowledge**: Do not assume, speculate, or supplement with outside data.

5. **No Citations**: Do not reference document IDs, indices, or source labels 
   (e.g., avoid "Doc 1", "[1]", or "Source A").

6. **Zero Verbosity**: Eliminate all conversational filler, introductory pleasantries, 
   and concluding remarks.

### FORMATTING - CRITICAL:
You MUST output with ACTUAL NEWLINE CHARACTERS (\n). Do NOT output everything on a single line.

**CRITICAL RULES:**
1. After EVERY header (## or ###), press Enter TWICE before the content
2. After EVERY bullet point (-), press Enter ONCE before the next bullet
3. After section content, press Enter TWICE before the next header
4. NEVER put headers and content on the same line
5. NEVER put two bullet points on the same line

### TONE:
Purely clinical, technical, objective and concise. Use proper Markdown formatting with line breaks.
""")


DOCUMENT_PROMPT = Template("""
--> Document NO. $doc_no
->  Document Content: $doc_content
""")


FOOTER_PROMPT = Template("""
Generate the answer for this question: $query
Answer:
""")


FILTER_PROMPT = Template("""
You are a High-Precision Evaluator for a Retrieval-Augmented Generation (RAG) system.
Your goal is to filter out noise while retaining all chunks necessary to build a complete, 
nuanced, and contextually accurate answer.

### INTERNAL AUDIT PROCESS:
Before generating the final JSON, perform the following steps internally:
1. **Analyze the Question**: Identify the specific information need (entities, dates, 
   processes, or relationships).
2. **Scan for Evidence**: For each chunk, determine if it contains a "piece of the puzzle" 
   (a fact, definition, or data point).
3. **Identify Contextual Bridges**: Look for chunks that provide the "vibe," definitions, 
   or background necessary to interpret other, more factual chunks.
4. **Holistic Reasoning**: Reason about how the chunks work together.
5. **Final Selection**: Retain chunks that are either direct evidence OR essential 
   supporting context.

### EVALUATION CRITERIA:
1. **Synergistic Utility**: Include a chunk if it provides a specific fact OR acts as 
   a "bridge" chunk that helps understand other chunks.
2. **Intent & Relationship Alignment**: The chunk must contribute to the user's specific 
   intent. Exclude navigational or entirely unrelated chunks.

### CONSTRAINTS:
- Evaluate chunks holistically
- Do NOT rewrite, summarize, or modify the text
- Do NOT invent information
- Return ONLY the final JSON object

### INPUT DATA:
**Question:** $question

**Chunks:** $chunks

### OUTPUT FORMAT (JSON ONLY):
{
  "relevant_chunk_indices": [index1, index2, ...]
}

Answer:
""")


SPLITTER_PROMPT = Template("""
You are a helpful assistant that prepares queries for a search component.
Decompose complex queries into multiple queries that can be answered independently.

### Instructions:
1. **Analyze**: If the query contains multiple entities, comparisons, or multi-step logic, 
   decompose it.
2. **Independence**: Each sub-question must be answerable on its own.
3. **Include Original**: The first item MUST be the original query exactly as provided.
4. **Simplicity**: If the query is already simple, return only the original.
5. **Format**: Output ONLY a valid JSON object.

### OUTPUT FORMAT (JSON ONLY):
{
  "decomposed_questions": ["original query", "sub-query 1", "sub-query 2", ...]
}

### Task:
Query: $question
Output:
""")


CHAT_HISTORY_PROMPT = Template("""
### CHAT HISTORY:
$chat_history

Use this context to understand the conversation flow, but focus on answering the current 
query based on the available information.
""")
