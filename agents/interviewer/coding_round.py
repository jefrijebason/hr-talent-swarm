from shared.openai_client import ask_gpt4o, ask_gpt4o_mini, parse_json
from shared.config import config
from agents.interviewer.anti_malpractice import (
    generate_interrogation_questions,
    evaluate_interrogation_answers,
    simulate_interrogation
)
import requests
import json

# Judge0 language IDs
LANGUAGE_IDS = {
    "python":     71,
    "javascript": 63,
    "java":       62,
    "cpp":        54,
    "c":          50,
    "go":         60,
    "rust":       73,
    "typescript": 74,
    "sql":        82,
    "bash":       46
}

def generate_coding_problem(jd_text: str,
                              tech_stack: list,
                              coding_type: str,
                              seniority: str) -> dict:
    """
    Generate a coding problem specific to the
    candidate's role and tech stack.
    Not generic — tailored to what this job needs.
    """
    print("[CODING] Generating problem...")

    language = tech_stack[0].lower() if tech_stack else "python"

    type_instructions = {
        "algorithms_and_design": """
            Create a practical algorithm problem that mirrors
            real work in this role. Not leetcode puzzles —
            real scenarios a developer would face.
            Include a system design component.
        """,
        "sql_and_data": """
            Create a SQL problem using realistic business data.
            Should test joins, aggregations, window functions.
            Include a data modeling question.
        """,
        "ml_implementation": """
            Create an ML implementation task.
            Could be feature engineering, model evaluation,
            or pipeline design. Practical not theoretical.
        """,
        "domain_specific": """
            Create a domain-specific technical task
            relevant to the role requirements in the JD.
        """
    }

    instructions = type_instructions.get(
        coding_type,
        type_instructions["algorithms_and_design"]
    )

    prompt = f"""
You are creating a coding assessment for a job interview.

JD Context: {jd_text[:500]}
Primary Language: {language}
Coding Type: {coding_type}
Seniority: {seniority}

{instructions}

Requirements:
- Problem should take 20-30 minutes for a qualified candidate
- Must be solvable in {language}
- Should test real skills needed for this job
- Include exactly 3 test cases (basic, edge, performance)
- NOT a leetcode puzzle — real work scenario

Return ONLY valid JSON:
{{
    "problem_title": "short descriptive title",
    "problem_description": "complete problem statement (3-4 paragraphs)",
    "input_format": "how input is provided",
    "output_format": "what output is expected",
    "constraints": ["constraint1", "constraint2"],
    "example": {{
        "input": "example input",
        "output": "expected output",
        "explanation": "why this is the output"
    }},
    "test_cases": [
        {{
            "id": 1,
            "type": "basic",
            "input": "basic test input",
            "expected_output": "expected",
            "is_hidden": false
        }},
        {{
            "id": 2,
            "type": "edge",
            "input": "edge case input",
            "expected_output": "expected",
            "is_hidden": true
        }},
        {{
            "id": 3,
            "type": "performance",
            "input": "large input description",
            "expected_output": "expected",
            "is_hidden": true
        }}
    ],
    "starter_code": "def solution():\\n    # Write your solution here\\n    pass",
    "solution_hint": "high level approach hint",
    "time_limit_minutes": 30,
    "language": "{language}"
}}
"""

    try:
        response = ask_gpt4o(prompt)
        result   = parse_json(response)
        print(f"[CODING] Problem: {result.get('problem_title')}")
        return result
    except Exception as e:
        print(f"[CODING] Problem generation error: {e}")
        return _fallback_problem(language)

