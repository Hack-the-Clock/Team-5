"""
Python Code Analyzer for Browser Execution
Pyodide: Mozilla Public License 2.0
See: https://pyodide.org and CREDITS.md
"""

import ast
import json

def analyze_code_simple(code: str) -> str:
    result = {
        "syntax_ok": False,
        "functions": 0,
        "classes": 0,
        "has_docstrings": False,
        "line_count": 0,
        "comment_count": 0,
        "error": None
    }

    try:
        result["line_count"] = len(code.splitlines())
        result["comment_count"] = sum(1 for l in code.splitlines() if l.strip().startswith("#"))

        tree = ast.parse(code)
        result["syntax_ok"] = True

        funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        result["functions"] = len(funcs)
        result["classes"] = len(classes)

        has_docs = False
        if ast.get_docstring(tree):
            has_docs = True
        else:
            for f in funcs + classes:
                if ast.get_docstring(f):
                    has_docs = True
                    break
        result["has_docstrings"] = has_docs

    except SyntaxError as e:
        result["error"] = f"SyntaxError: {e}"
    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result)
