"""Auto-generated tool module."""

from __future__ import annotations

import ast
import json
import math


def run(payload: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        data = json.loads(payload)
        expression = str(data.get("expression", ""))
    except (json.JSONDecodeError, TypeError):
        expression = payload

    if not expression.strip():
        return "error: empty expression"

    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "sqrt": math.sqrt, "log": math.log,
        "log10": math.log10, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "pi": math.pi, "e": math.e,
        "ceil": math.ceil, "floor": math.floor,
    }
    allowed_nodes = {
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call,
        ast.Name, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.USub, ast.UAdd, ast.Load,
    }
    try:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if type(node) not in allowed_nodes:
                if isinstance(node, ast.Name) and node.id in allowed_names:
                    continue
                return "error: disallowed operation in expression"
        result = eval(
            compile(tree, "<calculator>", "eval"),
            {"__builtins__": {}},
            allowed_names,
        )
        if isinstance(result, float):
            result = round(result, 10)
        return str(result)
    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "calculator",
    "description": "Evaluate a mathematical expression with support for basic arithmetic and math functions (sqrt, sin, cos, log, etc.).",
    "category": "analysis",
    "domain": "science",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate, e.g. '2 + 3 * 4' or 'sqrt(16) + sin(pi/2)'"
            }
        },
        "required": ["expression"]
    }
}
