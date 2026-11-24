# Week 2: Automated Pass/Fail Check Pipeline

A lightweight regression testing pipeline for LLM applications. Unlike heavy, subjective accuracy benchmarks, this pipeline acts as an operational smoke test to immediately answer: **did anything break after your latest code or prompt change?**

---

## 🎯 What Was Built

1. **`test_cases.yaml`**: 10 deterministic test cases with fixed input prompts and strict pass conditions.
2. **`run_checks.py`**: Regression check runner that sends test prompts to the LLM, evaluates the response against defined conditions, and outputs a clean pass/fail table.
3. **Week 1 Logging Reuse**: Every check is logged to the shared `llm_calls.jsonl` file, tagged with `run_type: "ci_check"` to distinguish automated runs from manual interactions.
4. **CI-Ready Exit Codes**: Exits with code `0` when all tests pass, and non-zero code (`1`) if any test fails.

---

## 📋 Deterministic Pass Conditions Supported

| Condition Type | Example | What it validates |
|---|---|---|
| `contains` | `["Paris"]` | All specified keywords must appear in response |
| `contains_any` | `["YES", "Yes"]` | At least one of the keywords must appear |
| `does_not_contain` | `["NO"]` | None of the forbidden keywords may appear |
| `max_words` / `min_words` | `max_words: 20` | Strict word count boundary check |
| `max_chars` / `min_chars` | `max_chars: 15` | Exact character length boundary check |
| `is_valid_json` | `true` | Validates JSON parseability (strips markdown code blocks if present) |
| `json_type` | `"dict"` or `"list"` | Verifies whether the parsed JSON is an object or array |
| `required_keys` | `["status", "code"]` | Checks that required dictionary keys exist |

---

## 🚀 How to Run

Navigate into `week 2`:
```powershell
cd "week 2"
```

Run the regression checks:
```powershell
python run_checks.py
```

### Sample Output:
```text
Running 10 regression checks against model 'qwen/qwen3.8-27b'...
Logging runs to: ...\week 1\llm_calls.jsonl (tagged with run_type: 'ci_check')

---------------------------------------------------------------------------
STATUS   ID                 TEST NAME                  LATENCY    DETAILS
---------------------------------------------------------------------------
[✓ PASS] tc01_capital       Capital of France          3464.95 ms Passed
[✓ PASS] tc02_math          Arithmetic Multiplicatio   238.66 ms  Passed
[✓ PASS] tc03_json_dict     Structured JSON Object     284.2 ms   Passed
[✓ PASS] tc04_length_bound  Word Count Length Bound    279.7 ms   Passed
[✓ PASS] tc05_boolean_choice Binary Choice Constraint   266.86 ms  Passed
[✓ PASS] tc06_code_syntax   Code Syntax Generation     267.0 ms   Passed
[✓ PASS] tc07_json_list     Structured JSON Array      251.38 ms  Passed
[✓ PASS] tc08_sentiment     Sentiment Classification   302.34 ms  Passed
[✓ PASS] tc09_trivia        Solar System Trivia        360.62 ms  Passed
[✓ PASS] tc10_chemical_formula Chemical Formula           966.21 ms  Passed
---------------------------------------------------------------------------

Summary: 10/10 passed (100.0%)

[+] All regression checks passed successfully.
```

---

## 📊 Viewing Logs (Distinguishing `ci_check` vs `manual`)

View the updated log analytics from Week 1:
```powershell
python "..\week 1\app.py" stats
```

Output:
```text
--- Log Analysis (llm_calls.jsonl) ---
Total calls:        13
Total tokens used:  1,918
Average latency:    1156.95 ms
Successful calls:   13
Error count:        0

Run types:
  - manual: 3 calls
  - ci_check: 10 calls
```
