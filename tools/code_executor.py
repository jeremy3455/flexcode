import subprocess
import sys
import tempfile


def execute_python(code: str, timeout: int = 10) -> str:
    if "input(" in code:
        return "Error: no se permite input() por seguridad."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmppath = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmppath],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\nErrores:\n{result.stderr}"
        return output.strip() or "(sin salida)"
    except subprocess.TimeoutExpired:
        return "Error: el codigo tardo demasiado (>10s)."
    except Exception as e:
        return f"Error al ejecutar: {e}"
    finally:
        import os
        try:
            os.unlink(tmppath)
        except Exception:
            pass
