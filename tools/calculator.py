import ast
import math
import operator


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_ALLOWED_FUNCS = {"abs": abs, "round": round, "int": int, "float": float, "min": min, "max": max}
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        return _OPERATORS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp):
        return _OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.Call):
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        if func_name in _ALLOWED_FUNCS:
            args = [_safe_eval(a) for a in node.args]
            return _ALLOWED_FUNCS[func_name](*args)
        raise ValueError(f"Funcion no permitida: {func_name}")
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTS:
            return _ALLOWED_CONSTS[node.id]
        raise ValueError(f"Variable no permitida: {node.id}")
    raise ValueError(f"Expresion no soportada: {type(node).__name__}")


def calculate(expression: str) -> str:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        return str(result)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error al calcular: {e}"
