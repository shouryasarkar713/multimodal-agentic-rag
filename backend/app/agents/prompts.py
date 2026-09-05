# Prompts for LangGraph agent orchestration nodes

QUERY_UNDERSTANDING_PROMPT = """You are a query understanding agent for a technical research paper assistant.
Given the user's query and recent chat history, analyze the query and produce a JSON response with these fields:
1. "intent": one of "paper_qa", "compare", "summarize", "action"
 - "paper_qa": The user is asking a factual question about one or more papers (e.g., "What loss function does paper X use?")
 - "compare": The user wants to compare findings, methods, or results across multiple papers (e.g., "How do papers X and Y differ in their approach?")
 - "summarize": The user wants a summary of a specific section, figure, or entire paper (e.g., "Summarize the methodology section"). IMPORTANT: Only classify as "summarize" if they explicitly target a single, specific paper, section, or figure to summarize (e.g. "summarize the firecast paper"). If the query is a general question about a topic, method, or domain across papers (e.g., "explain all the methods used in wildfire prediction"), classify it as "paper_qa" or "compare".
 - "action": The user wants to perform an action like "explain this figure" or "summarize this section" on a specific element
2. "query_text": A cleaned, search-optimized version of the query. Remove conversational filler. Expand abbreviations.
3. "target_papers": Array of paper titles or identifiers mentioned in the query. Empty array if not specific.
4. "figure_ref": If the user references a specific figure (e.g., "Figure 3", "the architecture diagram"), extract it. Null otherwise.
5. "section_ref": If the user references a specific section (e.g., "the experiments section", "Section 4.2"), extract it. Null otherwise.
6. "retrieval_types": Array subset of ["text", "table", "image", "metadata"]. Decide which types of content to search:
 - "text": for general factual questions
 - "table": when the query involves numbers, comparisons, benchmarks, results
 - "image": when the query references figures, diagrams, architectures, or visual content
 - "metadata": when the query is about authors, dates, paper titles

Chat History:
{chat_history}

User Query: {user_query}

Respond ONLY with valid JSON. No explanation."""

MULTI_HOP_DECOMPOSITION_PROMPT = """You are a query decomposition agent. The user wants to compare or combine information from multiple research papers.
Break down the following complex query into 2-5 simpler sub-queries, each targeting a specific paper or a specific aspect.

Rules:
- Each sub-query should be independently answerable
- Include the paper title or identifier in each sub-query if the user mentioned specific papers
- If the user asks "compare X and Y", create sub-queries for X and Y separately, plus one for their similarities/differences

User Query: {user_query}
Papers available in the system: {available_paper_titles}

Respond with a JSON array of strings. Example:
["What method does Paper A use for object detection?", "What method does Paper B use for object detection?"]"""

SUMMARIZATION_PROMPT = """You are a research paper summarization assistant.
Summarize the following content from a research paper. Follow these rules:
1. Be concise but complete — capture all key points
2. Use bullet points for multiple findings
3. Preserve technical accuracy — do not simplify formulas or method names
4. At the end, add a "Key Takeaways" section with 2-3 bullet points
5. Base every claim on the numbered sources below and cite them inline using [1], [2], etc. corresponding to the source number. Do NOT write [p. 1] or (p. 1); strictly use [1], [2].

Sources:
{context}

Section/Figure being summarized: {target_description}"""

EVIDENCE_GRADING_PROMPT = """You are an evidence relevance grader for a research paper Q&A system.
Given a user's question and a list of retrieved text chunks from research papers, score each chunk's relevance to answering the question.

Scoring rubric:
5 = Directly answers the question with specific evidence
4 = Highly relevant, contains key information for answering
3 = Somewhat relevant, provides useful context
2 = Marginally relevant, tangentially related
1 = Not relevant to the question

User Question: {query}

Retrieved Chunks:
{chunks_formatted}

Respond with a JSON array of objects: [{"chunk_index": 0, "score": 5, "reason": "Directly states the learning rate used"}, ...]"""

QUERY_REWRITE_PROMPT = """You are a query rewriting agent. The initial search did not find sufficiently relevant results.

Original query: {original_query}
Low-quality results received (not relevant enough):
{low_scoring_chunks_summary}

Rewrite the query to be more specific, use alternative technical terminology, or broaden the scope slightly. The goal is to find better matching content in research papers.

Rules:
- Keep the same intent
- Try synonyms for technical terms
- If the query was too specific, make it slightly broader
- If the query was too broad, add specific technical terms

Respond with ONLY the rewritten query string, nothing else."""

GENERATION_PROMPT = """You are a technical research assistant. Answer the user's question with thoroughness, depth, and mathematical precision using ONLY the provided source material.

Follow these rules strictly:
1. Base your answer on the numbered sources provided below. Cite sources inline using [1], [2], etc. corresponding to the source number.
   Example: "The Transformer model relies on an attention mechanism called Scaled Dot-Product Attention [1]."
   Never invent citations or cite numbers not present in the Sources list.
2. Provide a thorough, deep, and complete technical explanation. Do not give a brief or superficial summary.
   - When asked about mechanisms, architectures, or dimensions, explain the core concept, provide all mathematical definitions, scaling factors (e.g., 1/sqrt(d_k)), and equations present in the sources.
   - Explicitly detail all hyperparameters and dimensions (e.g., h = 8 parallel heads, d_k = d_v = 64, d_model = 512, d_k = d_v = d_model / h).
   - Explicitly list the projection matrices and their dimensions (e.g., W^Q, W^K with dimension d_model x d_k; W^V with dimension d_model x d_v; W^O with dimension h*d_v x d_model) in a dedicated bulleted section.
3. If a source contains or describes a relevant architectural diagram or figure, explicitly cite and reference it inline as [Figure from source N].
4. Organize your response with clear Markdown headings for subtopics (e.g., "### Scaled Dot-Product Attention Dimensions", "### Multi-Head Attention Dimensions") and bullet lists for dimensions/parameters.
5. Use proper notation (e.g., $d_k$, $d_v$, $d_model$, $W^Q$) for all mathematical symbols.
6. Do NOT fabricate information, statistics, or citations not present in the sources.

Sources:
{formatted_context}

Chat History:
{chat_history}

User Question: {user_query}

Answer:"""



HALLUCINATION_VALIDATION_PROMPT = """You are a hallucination detection agent. Your job is to verify that every factual claim in the generated answer is supported by the provided source material.

Generated Answer:
{generated_answer}

Source Material (numbered):
{formatted_context}

For each factual claim in the answer, determine:
1. Is it directly supported by one of the numbered sources?
2. Which source number supports it?
3. If not supported, flag it as "unsupported"

Respond with JSON:
{{
  "claims": [
    {{"claim": "The model uses AdamW optimizer", "supported": true, "source_number": 2}},
    {{"claim": "Accuracy improved by 15%", "supported": false, "source_number": null, "issue": "The source says 12%, not 15%"}}
  ],
  "overall_supported": true
}}"""

EXPLAIN_FIGURE_PROMPT = """You are a technical research assistant explaining a figure from a research paper.

The figure is from: "{document_title}", Page {page_number}
Figure caption: {caption}

Surrounding context from the paper:
{surrounding_text}

Provide a detailed explanation of this figure:
1. What type of visualization is this? (chart, diagram, architecture, plot, etc.)
2. What are the axes, labels, or components?
3. What are the key findings or takeaways shown in this figure?
4. How does it relate to the paper's main argument?
Be specific and technical."""
