"""
AI Code Quality Evaluator - Core Engine

This module provides comprehensive code quality evaluation for AI-generated Python code.

External Dependencies:
- Groq API (https://groq.com) - LLM code generation
- Radon (MIT) - Code complexity metrics (https://radon.readthedocs.io)
- Bandit (Apache 2.0) - Security analysis (https://bandit.readthedocs.io)

Evaluation Methodologies:
- Cyclomatic Complexity: McCabe (1976)
- Maintainability Index: Oman & Hagemeister (1992)
- Halstead Metrics: Halstead (1977)
- SOLID Principles: Martin (2000)

See CREDITS.md for full attribution.
"""

import os
import re
import tempfile
from groq import Groq
import ast
import radon.complexity as complexity
import radon.metrics as metrics
from radon.raw import analyze
import subprocess
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None



def generate_code(prompt: str) -> str:
    """
    Generate Python code from natural language prompt using Groq LLM API.
    
    Uses llama-3.3-70b-versatile model via Groq API, falls back to llama3-8b if rate limited.
    See: https://groq.com
    """
    if not client:
        print("No API key found. Using fallback generator.\n")
        return get_fallback_code()

    # Try with the larger model first, then fall back to smaller model if rate limited
    models_to_try = [
        "llama-3.3-70b-versatile",  # Better quality, but higher token usage
        "llama3-8b-8192",            # Faster, more token-efficient
    ]
    
    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": """You are an expert Python developer who writes production-ready code with:
- Clean, modular architecture following SOLID principles
- Comprehensive error handling with try-except blocks and meaningful exceptions
- Detailed docstrings for all functions and classes
- Unit tests with assertions
- Type hints where appropriate
- Logging for debugging
- Input validation
- Security best practices (no hardcoded credentials, SQL injection prevention, etc.)
- Include all necessary comments for clarity.

Return ONLY the Python code without markdown formatting or explanations."""},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
            )
            code = response.choices[0].message.content
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            print(f"Code generated successfully using {model_name}.\n")
            return code
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() and model_name != models_to_try[-1]:
                print(f"Rate limit hit on {model_name}, trying next model...\n")
                continue
            else:
                print(f"Using fallback (mock) generator because of error: {e}\n")
                return get_fallback_code()
    
    # If all models failed
    print("All models failed. Using fallback generator.\n")
    return get_fallback_code()



def get_fallback_code():
    """Fallback code when API is unavailable"""
    return """def hello_world():
    \"\"\"Simple fallback function\"\"\"
    print('Hello, World!')

if __name__ == '__main__':
    hello_world()
