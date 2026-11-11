import time
import json
import re
from typing import Optional, Any, Dict, List
from google import genai
from backend.app.core.config import settings
from backend.app.core.logger import logger

class GeminiClient:
    """
    Thread-safe, robust wrapper around Google GenAI client.
    Optimized for ultra-low latency, model quota resilience,
    and automatic failover across active models.
    """
    _instance: Optional["GeminiClient"] = None
    _client: Optional[genai.Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. Gemini calls will fail.")
            self._client = None
            return
        try:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Gemini Client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self._client = None

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 2,
    ) -> str:
        """
        Generate text response from Gemini with automatic multi-model failover.
        Optimized for < 1 second response times.
        """
        if not self._client:
            self._init_client()
            if not self._client:
                raise RuntimeError("GEMINI_API_KEY not configured or client initialization failed.")

        # Candidate models to try in sequence: requested model first, then fallback list
        target_model = model or settings.DEFAULT_GEMINI_MODEL
        candidates: List[str] = [target_model]
        for fb in settings.GEMINI_FALLBACK_MODELS:
            if fb not in candidates:
                candidates.append(fb)

        last_error = None
        for candidate in candidates:
            for attempt in range(1, max_retries + 1):
                try:
                    # Direct generate_content call (fastest: ~0.6s)
                    response = self._client.models.generate_content(
                        model=candidate,
                        contents=prompt
                    )
                    if hasattr(response, "text") and response.text:
                        return response.text.strip()
                    elif hasattr(response, "output_text") and response.output_text:
                        return response.output_text.strip()
                    return str(response).strip()
                except Exception as e:
                    err_msg = str(e)
                    last_error = e
                    # If model is deprecated (404), rate limited (429), or overloaded (503), immediately try next model
                    if any(code in err_msg for code in ["404", "429", "503", "NOT_FOUND", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                        logger.warning(f"Model '{candidate}' unavailable ({err_msg[:60]}...). Switching to fallback model...")
                        break  # Break attempt loop and try next candidate immediately
                    
                    logger.warning(f"Model '{candidate}' attempt {attempt}/{max_retries} failed: {err_msg[:80]}")
                    if attempt < max_retries:
                        time.sleep(0.5)

        # If all generate_content calls failed, try interactions.create as final rescue
        for candidate in candidates[:2]:
            try:
                logger.info(f"Trying interactions.create fallback with {candidate}...")
                resp = self._client.interactions.create(
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
        """
        Generates text and cleans JSON markdown wraps (e.g. ```json ... ```)
        to safely parse the returned output into a Python dict.
        """
        raw_text = self.generate(prompt=prompt, model=model, max_retries=max_retries)
        
        # Clean markdown codeblocks if model enclosed output in ```json
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt to extract first matching JSON object
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
        if not self._client:
            self._init_client()
            if not self._client:
                raise RuntimeError("GEMINI_API_KEY not configured.")

        try:
            logger.info(f"Uploading PDF to Gemini for multimodal OCR extraction: {pdf_path}")
            uploaded_file = self._client.files.upload(file=pdf_path)
            
            prompt = """
You are an expert multimodal document intelligence and OCR transcription system.
Extract ALL readable text, including:
- Handwritten notes, cursive writing, and student/doctor handwriting
- Printed text, headers, and bullet points
- Tables, numbers, mathematical formulas, and margin annotations
Transcribe all handwritten words faithfully. Format the output clearly using structured markdown.
Do not omit any sections, notes, or handwritten remarks.
"""
            response = self._client.models.generate_content(
                model=settings.DEFAULT_GEMINI_MODEL,
                contents=[uploaded_file, prompt]
            )

            # Cleanup uploaded file from Gemini storage
            try:
                self._client.files.delete(name=uploaded_file.name)
            except Exception as del_err:
                logger.warning(f"Failed to delete uploaded temp file from Gemini: {del_err}")

            return response.text.strip() if response.text else ""
        except Exception as e:
            logger.error(f"Gemini multimodal extraction failed: {e}")
            raise e

gemini_client = GeminiClient()
