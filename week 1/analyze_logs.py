import sys
import json
import os
import argparse


def parse_log_file(file_path):
    """Read jsonl lines and return list of dicts."""
    if not os.path.exists(file_path):
        return []

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def calculate_metrics(records):
    """Aggregate metrics across log records."""
    total_calls = len(records)
    if total_calls == 0:
        return {
            "total_calls": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "average_latency_ms": 0.0,
            "error_count": 0,
            "success_count": 0,
            "distinct_trace_ids": 0,
            "trace_id_counts": {},
            "model_breakdown": {},
        }

    prompt_tokens = 0
    completion_tokens = 0
    total_latency = 0.0
    errors = 0
    trace_counts = {}
    model_stats = {}

    for r in records:
        tid = r.get("trace_id", "unknown")
        trace_counts[tid] = trace_counts.get(tid, 0) + 1

        p = r.get("prompt_tokens") or 0
        c = r.get("completion_tokens") or 0
        prompt_tokens += p
        completion_tokens += c

        lat = r.get("latency_ms") or 0.0
        total_latency += float(lat)

        if not r.get("success", False) or r.get("error"):
            errors += 1

        m = r.get("model", "unknown")
        if m not in model_stats:
            model_stats[m] = {"calls": 0, "tokens": 0, "errors": 0}
        model_stats[m]["calls"] += 1
        model_stats[m]["tokens"] += (p + c)
        if not r.get("success", False):
            model_stats[m]["errors"] += 1

    total_tokens = prompt_tokens + completion_tokens
    avg_latency = round(total_latency / total_calls, 2)

    return {
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "average_latency_ms": avg_latency,
        "error_count": errors,
        "success_count": total_calls - errors,
        "distinct_trace_ids": len(trace_counts),
        "trace_id_counts": trace_counts,
        "model_breakdown": model_stats,
    }


def print_summary(metrics, file_path):
    print(f"\n--- Log Analysis ({file_path}) ---")
    if metrics["total_calls"] == 0:
        print("No calls found in log file.\n")
        return

    print(f"Total calls:        {metrics['total_calls']}")
    print(f"Total tokens used:  {metrics['total_tokens']:,} (Prompt: {metrics['prompt_tokens']:,}, Completion: {metrics['completion_tokens']:,})")
    print(f"Average latency:    {metrics['average_latency_ms']} ms")
    print(f"Successful calls:   {metrics['success_count']}")
    print(f"Error count:        {metrics['error_count']}")
    print(f"Distinct trace IDs: {metrics['distinct_trace_ids']}")

    print("\nModels:")
    for model, info in metrics["model_breakdown"].items():
        print(f"  - {model}: {info['calls']} calls, {info['tokens']} tokens, {info['errors']} errors")

    multi_traces = {t: c for t, c in metrics["trace_id_counts"].items() if c > 1}
    if multi_traces:
        print(f"\nMulti-step traces ({len(multi_traces)}):")
        for t, count in multi_traces.items():
            print(f"  - {t}: {count} calls linked")
    print()


def analyze(file_path="llm_calls.jsonl"):
    records = parse_log_file(file_path)
    metrics = calculate_metrics(records)
    print_summary(metrics, file_path)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze LLM JSONL logs")
    parser.add_argument("--file", "-f", default="llm_calls.jsonl", help="Log file path")
    parser.add_argument("--json", action="store_true", help="Print json metrics")
    args = parser.parse_args()

    records = parse_log_file(args.file)
    metrics = calculate_metrics(records)

    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print_summary(metrics, args.file)