"""



def analyze_security(code: str) -> dict:
    """
    Analyze code for security vulnerabilities using Bandit.
    
    Bandit: Apache 2.0 License
    See: https://bandit.readthedocs.io
    """
    results = {"security_issues": 0, "high_severity": 0, "issues": []}

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        result = subprocess.run(
            ['bandit', '-r', temp_file, '-f', 'json'],
            capture_output=True,
            text=True,
            timeout=10
        )

        os.unlink(temp_file)

        if result.stdout:
            bandit_data = json.loads(result.stdout)
            results["security_issues"] = len(bandit_data.get("results", []))
            results["high_severity"] = sum(
                1 for issue in bandit_data.get("results", [])
                if issue.get("issue_severity") == "HIGH"
            )
            results["issues"] = [
                {
                    "severity": issue.get("issue_severity"),
                    "confidence": issue.get("issue_confidence"),
                    "issue": issue.get("issue_text"),
                    "line": issue.get("line_number")
                }
                for issue in bandit_data.get("results", [])[:5]
            ]
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        results["error"] = f"Security scan unavailable: {str(e)}"

    return results





def analyze_error_handling(code: str) -> dict:
    """
    Analyze error handling patterns in Python code.
    
    Uses Python AST module for code structure analysis.
    See: https://docs.python.org/3/library/ast.html
    """
    results = {
        "has_try_except": False,
        "has_custom_exceptions": False,
        "has_logging": False,
        "exception_count": 0,
        "bare_except_count": 0,
        "has_validation": False
    }

    try:
        tree = ast.parse(code)

        try_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
        results["has_try_except"] = len(try_nodes) > 0
        results["exception_count"] = len(try_nodes)

        for try_node in try_nodes:
            for handler in try_node.handlers:
                if handler.type is None:
                    results["bare_except_count"] += 1

        class_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        for class_node in class_nodes:
            if any(isinstance(base, ast.Name) and 'Exception' in base.id 
                   for base in class_node.bases if isinstance(base, ast.Name)):
                results["has_custom_exceptions"] = True

        if re.search(r'import logging|from logging', code):
            results["has_logging"] = True

        if re.search(r'isinstance\(|ValueError|TypeError|assert.*>|assert.*<', code):
            results["has_validation"] = True

    except SyntaxError:
        pass

    return results





def analyze_solid_principles(code: str) -> dict:
    """
    Analyze adherence to SOLID principles, particularly Single Responsibility.
    
    SOLID Principles: Robert C. Martin (2000)
    See: Clean Architecture and SOLID design principles
    """
    results = {
        "srp_score": 0,
        "class_count": 0,
        "avg_methods_per_class": 0,
        "god_classes": [],
        "long_methods": []
    }

    try:
        tree = ast.parse(code)

        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        results["class_count"] = len(classes)

        method_counts = []
        for class_node in classes:
            methods = [n for n in class_node.body if isinstance(n, ast.FunctionDef)]
            method_count = len(methods)
            method_counts.append(method_count)

            if method_count > 10:
                results["god_classes"].append(class_node.name)

            for method in methods:
                lines = method.end_lineno - method.lineno if hasattr(method, 'end_lineno') else 0
                if lines > 50:
                    results["long_methods"].append(f"{class_node.name}.{method.name}")

        if method_counts:
            results["avg_methods_per_class"] = sum(method_counts) / len(method_counts)
            results["srp_score"] = max(0, 100 - (results["avg_methods_per_class"] * 5))
        else:
            results["srp_score"] = 100

    except SyntaxError:
        pass

    return results





def analyze_test_coverage(code: str) -> dict:
    """
    Analyze test coverage and testing patterns.
    
    Detects unittest, pytest, and nose frameworks.
    """
    results = {
        "has_tests": False,
        "test_functions": 0,
        "assertion_count": 0,
        "test_frameworks": []
    }

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(fw in alias.name for fw in ['unittest', 'pytest', 'nose']):
                        results["test_frameworks"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(fw in node.module for fw in ['unittest', 'pytest', 'nose']):
                    results["test_frameworks"].append(node.module)

        funcs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        test_funcs = [f for f in funcs if f.name.startswith('test_')]
        results["test_functions"] = len(test_funcs)
        results["has_tests"] = len(test_funcs) > 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                results["assertion_count"] += 1
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr.startswith('assert'):
                        results["assertion_count"] += 1

    except SyntaxError:
        pass

    return results





def calculate_maintainability_index(code: str) -> dict:
    """
    Calculate software maintainability metrics.
    
    Uses Radon library (MIT License) for:
    - Maintainability Index: Oman & Hagemeister (1992)
    - Halstead Metrics: Maurice Halstead (1977)
    - Cyclomatic Complexity: Thomas McCabe (1976)
    
    See: https://radon.readthedocs.io
    """

    results = {
        "maintainability_index": 0,
        "halstead_volume": 0,
        "lloc": 0,
        "comments": 0,
        "rating": ""
    }

    try:
        # Get raw metrics
        raw_analysis = analyze(code)
        results["lloc"] = raw_analysis.lloc
        results["comments"] = raw_analysis.comments
        
        # Calculate Maintainability Index
        # mi_visit with multi=True returns a single float (average across all functions)
        mi_score = metrics.mi_visit(code, multi=True)
        
        if mi_score is not None:
            results["maintainability_index"] = round(mi_score, 2)
            
            # Try to get Halstead volume
            try:
                h_result = metrics.h_visit(code)
                if h_result:
                    total_volume = sum(item.total.volume for item in h_result if hasattr(item, 'total') and item.total)
                    results["halstead_volume"] = round(total_volume, 2)
            except:
                results["halstead_volume"] = 0

            # Microsoft Visual Studio Maintainability Index ranges
            # Source: https://learn.microsoft.com/en-us/visualstudio/code-quality/code-metrics-maintainability-index-range-and-meaning
            mi = mi_score
            if mi >= 80:
                results["rating"] = "Good"
                results["color"] = "Green"
            elif mi >= 60:
                results["rating"] = "Moderate"
                results["color"] = "Yellow"
            elif mi >= 20:
                results["rating"] = "Difficult to maintain"
                results["color"] = "Red"
            else:  # < 20
                results["rating"] = "Critical - Very difficult to maintain"
                results["color"] = "Red"

    except Exception as e:
        results["error"] = str(e)

    return results





def evaluate_code(code: str) -> dict:
    """
    Comprehensive code quality evaluation.
    
    Combines multiple analysis methods:
    - Syntax validation (Python AST)
    - Complexity analysis (Radon)
    - Security scanning (Bandit)
    - Best practices checking
    """
    results = {
        "syntax_ok": False,
        "functions": 0,
        "avg_complexity": 0,
        "has_docstrings": False
    }

    try:
        tree = ast.parse(code)
        results["syntax_ok"] = True

        funcs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        results["functions"] = len(funcs)

        docstrings = [ast.get_docstring(f) for f in funcs if ast.get_docstring(f)]
        results["has_docstrings"] = len(docstrings) > 0

        analyzed = complexity.cc_visit(code)
        if analyzed:
            results["avg_complexity"] = round(sum(x.complexity for x in analyzed) / len(analyzed), 2)

    except SyntaxError:
        results["syntax_ok"] = False

    if results["syntax_ok"]:
        results["security"] = analyze_security(code)
        results["error_handling"] = analyze_error_handling(code)
        results["solid_principles"] = analyze_solid_principles(code)
        results["test_coverage"] = analyze_test_coverage(code)
        results["maintainability"] = calculate_maintainability_index(code)

    return results





def calculate_production_score(eval_results: dict) -> dict:
    """
    Calculate production readiness score (0-100+ scale with bonuses).
    
    Custom scoring algorithm evaluating:
    - Syntax (20 pts)
    - Documentation (15 pts)
    - Complexity (15 pts)
    - Security (20 pts)
    - Error handling (10 pts)
    - Tests (10 pts)
    - Maintainability (10 pts)
    - BONUS: Excellence bonuses (up to 10 pts)
    """
    score = 0
    max_score = 100
    breakdown = {}

    if not eval_results["syntax_ok"]:
        return {"total_score": 0, "rating": "Not Ready", "breakdown": {"syntax": "FAIL"}}

    breakdown["syntax"] = 20
    score += 20

    # Documentation (15 points)
    if eval_results.get("has_docstrings"):
        breakdown["documentation"] = 15
        score += 15
    else:
        breakdown["documentation"] = 0

    # Complexity (15 points) - graduated scoring
    avg_complexity = eval_results.get("avg_complexity", 0)
    if avg_complexity == 0:
        complexity_score = 15
    elif avg_complexity <= 3:
        complexity_score = 15  # Excellent
    elif avg_complexity <= 5:
        complexity_score = 13  # Very Good
    elif avg_complexity <= 7:
        complexity_score = 11  # Good
    elif avg_complexity <= 10:
        complexity_score = 8   # Acceptable
    elif avg_complexity <= 15:
        complexity_score = 4   # Needs improvement
    else:
        complexity_score = 0   # Poor
    
    breakdown["complexity"] = complexity_score
    score += complexity_score

    # Security (20 points) - graduated penalty
    sec = eval_results.get("security", {})
    security_issues = sec.get("security_issues", 0)
    high_severity = sec.get("high_severity", 0)
    
    if security_issues == 0:
        security_score = 20  # Perfect security
    elif high_severity > 0:
        # Critical: high severity issues = major penalty
        security_score = max(0, 20 - (high_severity * 10))  # -10 per high severity
    else:
        # Only medium/low issues
        security_score = max(5, 20 - (security_issues * 2))  # -2 per issue
    
    breakdown["security"] = security_score
    score += security_score

    # Error Handling (10 points) - graduated scoring
    err = eval_results.get("error_handling", {})
    err_score = 0
    
    if err.get("has_try_except"):
        err_score += 3
    if err.get("bare_except_count", 0) == 0:
        err_score += 2
    else:
        # Penalty for bare excepts
        err_score = max(0, err_score - err.get("bare_except_count", 0))
    if err.get("has_logging"):
        err_score += 2
    if err.get("has_validation"):
        err_score += 2
    if err.get("has_custom_exceptions"):
        err_score += 1  # Bonus for custom exceptions
    
    breakdown["error_handling"] = min(10, err_score)
    score += min(10, err_score)

    # Test Coverage (10 points) - graduated based on quality
    tests = eval_results.get("test_coverage", {})
    test_score = 0
    
    if tests.get("has_tests"):
        test_functions = tests.get("test_functions", 0)
        assertions = tests.get("assertion_count", 0)
        
        if test_functions >= 5 and assertions >= 10:
            test_score = 10  # Comprehensive tests
        elif test_functions >= 3 and assertions >= 5:
            test_score = 8   # Good coverage
        elif assertions > 0:
            test_score = 6   # Basic tests
        else:
            test_score = 3   # Tests exist but no assertions
    
    breakdown["tests"] = test_score
    score += test_score

    # Maintainability (10 points) - using Microsoft Visual Studio ranges
    # Source: https://learn.microsoft.com/en-us/visualstudio/code-quality/code-metrics-maintainability-index-range-and-meaning
    mi = eval_results.get("maintainability", {})
    mi_score = mi.get("maintainability_index", 0)
    
    if mi_score >= 80:
        maint_score = 10  # Good (Green)
    elif mi_score >= 70:
        maint_score = 8   # Good-Moderate transition
    elif mi_score >= 60:
        maint_score = 6   # Moderate (Yellow)
    elif mi_score >= 40:
        maint_score = 4   # Moderate-Difficult transition
    elif mi_score >= 20:
        maint_score = 2   # Difficult to maintain (Red)
    else:
        maint_score = 0   # Critical - Very difficult to maintain
    
    breakdown["maintainability"] = maint_score
    score += maint_score

    # BONUS POINTS for exceptional quality (up to +10)
    bonus = 0
    bonus_reasons = []
    
    # Bonus: Perfect security
    if security_issues == 0 and eval_results.get("functions", 0) > 3:
        bonus += 2
        bonus_reasons.append("Zero security vulnerabilities")
    
    # Bonus: Excellent complexity
    if avg_complexity > 0 and avg_complexity <= 3:
        bonus += 2
        bonus_reasons.append("Exceptional code simplicity")
    
    # Bonus: High test coverage
    if tests.get("test_functions", 0) >= 5 and tests.get("assertion_count", 0) >= 15:
        bonus += 2
        bonus_reasons.append("Comprehensive test coverage")
    
    # Bonus: Excellent maintainability (Microsoft "Good" range: >= 80)
    if mi_score >= 80:
        bonus += 2
        bonus_reasons.append("Outstanding maintainability (Microsoft Good range)")
    
    # Bonus: Advanced features (custom exceptions + logging + validation)
    if (err.get("has_custom_exceptions") and 
        err.get("has_logging") and 
        err.get("has_validation")):
        bonus += 2
        bonus_reasons.append("Advanced error handling")
    
    if bonus > 0:
        breakdown["excellence_bonus"] = bonus
        breakdown["bonus_reasons"] = bonus_reasons
        score += bonus

    # Dynamic rating based on actual score
    if score >= 100:
        rating = "Exceptional - Production Ready"
    elif score >= 90:
        rating = "Excellent - Production Ready"
    elif score >= 85:
        rating = "Production Ready"
    elif score >= 75:
        rating = "Nearly Ready"
    elif score >= 60:
        rating = "Needs Improvement"
    elif score >= 40:
        rating = "Significant Work Needed"
    else:
        rating = "Not Ready for Production"

    return {
        "total_score": score,
        "max_score": max_score,
        "percentage": round((score / max_score) * 100, 1),
        "rating": rating,
        "breakdown": breakdown
    }





def should_continue_refinement(current_score: int, previous_scores: list, iteration: int, max_iterations: int) -> dict:
    """
    Intelligent stopping criterion for iterative refinement.
    
    Custom convergence detection algorithm.
    """
    result = {
        "should_continue": False,
        "reason": "",
        "reached_plateau": False,
        "improvement_rate": 0
    }

    # Exceptional quality achieved
    if current_score >= 100:
        result["reason"] = "Code has achieved exceptional quality (score >= 100)"
        return result

    # Hit max iterations
    if iteration >= max_iterations:
        result["reason"] = "Maximum iterations reached"
        return result

    # Check for plateau (less than 1 point improvement in last 2 iterations)
    if len(previous_scores) >= 2:
        recent_improvement = current_score - previous_scores[-1]
        result["improvement_rate"] = recent_improvement

        if recent_improvement < 1 and len(previous_scores) >= 2:
            result["reached_plateau"] = True
            result["reason"] = f"Minimal improvement detected ({recent_improvement} points). Convergence plateau reached."
            return result

    # Continue refinement
    result["should_continue"] = True
    if current_score >= 90:
        result["reason"] = f"Continue refinement to reach exceptional quality from {current_score}/100"
    elif current_score >= 85:
        result["reason"] = f"Continue refinement to exceed production-ready from {current_score}/100"
    else:
        result["reason"] = f"Continue refinement to improve from {current_score}/100"
    return result
    if len(previous_scores) >= 2:
        recent_improvement = current_score - previous_scores[-1]
        result["improvement_rate"] = recent_improvement

        if recent_improvement < 2 and len(previous_scores) >= 2:
            result["reached_plateau"] = True
            result["reason"] = f"Minimal improvement detected ({recent_improvement}% gain). Convergence plateau reached."
            return result

    # Continue refinement
    result["should_continue"] = True
    result["reason"] = f"Continue refinement to improve from {current_score}/100"
    return result





def build_improvement_prompt(original_prompt: str, code: str, eval_results: dict, recommendations: list) -> str:
    """
    Build prompt for iterative code improvement based on test results and recommendations.
    
    Custom prompt engineering for LLM-based code refinement.
    Makes it explicit that the LLM should apply the specific recommendations.
    """
    prod_score = calculate_production_score(eval_results)

    improvement_prompt = f"""TASK: Improve the following Python code based on quality analysis and test results.