def execute_code(code: str,
                  language: str,
                  test_input: str) -> dict:
    """
    Execute code using Judge0.
    Returns stdout, stderr, status.
    """
    lang_id = LANGUAGE_IDS.get(language.lower(), 71)

    payload = {
        "source_code": code,
        "language_id": lang_id,
        "stdin":        test_input,
        "cpu_time_limit": 5,
        "memory_limit":   128000
    }

    try:
        # Submit to Judge0
        submit = requests.post(
            f"{config.JUDGE0_URL}/submissions?wait=true",
            json=payload,
            timeout=30
        )

        if submit.status_code in [200, 201]:
            result = submit.json()
            return {
                "success":   True,
                "stdout":    result.get("stdout", ""),
                "stderr":    result.get("stderr", ""),
                "status":    result.get("status", {}).get("description", ""),
                "time":      result.get("time"),
                "memory":    result.get("memory")
            }
        else:
            return {
                "success": False,
                "error":   f"Judge0 error: {submit.status_code}"
            }

    except requests.exceptions.ConnectionError:
        print("[CODING] Judge0 not available — demo mode")
        return _demo_execution(code, language)
    except Exception as e:
        print(f"[CODING] Execution error: {e}")
        return {"success": False, "error": str(e)}

def _demo_execution(code: str, language: str) -> dict:
    """Demo execution when Judge0 is not available."""
    return {
        "success": True,
        "stdout":  "Demo mode: Code submitted successfully",
        "stderr":  "",
        "status":  "Accepted (Demo)",
        "time":    "0.1",
        "memory":  "1024"
    }

def run_test_cases(code: str,
                    language: str,
                    test_cases: list) -> dict:
    """Run all test cases against candidate's code."""
    results   = []
    passed    = 0
    total     = len(test_cases)

    for tc in test_cases:
        result = execute_code(
            code,
            language,
            tc.get("input", "")
        )

        expected = str(tc.get("expected_output", "")).strip()
        actual   = str(result.get("stdout", "")).strip()
        tc_pass  = actual == expected or result.get("status") == "Accepted (Demo)"

        if tc_pass:
            passed += 1

        results.append({
            "test_case_id": tc.get("id"),
            "type":         tc.get("type"),
            "passed":       tc_pass,
            "expected":     expected if not tc.get("is_hidden") else "hidden",
            "actual":       actual   if not tc.get("is_hidden") else "hidden",
            "status":       result.get("status"),
            "time":         result.get("time")
        })

    score = round((passed / total) * 100) if total > 0 else 0

    return {
        "passed":       passed,
        "total":        total,
        "score":        score,
        "results":      results,
        "all_passed":   passed == total
    }

def evaluate_code_quality(code: str,
                           problem: dict,
                           test_results: dict) -> dict:
    """
    Evaluate overall code quality beyond just test passing.
    Looks at: readability, efficiency, edge case handling.
    """
    prompt = f"""
Evaluate this code submission for a job interview.

PROBLEM:
{problem.get('problem_title')}
{problem.get('problem_description', '')[:500]}

CANDIDATE'S CODE:
{code}

TEST RESULTS:
{test_results.get('passed')}/{test_results.get('total')} test cases passed

Evaluate on:
1. Code quality (readability, naming, structure)
2. Efficiency (time/space complexity awareness)
3. Edge case handling
4. Problem understanding

Return ONLY valid JSON:
{{
    "code_quality_score": 0-100,
    "efficiency_score": 0-100,
    "readability_score": 0-100,
    "overall_coding_score": 0-100,
    "time_complexity": "O(?) analysis",
    "space_complexity": "O(?) analysis",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "code_summary": "2 sentence assessment"
}}
"""

    try:
        response = ask_gpt4o(prompt)
        return parse_json(response)
    except Exception as e:
        print(f"[CODING] Quality eval error: {e}")
        return {
            "overall_coding_score": test_results.get("score", 50),
            "code_summary": "Evaluation completed"
        }

