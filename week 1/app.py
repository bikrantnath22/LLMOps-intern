import os
import sys
import argparse
from llm_logger import call_llm, run_summary_and_critique, DEFAULT_MODEL, DEFAULT_LOG_FILE
from analyze_logs import analyze


def check_api_key():
    if not os.getenv("GROQ_API_KEY"):
        print("\nNote: GROQ_API_KEY is not set.")
        print("Set it in terminal:  $env:GROQ_API_KEY='gsk_...' (PowerShell) or export GROQ_API_KEY='gsk_...'")
        print("Or add it to a .env file.\n")


def main():
    parser = argparse.ArgumentParser(description="Groq LLM CLI with structured JSONL logging")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE, help="Log file path")
    subparsers = parser.add_subparsers(dest="cmd")

    # Single call
    p_ask = subparsers.add_parser("ask", help="Send prompt to Groq")
    p_ask.add_argument("prompt", help="Prompt text")
    p_ask.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    p_ask.add_argument("--trace-id", default=None, help="Custom trace id")

    # 2-step chain (summary -> critique)
    p_chain = subparsers.add_parser("chain", help="Run 2 sequential calls with shared trace_id")
    p_chain.add_argument("text", help="Text to summarize and critique")
    p_chain.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    p_chain.add_argument("--trace-id", default=None, help="Custom trace id")

    # Stats
    subparsers.add_parser("stats", help="Read log file and print summary metrics")

    # Error simulation
    subparsers.add_parser("simulate-error", help="Test error logging without crashing")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(0)

    if args.cmd == "ask":
        check_api_key()
        print(f"Calling {args.model}...")
        res = call_llm(
            prompt=args.prompt,
            model=args.model,
            trace_id=args.trace_id,
            log_file=args.log_file,
        )
        if res["success"]:
            print(f"\nResponse (trace_id={res['trace_id']}):")
            print(res["response"])
            print(f"\n[tokens: {res['prompt_tokens']} in + {res['completion_tokens']} out | latency: {res['latency_ms']} ms]")
        else:
            print(f"\nCall failed: {res['error']}")
        print(f"Logged to {args.log_file}")

    elif args.cmd == "chain":
        check_api_key()
        print("Running summary -> critique chain...")
        res = run_summary_and_critique(
            text=args.text,
            model=args.model,
            trace_id=args.trace_id,
            log_file=args.log_file,
        )
        print(f"\nTrace ID: {res['trace_id']}")
        if res["summary"]:
            print(f"\nStep 1 (Summary):\n{res['summary']}")
        if res["critique"]:
            print(f"\nStep 2 (Critique):\n{res['critique']}")
        print(f"\nBoth calls logged to {args.log_file} with matching trace_id.")

    elif args.cmd == "stats":
        analyze(args.log_file)

    elif args.cmd == "simulate-error":
        print("Simulating error by calling non-existent model...")
        res = call_llm(
            prompt="Test failure",
            model="broken-model-name-xyz",
            log_file=args.log_file,
        )
        print(f"Success: {res['success']}")
        print(f"Error captured: {res['error']}")
        print(f"Latency measured: {res['latency_ms']} ms")
        print(f"Error logged cleanly to {args.log_file} without crashing.")


if __name__ == "__main__":
    main()