ORIGINAL REQUIREMENT:
{original_prompt}

CURRENT CODE:
{code}

QUALITY ANALYSIS RESULTS (Based on Tests):
- Production Score: {prod_score['total_score']}/{prod_score['max_score']} ({prod_score['rating']})
- Syntax Valid: {'Yes' if eval_results['syntax_ok'] else 'No'}
- Has Docstrings: {'Yes' if eval_results.get('has_docstrings') else 'No'}
- Avg Complexity: {eval_results.get('avg_complexity', 0)}
- Security Issues: {eval_results.get('security', {}).get('security_issues', 0)}
- Has Error Handling: {'Yes' if eval_results.get('error_handling', {}).get('has_try_except') else 'No'}
- Has Tests: {'Yes' if eval_results.get('test_coverage', {}).get('has_tests') else 'No'}
- Maintainability Index: {eval_results.get('maintainability', {}).get('maintainability_index', 0)}

SPECIFIC RECOMMENDATIONS TO APPLY (from test results):
"""

    for i, rec in enumerate(recommendations, 1):
        improvement_prompt += f"{i}. {rec}\n"

    improvement_prompt += f"""

INSTRUCTIONS FOR IMPROVED CODE:
You MUST address ALL {len(recommendations)} recommendations listed above. For each recommendation:
- Apply the specific fix mentioned
- Maintain all original functionality
- Ensure no breaking changes

