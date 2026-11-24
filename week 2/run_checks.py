import os
import sys
import json
import yaml
import argparse
from pathlib import Path

# Add week 1 to sys.path so we can reuse the Week 1 logging wrapper
current_dir = Path(__file__).resolve().parent
week1_dir = current_dir.parent / "week 1"
if str(week1_dir) not in sys.path:
    sys.path.insert(0, str(week1_dir))

from llm_logger import call_llm, DEFAULT_MODEL

# Default log file targets Week 1's llm_calls.jsonl
DEFAULT_LOG_FILE = str(week1_dir / "llm_calls.jsonl")
DEFAULT_TEST_CASES = str(current_dir / "test_cases.yaml")


def clean_json_text(text):
    """Strip markdown code fences if model wrapped json in ```json ... ```."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def evaluate_condition(response_text, condition):
    """
    Checks LLM response against deterministic pass conditions.
    Returns (passed: bool, reason: str)
    """
    if not response_text:
        return False, "Empty or null response"

    raw_text = response_text.strip()
    lower_text = raw_text.lower()

    # 1. Check all required keywords
    if "contains" in condition:
        for kw in condition["contains"]:
            if kw.lower() not in lower_text:
                return False, f"Missing '{kw}'"

    # 2. Check at least one of keywords
    if "contains_any" in condition:
        if not any(kw.lower() in lower_text for kw in condition["contains_any"]):
            return False, f"Missing any of {condition['contains_any']}"

    # 3. Check forbidden keywords
    if "does_not_contain" in condition:
        for kw in condition["does_not_contain"]:
            if kw.lower() in lower_text:
                return False, f"Contains forbidden '{kw}'"

    # 4. Word length limits
    words = raw_text.split()
    if "max_words" in condition and len(words) > condition["max_words"]:
        return False, f"Too long ({len(words)} words > {condition['max_words']})"
    if "min_words" in condition and len(words) < condition["min_words"]:
        return False, f"Too short ({len(words)} words < {condition['min_words']})"

    # 5. Character length limits
    if "max_chars" in condition and len(raw_text) > condition["max_chars"]:
        return False, f"Too long ({len(raw_text)} chars > {condition['max_chars']})"
    if "min_chars" in condition and len(raw_text) < condition["min_chars"]:
        return False, f"Too short ({len(raw_text)} chars < {condition['min_chars']})"

    # 6. JSON validation
    if condition.get("is_valid_json"):
        cleaned = clean_json_text(raw_text)
        try:
            parsed = json.loads(cleaned)
        except Exception as e:
            return False, f"Invalid JSON ({e})"

        # Check json type if specified
        if "json_type" in condition:
            if condition["json_type"] == "dict" and not isinstance(parsed, dict):
                return False, "Expected JSON object/dict"
            if condition["json_type"] == "list" and not isinstance(parsed, list):
                return False, "Expected JSON array/list"

        # Check required keys for dict
        if "required_keys" in condition and isinstance(parsed, dict):
            for k in condition["required_keys"]:
                if k not in parsed:
                    return False, f"JSON missing key '{k}'"

    return True, "Passed"


def load_test_cases(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Test cases file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(f)
        return json.load(f)


def run_checks(test_cases_file=DEFAULT_TEST_CASES, log_file=DEFAULT_LOG_FILE, model=DEFAULT_MODEL):
    cases = load_test_cases(test_cases_file)
    total = len(cases)
    passed_count = 0
    results = []

    print(f"\nRunning {total} regression checks against model '{model}'...")
    print(f"Logging runs to: {log_file} (tagged with run_type: 'ci_check')\n")

    for idx, tc in enumerate(cases, start=1):
        tc_id = tc.get("id", f"tc_{idx}")
        name = tc.get("name", tc_id)
        prompt = tc["prompt"]
        condition = tc.get("pass_condition", {})

        # Call LLM using Week 1 wrapper, tagging with run_type: "ci_check"
        call_res = call_llm(
            prompt=prompt,
            model=model,
            log_file=log_file,
            run_type="ci_check",
            temperature=0.0,
        )

        if not call_res["success"]:
            passed = False
            reason = f"API Error: {call_res['error']}"
        else:
            passed, reason = evaluate_condition(call_res["response"], condition)

        if passed:
            passed_count += 1

        results.append({
            "id": tc_id,
            "name": name,
            "passed": passed,
            "reason": reason,
            "latency_ms": call_res.get("latency_ms", 0.0),
            "response": call_res.get("response", ""),
        })

    # Print Pass / Fail Results Table
    print("-" * 75)
    print(f"{'STATUS':<8} {'ID':<18} {'TEST NAME':<26} {'LATENCY':<10} {'DETAILS'}")
    print("-" * 75)

    for r in results:
        status_symbol = "[✓ PASS]" if r["passed"] else "[✗ FAIL]"
        latency_str = f"{r['latency_ms']} ms"
        print(f"{status_symbol:<8} {r['id']:<18} {r['name'][:24]:<26} {latency_str:<10} {r['reason']}")

    print("-" * 75)

    # Summary Line
    failed_count = total - passed_count
    pct = round((passed_count / total) * 100, 1) if total > 0 else 0
    print(f"\nSummary: {passed_count}/{total} passed ({pct}%)\n")

    # Non-zero exit code if any test fails (for CI pipelines)
    if failed_count > 0:
        print(f"[!] {failed_count} check(s) failed.")
        return 1
    else:
        print("[+] All regression checks passed successfully.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Automated Pass/Fail Regression Check Runner")
    parser.add_argument("--tests", "-t", default=DEFAULT_TEST_CASES, help="Path to test_cases.yaml or json")
    parser.add_argument("--log-file", "-l", default=DEFAULT_LOG_FILE, help="Path to shared JSONL log file")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help="Model name")
    args = parser.parse_args()

    exit_code = run_checks(
        test_cases_file=args.tests,
        log_file=args.log_file,
        model=args.model,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