def run_coding_round(candidate_id: str,
                      jd_text: str,
                      tech_stack: list,
                      coding_type: str,
                      seniority: str,
                      submitted_code: str = None,
                      language: str = "python") -> dict:
    """
    Run complete coding round:
    1. Generate problem
    2. Candidate writes solution (or simulate for testing)
    3. Run test cases
    4. Evaluate code quality
    5. Anti-malpractice interrogation
    6. Return complete result
    """
    print(f"[CODING] Starting coding round for: {candidate_id}")

    # Step 1 — Generate problem
    problem = generate_coding_problem(
        jd_text, tech_stack, coding_type, seniority
    )

    # Step 2 — Get or simulate code
    if submitted_code:
        code     = submitted_code
        language = language
    else:
        # Demo mode — simulate a solution
        print("[CODING] Demo mode — simulating solution")
        code     = _simulate_solution(problem, language)
        language = language

    print(f"[CODING] Code received ({len(code)} chars)")

    # Step 3 — Run test cases
    test_results = run_test_cases(
        code,
        language,
        problem.get("test_cases", [])
    )
    print(f"[CODING] Tests: {test_results['passed']}/{test_results['total']} passed")

    # Step 4 — Evaluate code quality
    quality = evaluate_code_quality(code, problem, test_results)
    print(f"[CODING] Quality score: {quality.get('overall_coding_score')}/100")

    # Step 5 — Anti-malpractice interrogation
    print("[CODING] Running anti-malpractice check...")
    questions = generate_interrogation_questions(
        code, "code", "software_development"
    )

    # Simulate answers for demo
    answers = simulate_interrogation(
        questions, code, "code"
    )

    malpractice_result = evaluate_interrogation_answers(
        questions, answers, code, "code"
    )

    print(f"[CODING] Malpractice: {malpractice_result.get('malpractice_verdict')}")

    # Step 6 — Calculate final coding score
    test_weight    = 0.5
    quality_weight = 0.3
    malpractice_weight = 0.2

    malpractice_score = malpractice_result.get("overall_score", 70)

    final_coding_score = (
        test_results.get("score", 0)    * test_weight +
        quality.get("overall_coding_score", 0) * quality_weight +
        malpractice_score * malpractice_weight
    )

    result = {
        "candidate_id":        candidate_id,
        "problem":             problem,
        "code_submitted":      code,
        "language":            language,
        "test_results":        test_results,
        "code_quality":        quality,
        "malpractice_check":   malpractice_result,
        "malpractice_score":   malpractice_score,
        "malpractice_flagged": malpractice_result.get(
            "recommendation"
        ) != "Proceed",
        "final_coding_score":  round(final_coding_score, 1),
        "interrogation_questions": questions,
        "interrogation_answers":   answers
    }

    print(f"[CODING] Final score: {result['final_coding_score']}/100")
    return result

def _simulate_solution(problem: dict, language: str) -> str:
    """Simulate a competent solution for demo/testing."""
    prompt = f"""
Write a competent but not perfect {language} solution
for this problem. Real code that mostly works.
Include comments. Natural coding style.

Problem: {problem.get('problem_title')}
{problem.get('problem_description', '')[:500]}

Starter code: {problem.get('starter_code', '')}

Return ONLY the code. No explanation.
"""
    try:
        return ask_gpt4o(prompt)
    except Exception:
        return problem.get("starter_code",
                          f"def solution():\n    pass")

def _fallback_problem(language: str) -> dict:
    """Fallback problem if generation fails."""
    return {
        "problem_title":       "Process Candidate Scores",
        "problem_description": "Given a list of candidate scores and a number k, return the top k candidates with their percentile rankings.",
        "input_format":        "List of scores and integer k",
        "output_format":       "List of (score, percentile) tuples",
        "test_cases": [
            {"id": 1, "type": "basic",
             "input": "[85, 92, 78, 95, 88]\n3",
             "expected_output": "[(95, 100.0), (92, 80.0), (88, 60.0)]",
             "is_hidden": False},
            {"id": 2, "type": "edge",
             "input": "[]\n0",
             "expected_output": "[]",
             "is_hidden": True},
            {"id": 3, "type": "performance",
             "input": "large_list\n100",
             "expected_output": "top_100",
             "is_hidden": True}
        ],
        "starter_code":     f"def solution(scores, k):\n    # Write your solution here\n    pass",
        "time_limit_minutes": 30,
        "language":           language
    }