from urllib.parse import quote

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


def generate_image(prompt: str) -> str:
    try:
        url = POLLINATIONS_URL.format(prompt=quote(prompt))
        import httpx
        r = httpx.get(url, timeout=30)
        if r.status_code == 200:
            return url
        return f"Error: status {r.status_code}"
    except Exception as e:
        return f"Error al generar imagen: {e}"
