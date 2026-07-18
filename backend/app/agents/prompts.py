import time
import logging
from typing import List

# Query Understanding Prompts
INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a research assistant assistant.
Given a user query and the chat history, classify the user's intent into one of the following categories:
- "paper_qa": General Q&A, searching for facts, concepts, or details within research papers.
- "compare": Comparing findings, methodologies, results, or attributes across multiple papers.
- "summarize": Summarizing specific papers, sections, or overall research corpus.
- "action": Specific technical action requests like explaining a figure/table or summarizing a specific section.

Chat History:
{chat_history}

User Query: "{query}"

Output ONLY the category name as a single word in lowercase (one of: paper_qa, compare, summarize, action). Do not write anything else."""

QUERY_PARSING_PROMPT = """You are a query parser for a research assistant assistant.
Extract structured metadata from the user's query.

For the key "retrieval_types": select any subset of ["text", "table", "image", "metadata"] that are relevant to satisfying the query.
For the key "target_papers": extract any specific paper titles or authors mentioned.
For the key "figure_ref": extract figure references if any (e.g. "Figure 3", "Fig 1").
For the key "section_ref": extract section references if any (e.g. "Section 4.2", "Introduction").

User Query: "{query}"

Respond with JSON ONLY:
{{
  "query_text": "cleaned search query",
  "retrieval_types": ["text", "image"],
  "target_papers": [],
  "figure_ref": null,
  "section_ref": null
}}"""

# Multi-Hop prompts
QUERY_DECOMPOSITION_PROMPT = """You are an expert research analyst.
Decompose a comparative user query into 2 or 3 distinct sub-queries that can be run independently against a database of research papers.
Focus each sub-query on gathering specific factual evidence about one aspect or one paper.

Comparative Query: "{query}"

Respond with JSON ONLY:
{{
  "sub_queries": [
    "Sub-query 1",
    "Sub-query 2"
  ]
}}"""

# Generation prompts
RAG_GENERATION_PROMPT = """You are a highly precise, technical academic research assistant.
Answer the user's query based ONLY on the provided papers context. 

Guidelines:
1. Ground your answer strictly in the facts from the context. Do not extrapolate.
2. Synthesize findings across papers if relevant.
3. Cite your sources using bracketed numbers corresponding to the context items (e.g., [1], [2]).
4. If the context does not contain enough information to answer, state: "The provided research corpus does not contain sufficient information to answer this query."

Context:
{context}

User Query: "{query}"

Respond with a professional, detailed, structured academic answer. Cite sources continuously."""

# Evaluation/Validation Prompts
HALLUCINATION_GRADING_PROMPT = """You are a factual validator for research assistant answers.
Compare the generated answer to the retrieved context chunks and verify if the answer introduces any facts not present in the context.

Retrieved Context:
{context}

Generated Answer:
{generation}

Identify any claims in the answer that are not supported by the context.
Respond with JSON:
{{
  "hallucination": true/false,
  "unsupported_claims": [
    "List of unsupported claims if any"
  ]
}}"""

# Evidence grading prompt
EVIDENCE_GRADING_PROMPT = """You are an academic peer reviewer grading the relevance of retrieved research paper chunks for answering a specific query.
Rate each chunk on a scale of 1.0 to 5.0:
- 5.0: Extremely relevant, contains the exact answer or critical evidence.
- 4.0: Highly relevant, contains context directly related to the answer.
- 3.0: Somewhat relevant, general background info on the topic.
- 1.0 - 2.0: Irrelevant, unrelated paper section or noise.

User Query: "{query}"

Retrieved Chunks:
{chunks_formatted}

Grade each chunk by its index. If a chunk mentions an image or figure description that is relevant to the query, grade it high.
If a chunk is a figure caption and the user is asking to explain that figure, score it 5.0.

Respond with JSON ONLY:
[
  {{"chunk_index": 0, "score": 5.0, "reasoning": "contains the main equation requested"}},
  {{"chunk_index": 1, "score": 2.0, "reasoning": "background information unrelated to the main query"}}
]"""

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
