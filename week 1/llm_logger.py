import os
import json
import time
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

from pathlib import Path

# load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
_env_log = os.getenv("LLM_LOG_FILE", "llm_calls.jsonl")
DEFAULT_LOG_FILE = str(BASE_DIR / _env_log) if not os.path.isabs(_env_log) else _env_log


def log_entry(log_path, entry):
    """Append one structured log record to the jsonl file."""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_client(api_key=None):
    from groq import Groq
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not set. Please set it in your environment or in a .env file.")
    return Groq(api_key=key)


def call_llm(prompt, model=DEFAULT_MODEL, trace_id=None, log_file=DEFAULT_LOG_FILE, client=None, run_type="manual", **kwargs):
    """
    Wraps Groq LLM call with timing, error handling, and JSONL logging.
    Returns result dict with success flag, response, and metadata.
    """
    trace_id = trace_id or str(uuid.uuid4())[:8]
    t0 = time.perf_counter()

    try:
        if client is None:
            client = get_client()

        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        content = res.choices[0].message.content if res.choices else ""
        prompt_tokens = res.usage.prompt_tokens if res.usage else 0
        completion_tokens = res.usage.completion_tokens if res.usage else 0

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "run_type": run_type,
            "model": model,
            "prompt": prompt,
            "response": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "success": True,
            "error": None,
        }
        log_entry(log_file, entry)

        return {
            "success": True,
            "trace_id": trace_id,
            "run_type": run_type,
            "response": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "error": None,
            "log_entry": entry,
        }

    except Exception as e:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        err_msg = f"{type(e).__name__}: {str(e)}"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "run_type": run_type,
            "model": model,
            "prompt": prompt,
            "response": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_ms": latency_ms,
            "success": False,
            "error": err_msg,
        }
        log_entry(log_file, entry)

        return {
            "success": False,
            "trace_id": trace_id,
            "run_type": run_type,
            "response": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": latency_ms,
            "error": err_msg,
            "log_entry": entry,
        }


def run_summary_and_critique(text, model=DEFAULT_MODEL, trace_id=None, log_file=DEFAULT_LOG_FILE, client=None):
    """
    Makes 2 sequential calls sharing the exact same trace_id:
    Step 1: Summarize input text
    Step 2: Critique the summary
    """
    trace_id = trace_id or f"trace_{uuid.uuid4().hex[:8]}"

    # Step 1: Summary
    summary_prompt = f"Summarize the following in 2-3 concise sentences:\n\n{text}"
    sum_res = call_llm(
        prompt=summary_prompt,
        model=model,
        trace_id=trace_id,
        log_file=log_file,
        client=client,
    )

    if not sum_res["success"]:
        return {
            "trace_id": trace_id,
            "status": "failed_at_step_1",
            "summary": None,
            "critique": None,
            "summary_result": sum_res,
            "critique_result": None,
        }

    summary_text = sum_res["response"]

    # Step 2: Critique the generated summary
    critique_prompt = f"Critique this summary for clarity and completeness:\n\n{summary_text}"
    crit_res = call_llm(
        prompt=critique_prompt,
        model=model,
        trace_id=trace_id,
        log_file=log_file,
        client=client,
    )

    return {
        "trace_id": trace_id,
        "status": "completed" if crit_res["success"] else "failed_at_step_2",
        "summary": summary_text,
        "critique": crit_res["response"],
        "summary_result": sum_res,
        "critique_result": crit_res,
    }


# Backwards-compatible class helper for test suite / direct callers
class LLMLogger:
    def __init__(self, log_path=DEFAULT_LOG_FILE):
        self.log_path = log_path

    def log_call(self, trace_id, model, prompt, response, prompt_tokens, completion_tokens, latency_ms, success, error=None, extra=None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "model": model,
            "prompt": prompt,
            "response": response,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "error": error,
        }
        if extra:
            entry["extra"] = extra
        log_entry(self.log_path, entry)
        return entry