Additional requirements:
1. Add comprehensive docstrings to every function and class
2. Implement proper error handling with try-except blocks
3. Add input validation for all user-facing functions
4. Include logging statements for debugging
5. Add unit tests with assertions
6. Follow SOLID principles
7. Ensure cyclomatic complexity < 10 for all functions
8. Fix any security vulnerabilities

Return ONLY the complete improved Python code without explanations or markdown formatting.
"""

    return improvement_prompt





def refine_code_automatic(original_prompt: str, code: str, eval_results: dict) -> tuple:
    """
    Automatic iterative code refinement system based on test results and recommendations.
    
    Custom algorithm with intelligent stopping based on:
    - Score improvement tracking
    - Convergence detection
    - Maximum iteration limits
    
    The LLM applies recommendations generated from test/evaluation results.
    """
    if not client:
        print("API not available. Cannot refine code.")
        return code, eval_results, 0, []

    current_code = code
    current_eval = eval_results
    improvement_history = []
    score_history = []
    iteration = 0
    max_auto_iterations = 8

    while iteration < max_auto_iterations:
        iteration += 1

        # Calculate current score
        prod_score = calculate_production_score(current_eval)
        current_score = prod_score['total_score']
        score_history.append(current_score)

        # Check convergence
        convergence = should_continue_refinement(
            current_score, 
            score_history[:-1],  # Previous scores
            iteration,
            max_auto_iterations
        )

        # Generate recommendations based on current evaluation
        recommendations = generate_recommendations(current_eval)

        # Track history
        improvement_history.append({
            "iteration": iteration,
            "score": current_score,
            "rating": prod_score['rating'],
            "reason": convergence.get("reason", ""),
            "recommendations_count": len(recommendations)
        })

        print(f"\n{'='*50}")
        print(f"Iteration {iteration}: Score {current_score}/100 ({prod_score['rating']})")
        print(f"   {convergence['reason']}")
        print(f"   Recommendations to apply: {len(recommendations)}")
        print(f"{'='*50}")

        if not convergence["should_continue"]:
            break

        # Build improvement prompt with specific recommendations
        improvement_prompt = build_improvement_prompt(
            original_prompt,
            current_code,
            current_eval,
            recommendations
        )

        # Generate improved code by applying recommendations
        try:
            print(f"\n🤖 Applying {len(recommendations)} recommendation(s) via LLM...")
            for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
                print(f"   {i}. {rec[:70]}...")
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": """You are an expert Python developer focused on code quality.
Given code with specific issues identified by tests and analysis, produce improved code that addresses ALL identified problems while maintaining functionality.
Apply each recommendation precisely and completely.
Return ONLY the complete improved Python code without explanations."""},
                    {"role": "user", "content": improvement_prompt},
                ],
                temperature=0.5,
                max_tokens=4096,
            )

            improved_code = response.choices[0].message.content

            if "```python" in improved_code:
                improved_code = improved_code.split("```python")[1].split("```")[0].strip()
            elif "```" in improved_code:
                improved_code = improved_code.split("```")[1].split("```")[0].strip()

            # Evaluate improved code
            print(f"   ✓ Code improved, re-evaluating...")
            new_eval = evaluate_code(improved_code)
            new_score = calculate_production_score(new_eval)

            if new_score['total_score'] > current_score:
                print(f"   ✅ Score improved: {current_score} → {new_score['total_score']} (+{new_score['total_score'] - current_score})")
                current_code = improved_code
                current_eval = new_eval
            else:
                print(f"   ⚠️  No improvement. Stopping refinement.")
                break

        except Exception as e:
            print(f"   ❌ Refinement failed: {e}")
            break

    print(f"\n{'='*50}")
    print(f"REFINEMENT COMPLETE: {iteration} iteration(s)")
    print(f"{'='*50}\n")

    return current_code, current_eval, iteration, improvement_history





def generate_documentation(prompt: str, code: str, eval_results: dict, improvement_history: list) -> str:
    """
    Generate comprehensive project documentation.
    
    Custom documentation generator for evaluation results.
    """
  
    prod_score = calculate_production_score(eval_results)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    doc = f"""# Auto-Generated Project Documentation

