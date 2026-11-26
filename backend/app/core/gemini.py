import time
import json
import re
from typing import Optional, Any, Dict, List
from google import genai
from google.genai import types
from backend.app.core.config import settings
from backend.app.core.logger import logger


class GeminiClient:
    """
    Thread-safe wrapper around Google GenAI client with automatic model failover,
    configurable temperature, and multimodal PDF/image extraction.
    """
    _instance: Optional["GeminiClient"] = None
    _client: Optional[genai.Client] = None
    _configured_key: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    @property
    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    def _init_client(self):
        key = (settings.GEMINI_API_KEY or "").strip()
        if not key:
            logger.warning("GEMINI_API_KEY is not set. Running in Local Extractive fallback mode.")
            self._client = None
            self._configured_key = None
            return
        try:
            self._client = genai.Client(api_key=key)
            self._configured_key = key
            logger.info("Gemini Client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self._client = None
            self._configured_key = None

    def _ensure_client(self) -> genai.Client:
        key = (settings.GEMINI_API_KEY or "").strip()
        if not key:
            self._client = None
            self._configured_key = None
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        if not self._client or self._configured_key != key:
            self._init_client()
        if not self._client:
            raise RuntimeError("GEMINI_API_KEY not configured or client initialization failed.")
        return self._client

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 2,
    ) -> str:
        client = self._ensure_client()
        target_model = model or settings.DEFAULT_GEMINI_MODEL
        candidates: List[str] = [target_model]
        for fb in settings.GEMINI_FALLBACK_MODELS:
            if fb not in candidates:
                candidates.append(fb)

        gen_config = types.GenerateContentConfig(temperature=settings.TEMPERATURE)
        last_error = None
        for candidate in candidates:
            for attempt in range(1, max_retries + 1):
                try:
                    response = client.models.generate_content(
                        model=candidate,
                        contents=prompt,
                        config=gen_config
                    )
                    if hasattr(response, "text") and response.text:
                        return response.text.strip()
                    elif hasattr(response, "output_text") and response.output_text:
                        return response.output_text.strip()
                    return str(response).strip()
                except Exception as e:
                    err_msg = str(e)
                    last_error = e
                    if any(code in err_msg for code in ["404", "429", "503", "NOT_FOUND", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                        logger.warning(f"Model '{candidate}' unavailable ({err_msg[:60]}...). Switching to fallback model...")
                        break
                    logger.warning(f"Model '{candidate}' attempt {attempt}/{max_retries} failed: {err_msg[:80]}")
                    if attempt < max_retries:
                        time.sleep(0.5)

        for candidate in candidates[:2]:
            try:
                logger.info(f"Trying interactions.create fallback with {candidate}...")
                resp = client.interactions.create(
                    model=candidate,
                    input=prompt
                )
                if hasattr(resp, "output_text") and resp.output_text:
                    return resp.output_text.strip()
                elif hasattr(resp, "text") and resp.text:
                    return resp.text.strip()
            except Exception as rescue_err:
                logger.warning(f"Interactions fallback failed for {candidate}: {rescue_err}")

        raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")

    def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        raw_text = self.generate(prompt=prompt, model=model, max_retries=max_retries)
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse JSON from response:\n{cleaned}")
            raise ValueError(f"Model output could not be parsed as valid JSON: {cleaned[:100]}...")

    def extract_document_multimodal(self, pdf_path: str) -> str:
        """
        Extracts full text, tables, and details from scanned or image-based PDFs
        using Gemini Multimodal Document Vision.
        """
        client = self._ensure_client()
        logger.info(f"Uploading PDF to Gemini for multimodal OCR extraction: {pdf_path}")
        uploaded_file = client.files.upload(file=pdf_path)

        prompt = """
You are an expert multimodal document intelligence and OCR transcription system.
Extract ALL readable text, including:
- Handwritten notes, cursive writing, and student/doctor handwriting
- Printed text, headers, and bullet points
- Tables, numbers, mathematical formulas, and margin annotations
Transcribe all handwritten words faithfully. Format the output clearly using structured markdown.
Do not omit any sections, notes, or handwritten remarks.
"""
        try:
            response = client.models.generate_content(
                model=settings.DEFAULT_GEMINI_MODEL,
                contents=[uploaded_file, prompt]
            )
            return response.text.strip() if response.text else ""
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as del_err:
                logger.warning(f"Failed to delete uploaded temp file from Gemini: {del_err}")

    def extract_image_multimodal(self, image_bytes: bytes, mime_type: str, source_name: str = "image") -> str:
        """
        Transcribes text, tables, diagrams, and charts from image files (PNG, JPEG, WebP)
        using Gemini Multimodal Vision.
        """
        client = self._ensure_client()
        logger.info(f"Running Gemini multimodal image transcription for '{source_name}' ({mime_type})")
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        prompt = """
You are an expert multimodal OCR and visual diagram analysis engine.
Extract ALL visible text, labels, tables, numbers, charts, and structural details from this image.
If the image shows a chart, diagram, receipt, or document scan, summarize its structure and transcribe every readable detail accurately in Markdown.
"""
        response = client.models.generate_content(
            model=settings.DEFAULT_GEMINI_MODEL,
            contents=[part, prompt]
        )
        return response.text.strip() if response.text else ""


gemini_client = GeminiClient()
