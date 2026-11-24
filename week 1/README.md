# Structured Logging for LLM Calls

A simple, practical logging wrapper around Groq API calls that writes structured JSON Lines (`.jsonl`) for tracking token usage, latency, errors, and multi-step call traces.

## Features

- **JSON Lines logging**: Appends one JSON line per LLM call to `llm_calls.jsonl`.
- **Latency tracking**: Uses `time.perf_counter()` to record accurate call duration in milliseconds.
- **Resilient error handling**: Catches exceptions and logs them with `success: false` instead of crashing.
- **Trace correlation**: Stamps sequential related calls (e.g. summary -> critique) with the same `trace_id`.
- **Log analyzer**: Reads back logs and reports total calls, token usage, error counts, and average latency.

## Log Schema

Each line in `llm_calls.jsonl` contains:
- `timestamp`: UTC ISO 8601 string
- `trace_id`: UUID/short string correlating calls
- `model`: e.g. `qwen/qwen3.8-27b`
- `prompt`: Full prompt sent to the LLM
- `response`: Full response text (or `null` if errored)
- `prompt_tokens`: Input tokens
- `completion_tokens`: Output tokens
- `total_tokens`: Total tokens consumed
- `latency_ms`: Duration in milliseconds
- `success`: `true` or `false`
- `error`: Error message string or `null`

## Setup

Get a free API key at [console.groq.com/keys](https://console.groq.com/keys) (no credit card required).

Set your key:
```powershell
$env:GROQ_API_KEY="gsk_your_key_here"
```
Or create a `.env` file:
```
GROQ_API_KEY=gsk_your_key_here
```

## Quick Commands

1. **Single prompt:**
   ```powershell
   python app.py ask "Why is the sky blue?"
   ```

2. **2-step chain (summary -> critique with shared trace_id):**
   ```powershell
   python app.py chain "Large language models predict tokens..."
   ```

3. **Check metrics and summary:**
   ```powershell
   python app.py stats
   ```

4. **Simulate API error:**
   ```powershell
   python app.py simulate-error
   ```
