import os


_MAX_FILE_SIZE = 1024 * 1024  # 1 MB


def read_file(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return f"Error: el archivo '{path}' no existe."
    if os.path.isdir(abs_path):
        return f"Error: '{path}' es un directorio, no un archivo."
    size = os.path.getsize(abs_path)
    if size > _MAX_FILE_SIZE:
        return f"Error: el archivo es demasiado grande ({size} bytes, maximo {_MAX_FILE_SIZE} bytes)."
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"Error al leer el archivo: {e}"