**Generated:** {timestamp}

---

## 0. Installation

Recommended Python version: 3.8+

Create and activate a virtual environment (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies from the included requirements file:

```bash
pip install -r requirements.txt
```

Or install the main packages directly:

```bash
pip install groq radon bandit
```

If you use the Groq API, export your API key before running the script:

```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

---

## 1. Project Overview

### Objective
{prompt}

### Production Readiness
- **Overall Score:** {prod_score['total_score']}/{prod_score['max_score']} ({prod_score['percentage']}%)
- **Status:** {prod_score['rating']}
- **Refinement Iterations:** {len(improvement_history) - 1}

---

## 2. Refinement History

"""

    if improvement_history:
        doc += "| Iteration | Score | Rating | Notes |\n"
        doc += "|-----------|-------|--------|-------|\n"
        for entry in improvement_history:
            reason = entry.get('reason', 'Initial')[:50]
            doc += f"| {entry['iteration']} | {entry['score']}/100 | {entry['rating']} | {reason} |\n"
        doc += "\n"

    doc += """---

## 3. Code Quality Metrics

### Basic Metrics
"""
    doc += f"- **Functions:** {eval_results.get('functions', 0)}\n"
    doc += f"- **Syntax Valid:** {'Yes' if eval_results['syntax_ok'] else 'No'}\n"
    doc += f"- **Average Complexity:** {eval_results.get('avg_complexity', 0)}\n"
    doc += f"- **Has Docstrings:** {'Yes' if eval_results.get('has_docstrings') else 'No'}\n"

    doc += "\n### Maintainability"
    mi = eval_results.get('maintainability', {})
    doc += f"\n- **Maintainability Index:** {mi.get('maintainability_index', 0)} ({mi.get('rating', 'N/A')})\n"
    doc += f"- **Halstead Volume:** {mi.get('halstead_volume', 0):.2f}\n"
    doc += f"- **Logical Lines of Code:** {mi.get('lloc', 0)}\n"

    doc += "\n### Security"
    sec = eval_results.get('security', {})
    if 'error' not in sec:
        doc += f"\n- **Total Issues:** {sec.get('security_issues', 0)}\n"
        doc += f"- **High Severity:** {sec.get('high_severity', 0)}\n"
        if sec.get('issues'):
            doc += "\n**Issues Found:**\n"
            for issue in sec['issues'][:5]:
                doc += f"  - Line {issue['line']}: {issue['issue']} [{issue['severity']}]\n"

    doc += "\n### Error Handling"
    err = eval_results.get('error_handling', {})
    doc += f"\n- **Try-Except Blocks:** {err.get('exception_count', 0)}\n"
    doc += f"- **Bare Except Clauses:** {err.get('bare_except_count', 0)}\n"
    doc += f"- **Has Logging:** {'Yes' if err.get('has_logging') else 'No'}\n"
    doc += f"- **Input Validation:** {'Yes' if err.get('has_validation') else 'No'}\n"

    doc += "\n### Test Coverage"
    tests = eval_results.get('test_coverage', {})
    doc += f"\n- **Test Functions:** {tests.get('test_functions', 0)}\n"
    doc += f"- **Assertions:** {tests.get('assertion_count', 0)}\n"
    doc += f"- **Frameworks:** {', '.join(tests.get('test_frameworks', [])) if tests.get('test_frameworks') else 'None'}\n"

    doc += "\n### SOLID Principles"
    solid = eval_results.get('solid_principles', {})
    doc += f"\n- **SRP Score:** {solid.get('srp_score', 0):.1f}/100\n"
    doc += f"- **Class Count:** {solid.get('class_count', 0)}\n"
    if solid.get('god_classes'):
        doc += f"- **God Classes:** {', '.join(solid['god_classes'])}\n"
    if solid.get('long_methods'):
        doc += f"- **Long Methods:** {', '.join(solid['long_methods'])}\n"

    doc += f"""

---

## 4. Score Breakdown

"""
    for category, points in prod_score['breakdown'].items():
        max_points = {"syntax": 20, "documentation": 15, "complexity": 15, 
                     "security": 20, "error_handling": 10, "tests": 10, 
                     "maintainability": 10}.get(category, 10)
        percentage = (points / max_points * 100) if max_points > 0 else 0
        doc += f"- **{category.title()}:** {points}/{max_points} ({percentage:.0f}%)\n"

    recommendations = generate_recommendations(eval_results)
    doc += f"""

---

## 5. Recommendations

"""
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            doc += f"{i}. {rec}\n"
    else:
        doc += "No major recommendations. Code is well-structured!\n"

    doc += f"""

---

## 6. Generated Code

```python
{code}
```

---

## 7. Usage Notes

- This code was automatically generated and refined for production readiness
- Review security issues before deploying to production
- Run the included unit tests before integration
- Consider additional testing for edge cases
- Document any custom configurations or environment variables needed
- Ensure all dependencies are properly installed: `pip install -r requirements.txt`

---

*Documentation generated automatically by AI Code Quality Evaluator*
"""

    return doc





def generate_recommendations(eval_results: dict) -> list:
    """
    Generate comprehensive list of recommendations based on evaluation.
    
    Includes static and dynamic code analysis principles from:
    - Checkpoint Dynamic Code Analysis guidelines
    - OWASP security best practices
    - Clean Code principles (Robert C. Martin)

    Args:
        eval_results (dict): Code evaluation results

    Returns:
        list: Recommendations for improvement
    """
    recommendations = []

    # Documentation & Code Clarity
    if not eval_results.get('has_docstrings'):
        recommendations.append("Add comprehensive docstrings to all functions and classes with parameter types and return values")
    
    # Complexity & Maintainability
    avg_complexity = eval_results.get('avg_complexity', 0)
    if avg_complexity > 15:
        recommendations.append(f"Critical: Refactor highly complex functions (complexity {avg_complexity:.1f} > 15). Break into smaller, single-responsibility functions")
    elif avg_complexity > 10:
        recommendations.append(f"Refactor complex functions (complexity {avg_complexity:.1f} > 10) to improve readability and testability")
    elif avg_complexity > 5:
        recommendations.append(f"Consider simplifying moderately complex functions (complexity {avg_complexity:.1f}) for long-term maintainability")
    
    # Security Analysis
    security = eval_results.get('security', {})
    high_severity = security.get('high_severity', 0)
    total_issues = security.get('security_issues', 0)
    
    if high_severity > 0:
        recommendations.append(f"CRITICAL: Fix {high_severity} high-severity security vulnerability/vulnerabilities immediately (SQL injection, hardcoded secrets, command injection)")
    if total_issues > high_severity:
        medium_issues = total_issues - high_severity
        recommendations.append(f"Address {medium_issues} medium/low severity security issue(s) to harden defenses")
    
    # Add security best practices
    if total_issues == 0 and eval_results.get('syntax_ok'):
        # Recommend proactive security measures
        recommendations.append("Implement input sanitization and validation for all user-facing functions")
        recommendations.append("Add security headers and CSRF protection for web endpoints")
    
    # Error Handling & Resilience
    error_handling = eval_results.get('error_handling', {})
    
    if not error_handling.get('has_try_except'):
        recommendations.append("Add comprehensive error handling with try-except blocks for all I/O operations and external calls")
    
    if error_handling.get('bare_except_count', 0) > 0:
        recommendations.append(f"Replace {error_handling['bare_except_count']} bare 'except:' clause(s) with specific exception types (ValueError, IOError, etc.)")
    
    if not error_handling.get('has_validation'):
        recommendations.append("Add input validation with type checking and range validation to prevent runtime errors")
    
    if not error_handling.get('has_custom_exceptions'):
        recommendations.append("Create custom exception classes for domain-specific error scenarios")
    
    if not error_handling.get('has_logging'):
        recommendations.append("Add structured logging with different levels (DEBUG, INFO, WARNING, ERROR) for debugging and monitoring")
    
    # Testing & Quality Assurance
    tests = eval_results.get('test_coverage', {})
    test_count = tests.get('test_functions', 0)
    assertion_count = tests.get('assertion_count', 0)
    
    if not tests.get('has_tests'):
        recommendations.append("Add comprehensive unit tests with pytest or unittest framework - aim for 80%+ code coverage")
    elif test_count < 3:
        recommendations.append(f"Expand test suite beyond {test_count} test(s) - add edge cases, error scenarios, and integration tests")
    elif assertion_count < test_count * 2:
        recommendations.append(f"Add more assertions per test (currently {assertion_count}/{test_count} ratio) to validate behavior thoroughly")
    
    # Maintainability Index (Microsoft Visual Studio ranges)
    # Source: https://learn.microsoft.com/en-us/visualstudio/code-quality/code-metrics-maintainability-index-range-and-meaning
    mi = eval_results.get('maintainability', {})
    mi_score = mi.get('maintainability_index', 0)
    mi_rating = mi.get('rating', 'Unknown')
    mi_color = mi.get('color', 'Unknown')
    
    if mi_score < 20:
        recommendations.append(f"CRITICAL: Maintainability Index extremely low ({mi_score:.1f}/100, {mi_rating}). Immediate refactoring required - code is very difficult to maintain")
    elif mi_score < 60:
        recommendations.append(f"URGENT: Maintainability Index in red zone ({mi_score:.1f}/100, {mi_rating}). Difficult to maintain - reduce complexity, add comments, improve structure")
    elif mi_score < 80:
        recommendations.append(f"Maintainability Index in yellow zone ({mi_score:.1f}/100, {mi_rating}). Moderate maintainability - can be enhanced with refactoring")
    elif mi_score < 90:
        recommendations.append(f"Good maintainability ({mi_score:.1f}/100, Green zone), but can reach excellent with minor improvements")
    
    # SOLID Principles
    solid = eval_results.get('solid_principles', {})
    god_classes = solid.get('god_classes', [])
    long_methods = solid.get('long_methods', [])
    avg_methods = solid.get('avg_methods_per_class', 0)
    
    if god_classes:
        recommendations.append(f"Refactor God classe(s) {', '.join(god_classes)} - violates Single Responsibility Principle. Split into focused classes")
    
    if long_methods:
        recommendations.append(f"Break down long method(s) {', '.join(long_methods[:3])} (>50 lines) into smaller functions")
    
    if avg_methods > 10:
        recommendations.append(f"Classes average {avg_methods:.1f} methods - consider extracting related methods into separate classes or modules")
    
    # Dynamic Code Analysis Recommendations (Checkpoint principles)
    if eval_results.get('syntax_ok'):
        # Runtime behavior recommendations
        recommendations.append("Consider adding runtime assertions and invariant checks for dynamic behavior validation")
        recommendations.append("Implement code profiling to identify performance bottlenecks during execution")
        recommendations.append("Add memory usage monitoring for resource-intensive operations")
        
        # Code quality patterns
        if not error_handling.get('has_validation'):
            recommendations.append("Use defensive programming: validate inputs at function boundaries to fail fast")
        
        if eval_results.get('functions', 0) > 5 and not tests.get('has_tests'):
            recommendations.append("Add integration tests to verify component interactions and data flow")
        
        # Modern best practices
        recommendations.append("Use type hints (PEP 484) for better IDE support and static analysis")
        recommendations.append("Consider using linters (pylint, flake8) and formatters (black) for consistent code style")
        recommendations.append("Add pre-commit hooks to enforce quality checks before code commits")
    
    return recommendations




def apply_recommendations_once(original_prompt: str, code: str, eval_results: dict, recommendations: list) -> tuple:
    """
    Ask the LLM to apply the provided recommendations once and return the resulting code and its evaluation.

    Returns: (new_code, new_eval_results)
    """
    if not client:
        print("API not available. Skipping applying recommendations via LLM.")
        return code, eval_results

    if not recommendations:
        return code, eval_results

    print("\nApplying end-of-report recommendations to the initial Groq code...")
    improvement_prompt = build_improvement_prompt(original_prompt, code, eval_results, recommendations)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert Python developer focused on improving code quality. Apply the listed recommendations to the provided code and return ONLY the complete improved Python code without any explanation or markdown."},
                {"role": "user", "content": improvement_prompt},
            ],
            temperature=0.5,
            max_tokens=4096,
        )

        new_code = response.choices[0].message.content
        if "```python" in new_code:
            new_code = new_code.split("```python")[1].split("```")[0].strip()
        elif "```" in new_code:
            new_code = new_code.split("```")[1].split("```")[0].strip()

        new_eval = evaluate_code(new_code)
        return new_code, new_eval

    except Exception as e:
        print(f"Failed to apply recommendations via LLM: {e}")
        return code, eval_results





def report_results(prompt: str, code: str, eval_results: dict, improvement_history: list = None):
    """
    Generate and display comprehensive quality report.

    Args:
        prompt (str): Original user prompt
        code (str): Final generated code
        eval_results (dict): Code evaluation results
        improvement_history (list): Iteration history
    """
    print("\n" + "="*60)
    print("CODE GENERATION & QUALITY REPORT")
    print("="*60)
    print(f"\nPrompt:\n{prompt}\n")

    # Show improvement progression if available
    if improvement_history and len(improvement_history) > 1:
        print("-"*60)
        print("IMPROVEMENT PROGRESSION:")
        print("-"*60)
        for entry in improvement_history:
            print(f"   Iteration {entry['iteration']}: {entry['score']}/100 ({entry['rating']})")
        print()

    print("-"*60)
    print("FINAL GENERATED CODE:")
    print("-"*60)
    print(code)
    print()

    # Production Score
    prod_score = calculate_production_score(eval_results)
    print("="*60)
    print(f"PRODUCTION READINESS SCORE: {prod_score['total_score']}/{prod_score['max_score']} ({prod_score['percentage']}%)")
    print(f"   Rating: {prod_score['rating']}")
    print("="*60)

    print("\nSCORE BREAKDOWN:")
    for category, points in prod_score['breakdown'].items():
        max_points = {"syntax": 20, "documentation": 15, "complexity": 15,
                     "security": 20, "error_handling": 10, "tests": 10,
                     "maintainability": 10}.get(category, 10)
        print(f"   • {category.title()}: {points}/{max_points}")

    # Basic Metrics
    print("\nBASIC METRICS:")
    print(f"   • Syntax Valid: {'Yes' if eval_results['syntax_ok'] else 'No'}")
    print(f"   • Functions: {eval_results.get('functions', 0)}")
    print(f"   • Avg Complexity: {eval_results.get('avg_complexity', 0)}")
    print(f"   • Has Docstrings: {'Yes' if eval_results.get('has_docstrings') else 'No'}")

    # Maintainability
    if 'maintainability' in eval_results:
        mi = eval_results['maintainability']
        print(f"\nMAINTAINABILITY INDEX:")
        print(f"   • Score: {mi.get('maintainability_index', 0)} - {mi.get('rating', 'N/A')}")
        print(f"   • Halstead Volume: {mi.get('halstead_volume', 0):.2f}")
        print(f"   • Logical LOC: {mi.get('lloc', 0)}")

    # Security
    if 'security' in eval_results:
        sec = eval_results['security']
        print(f"\nSECURITY ANALYSIS:")
        if 'error' in sec:
            print(f"   Warning: {sec['error']}")
        else:
            print(f"   • Total Issues: {sec.get('security_issues', 0)}")
            print(f"   • High Severity: {sec.get('high_severity', 0)}")
            if sec.get('issues'):
                print(f"   • Top Issues:")
                for issue in sec['issues'][:3]:
                    print(f"     - Line {issue['line']}: {issue['issue']} [{issue['severity']}]")

    # Error Handling
    if 'error_handling' in eval_results:
        err = eval_results['error_handling']
        print(f"\nERROR HANDLING:")
        print(f"   • Try-Except Blocks: {err.get('exception_count', 0)}")
        print(f"   • Bare Except: {err.get('bare_except_count', 0)} {'(avoid!)' if err.get('bare_except_count', 0) > 0 else ''}")
        print(f"   • Has Logging: {'Yes' if err.get('has_logging') else 'No'}")
        print(f"   • Input Validation: {'Yes' if err.get('has_validation') else 'No'}")

    # Tests
    if 'test_coverage' in eval_results:
        tests = eval_results['test_coverage']
        print(f"\nTEST COVERAGE:")
        print(f"   • Has Tests: {'Yes' if tests.get('has_tests') else 'No'}")
        print(f"   • Test Functions: {tests.get('test_functions', 0)}")
        print(f"   • Assertions: {tests.get('assertion_count', 0)}")
        if tests.get('test_frameworks'):
            print(f"   • Frameworks: {', '.join(tests['test_frameworks'])}")

    # SOLID Principles
    if 'solid_principles' in eval_results:
        solid = eval_results['solid_principles']
        print(f"\nSOLID PRINCIPLES:")
        print(f"   • SRP Score: {solid.get('srp_score', 0):.1f}/100")
        print(f"   • Classes: {solid.get('class_count', 0)}")
        if solid.get('god_classes'):
            print(f"   • God Classes (>10 methods): {', '.join(solid['god_classes'])}")
        if solid.get('long_methods'):
            print(f"   • Long Methods (>50 lines): {', '.join(solid['long_methods'])}")

    recommendations = generate_recommendations(eval_results)
    print("\nRECOMMENDATIONS:")

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    else:
        print("   Code looks good! Consider peer review before deployment.")

    print("\n" + "="*60)





def get_multiline_input(prompt: str) -> str:
    """
    Get multi-line input from user.

    Args:
        prompt (str): Input prompt

    Returns:
        str: Multi-line user input
    """
    print(prompt)
    print("(Paste your task description. Press Enter twice when done, or type 'END' on a new line)")
    print("-" * 60)

    lines = []
    empty_line_count = 0

    while True:
        try:
            line = input()

            if line.strip().upper() == 'END':
                break

            if not line.strip():
                empty_line_count += 1
                if empty_line_count >= 2:
                    break
            else:
                empty_line_count = 0

            lines.append(line)

        except EOFError:
            break

    while lines and not lines[-1].strip():
        lines.pop()

    return '\n'.join(lines)





if __name__ == "__main__":
    print("AI Code Quality Evaluator with Auto-Refinement (Powered by Groq)")
    print("="*60)
    print("This tool generates Python code from your description,")
    print("evaluates it for production readiness, and automatically")
    print("improves it to achieve the best quality possible.")
    print("="*60)

    # Get multi-line input
    user_prompt = get_multiline_input("\nEnter your coding task:")

    if not user_prompt.strip():
        print("No input provided. Exiting.")
        exit(1)

    print("\nGenerating initial code (this may take 5-10 seconds)...")
    generated_code = generate_code(user_prompt)

    # Keep a copy of the raw initial Groq output so we can print it later
    initial_groq_code = generated_code

    print("Evaluating initial code quality...")
    eval_results = evaluate_code(generated_code)

    initial_score = calculate_production_score(eval_results)
    print(f"\nInitial Score: {initial_score['total_score']}/100 ({initial_score['rating']})")

    print("\n" + "-"*60)
    print("INITIAL GROQ-GENERATED CODE:")
    print("-"*60)
    print(initial_groq_code)

    recs = generate_recommendations(eval_results)
    if recs:
        print("\nRecommendations detected from initial evaluation:")
        for i, r in enumerate(recs, 1):
            print(f"   {i}. {r}")

        rec_code, rec_eval = apply_recommendations_once(user_prompt, generated_code, eval_results, recs)
        rec_score = calculate_production_score(rec_eval)

        if rec_score['total_score'] > initial_score['total_score']:
            print(f"\nApplying recommendations improved score: {initial_score['total_score']} -> {rec_score['total_score']}")
            generated_code = rec_code
            eval_results = rec_eval
        else:
            print(f"\nApplying recommendations did not improve the score ({initial_score['total_score']} -> {rec_score['total_score']}). Keeping initial Groq output as starting point.")

    print("\nStarting automatic refinement process...")
    print("   (This will refine the code intelligently until production-ready or convergence)")

    generated_code, eval_results, iterations, improvement_history = refine_code_automatic(
        user_prompt,
        generated_code,
        eval_results
    )

    print(f"\nRefinement complete after {iterations} iteration(s)")

    report_results(user_prompt, generated_code, eval_results, improvement_history)

    print("\nGenerating documentation...")
    documentation = generate_documentation(user_prompt, generated_code, eval_results, improvement_history)

    save = input("\nSave results? (y/n): ").strip().lower()
    if save == 'y':
        # Save code
        code_filename = input("Enter code filename (default: generated_code.py): ").strip() or "generated_code.py"
        with open(code_filename, 'w') as f:
            f.write(f"# Auto-generated and refined code\n")
            f.write(f"# Original prompt: {user_prompt[:100]}...\n")
            f.write(f"# Production score: {calculate_production_score(eval_results)['total_score']}/100\n\n")
            f.write(generated_code)
        print(f"Code saved to {code_filename}")

        # Save documentation
        doc_filename = input("Enter documentation filename (default: PROJECT_DOCUMENTATION.md): ").strip() or "PROJECT_DOCUMENTATION.md"
        with open(doc_filename, 'w') as f:
            f.write(documentation)
        print(f"Documentation saved to {doc_filename}")

