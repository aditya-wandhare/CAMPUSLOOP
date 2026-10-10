"""Small, shared wrapper for the required Gemma model and Gemini API."""
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# Read key/value pairs from .env into the process environment.
load_dotenv()

MODEL_NAME = "gemma-4-26b-a4b-it"


def _get_client():
    """Create a client without ever displaying the API key."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=api_key)


def _response_text(response):
    """Return readable model text, including a friendly fallback."""
    return (getattr(response, "text", None) or "Gemma returned an empty response.").strip()


def ask(prompt: str) -> str:
    """Send one text prompt to the fixed Gemma model and return its answer."""
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return _response_text(response)


def ask_with_image(prompt: str, image_path: str | Path) -> str:
    """Send one image-and-text prompt to Gemma using a temporary uploaded image."""
    client = _get_client()
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError("The selected image could not be found. Please upload it again.")

    uploaded_file = client.files.upload(file=str(path))
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[uploaded_file, prompt],
        )
        return _response_text(response)
    finally:
        # Best-effort cleanup. Never print the API key or uploaded file details.
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass


def make_chat():
    """Create a fresh chat session; the app sends only one message per click."""
    client = _get_client()
    return client.chats.create(model=MODEL_NAME)
