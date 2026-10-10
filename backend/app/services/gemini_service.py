"""
ChemRAG — Gemini AI Service Integration
=========================================
Handles secure Gemini LLM synthesis using the Google Gen AI SDK.
Strictly respects grounding requirements, citation anchors [CIT-xxx],
chemical notation, and detailed error diagnostics.
"""

from __future__ import annotations

try:
    from google import genai
    from google.genai import errors
    GENAI_AVAILABLE = True
except (ImportError, Exception):
    genai = None
    errors = None
    GENAI_AVAILABLE = False

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class GeminiService:
    """
    Secure backend service wrapper for Google Gemini models.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logger
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> Optional[genai.Client]:
        """Lazy-initialize Google GenAI client if key is configured."""
        if not GENAI_AVAILABLE or genai is None:
            self.logger.warning("google-genai SDK is not installed or available in python environment.")
            return None

        if self._client is not None:
            return self._client

        api_key_secret = self.settings.llm.effective_api_key
        if not api_key_secret:
            self.logger.warning("Gemini API key is not configured in environment")
            return None

        key_value = api_key_secret.get_secret_value()
        if not key_value or not key_value.strip():
            return None

        try:
            self._client = genai.Client(api_key=key_value.strip())
            return self._client
        except Exception as exc:
            self.logger.error("Failed to initialize Google GenAI client", error=str(exc))
            return None

    def is_configured(self) -> bool:
        """Check if Gemini API key is configured without exposing secret values."""
        return self._get_client() is not None

    async def generate_grounded_answer(
        self,
        query: str,
        retrieved_passages: List[dict[str, Any]],
        chemical_metadata: List[dict[str, Any]],
        calculation_results: List[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Synthesize evidence-grounded answer using Gemini.

        Returns dict containing:
          - answer: str
          - model_used: str
          - status: 'success' | 'quota_exceeded' | 'auth_error' | 'model_error' | 'key_missing' | 'fallback'
          - error_detail: Optional[str]
        """
        client = self._get_client()
        model_name = self.settings.llm.effective_model

        if not client:
            return {
                "answer": None,
                "model_used": model_name,
                "status": "key_missing",
                "error_detail": "Gemini API key is missing or not configured in environment.",
            }

        # Build Context Prompt & System Instructions
        if retrieved_passages:
            context_lines: list[str] = ["### RETRIEVED SCIENTIFIC EVIDENCE:"]
            for p in retrieved_passages:
                cit_id = p.get("citation_id", "CIT-000")
                doc_id = str(p.get("document_id", ""))[:8]
                page = p.get("page_number", "N/A")
                content = p.get("content", "").strip()
                context_lines.append(f"- [{cit_id}] (Doc: {doc_id}, Page: {page}): {content}")

            if chemical_metadata:
                context_lines.append("\n### CHARACTERIZED CHEMICAL ENTITIES:")
                for chem in chemical_metadata:
                    context_lines.append(
                        f"- {chem.get('name')}: SMILES={chem.get('smiles')}, MW={chem.get('molecular_weight')}, Formula={chem.get('molecular_formula')}"
                    )

            if calculation_results:
                context_lines.append("\n### CALCULATED STOICHIOMETRIC RESULTS:")
                for calc in calculation_results:
                    context_lines.append(
                        f"- {calc.get('calculation_type')}: {calc.get('result_value')} {calc.get('units')} (Formula: {calc.get('formula_applied')})"
                    )

            context_str = "\n".join(context_lines)

            system_instruction = (
                "You are ChemRAG's Senior Chemical AI Research Assistant.\n"
                "Answer the scientific question using the provided evidence passages and chemical data.\n\n"
                "CRITICAL GROUNDED RESPONSE RULES:\n"
                "1. Synthesize a direct, precise scientific answer using the retrieved Context Passages.\n"
                "2. Cite evidence passages using in-text tags matching the exact citation identifiers, e.g. [CIT-001].\n"
                "3. Preserve scientific notation, chemical formulas (e.g. H₂SO₄, O₂), units (e.g. °C, K, g/mol), and experimental conditions.\n"
                "4. Where property extraction is requested, include a Markdown table with columns: Property | Extracted Value | Unit | Conditions | Source.\n"
            )
            user_prompt = f"{context_str}\n\n### USER RESEARCH QUESTION:\n{query}"
        else:
            system_instruction = (
                "You are ChemRAG's Senior Chemical AI Research Assistant.\n"
                "No matching document evidence was retrieved from the user's indexed corpus for this query.\n"
                "Answer the user's scientific research question accurately using general scientific knowledge.\n\n"
                "CRITICAL GENERAL KNOWLEDGE RULES:\n"
                "1. Begin your response with the exact heading:\n"
                "   ### General Knowledge — Not verified against your indexed documents\n"
                "2. Include this exact callout note at the top:\n"
                "   > 📌 **General Knowledge Answer**: No matching evidence was found in your indexed scientific documents for this query. The answer below is synthesized from general scientific literature.\n"
                "3. Provide a clear, accurate scientific answer including property values, units (e.g., °C, K, g/mol), standard conditions (e.g., 1 atm / 101.3 kPa), and relevant chemical context.\n"
                "4. Do NOT include any fake citation tags (such as [CIT-001]).\n"
            )
            user_prompt = f"### USER RESEARCH QUESTION:\n{query}"

        # Try candidate models if the default model fails with 404 or quota
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", model_name]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

        last_error = ""

        for current_model in candidate_models:
            try:
                self.logger.info("Executing Gemini API synthesis call", model=current_model)
                response = client.models.generate_content(
                    model=current_model,
                    contents=f"{system_instruction}\n\n{user_prompt}",
                )
                if response and response.text:
                    return {
                        "answer": response.text.strip(),
                        "model_used": current_model,
                        "status": "success",
                        "error_detail": None,
                    }
            except errors.APIError as err:
                last_error = str(err)
                code = getattr(err, "code", getattr(err, "status_code", 500))
                self.logger.warning("Gemini API error encountered", model=current_model, code=code, error=last_error[:200])

                if code == 429 or "RESOURCE_EXHAUSTED" in last_error or "quota" in last_error.lower():
                    self.logger.warning("Gemini API quota rate limit encountered, trying next candidate", model=current_model)
                    continue
                elif code == 401 or "UNAUTHENTICATED" in last_error:
                    self.logger.error("Gemini API authentication failed", model=current_model)
                    return {
                        "answer": None,
                        "model_used": current_model,
                        "status": "auth_error",
                        "error_detail": "Gemini API authentication failed. Please check the API key.",
                    }
                elif code in (404, 503) or "NOT_FOUND" in last_error or "UNAVAILABLE" in last_error or "capacity" in last_error.lower():
                    self.logger.warning("Gemini model unavailable or not found, trying next candidate", model=current_model)
                    continue
                else:
                    self.logger.error("Gemini API error", error=last_error, model=current_model)
                    continue
            except Exception as exc:
                last_error = str(exc)
                self.logger.error("Unexpected Gemini error", error=last_error, model=current_model)
                continue

        return {
            "answer": None,
            "model_used": model_name,
            "status": "model_error",
            "error_detail": f"Gemini API error: {last_error or 'Unable to generate response'}",
        }


# Singleton service instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
