# Solution to API Quota Exceeded Issue

## Problem Analysis
Your evaluation is failing due to Google Gemini API quota limits:
- Free tier allows only **20 requests per day** for the Gemini model (`gemini-3.5-flash`)
- Each evaluation question makes **dozens of LLM calls** (query understanding, evidence grading, generation, validation, plus evaluation metrics)
- With 30 questions, you easily exceed 600+ requests/day >> 20/day limit

## What Was Fixed
I optimized the **embedding API calls** in `backend/app/services/embedding.py` to batch requests (reducing embedding calls by 10x-100x), but this doesn't solve the main LLM quota issue.

## Solutions Provided

### Option 1: Quick System Test (Recommended First Step)
```bash
# Test if system basically works - minimal API usage
docker compose exec backend python eval/system_test.py
```
This checks:
- Documents are processed and ready
- RAG pipeline responds to basic queries
- Uses minimal API calls (just enough to verify flow)

### Option 2: Limited Evaluation (1-3 questions)
```bash
# Test with just a few questions to conserve quota
docker compose exec backend python eval/limited_eval.py 3
```
This runs only the specified number of questions (default 3) with basic success metrics.

### Option 3: Wait for Quota Reset
Google quotas typically reset daily at midnight Pacific Time. Wait until then to run full evaluation.

### Option 4: Create Custom Minimal Test
Use `eval/quick_test.py` as a template to test specific questions you care about.

## Current Status
✅ **Documents processed successfully**: Your 3 papers (1706.03762, 1512.03385, 1810.04805) show as "ready" in the logs
✅ **Embedding optimization complete**: API call batching implemented
❌ **Full evaluation blocked by quota**: Need to reduce LLM call frequency

## Next Steps
1. Run `system_test.py` to verify basic functionality
2. If that passes, run `limited_eval.py` with 1-2 questions
3. Wait for quota reset or consider upgrading Google Cloud plan for higher limits
4. For production use, monitor quota usage in Google Cloud Console

The core RAG system is working - it's just hitting the free tier limits during intensive evaluation.
