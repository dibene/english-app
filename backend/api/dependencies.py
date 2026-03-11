"""FastAPI dependency providers for the pronunciation analysis pipeline."""

import functools
import os

from core.services.pronunciation_service import PronunciationService
from core.services.text_comparison import TextComparisonEngine
from providers.azure_pronunciation import AzurePronunciationProvider
from providers.openai_llm import OpenAILLMProvider


@functools.lru_cache(maxsize=1)
def get_pronunciation_service() -> PronunciationService:
    """Build and cache a PronunciationService singleton wired from environment variables.

    Environment variables read:
        PRONUNCIATION_PROVIDER: Only "azure" is supported. Defaults to "azure".
        AZURE_SPEECH_KEY: Required when PRONUNCIATION_PROVIDER=azure.
        AZURE_SPEECH_REGION: Required when PRONUNCIATION_PROVIDER=azure.
        LLM_API_KEY: Required when ENABLE_LLM is true.
        LLM_MODEL: Chat model identifier. Defaults to "gemini-2.0-flash".
        LLM_BASE_URL: Optional base URL override for non-OpenAI providers.
        ENABLE_LLM: Set to "false" to skip LLM feedback. Defaults to "true".

    Raises:
        RuntimeError: If required environment variables are missing.
    """
    pronunciation_provider_name = os.getenv("PRONUNCIATION_PROVIDER", "azure").lower()
    if pronunciation_provider_name == "azure":
        key = os.getenv("AZURE_SPEECH_KEY", "")
        region = os.getenv("AZURE_SPEECH_REGION", "")
        if not key or not region:
            raise RuntimeError(
                "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set when "
                "PRONUNCIATION_PROVIDER=azure"
            )
        pronunciation_provider = AzurePronunciationProvider(key=key, region=region)
    else:
        raise RuntimeError(
            f"Unsupported PRONUNCIATION_PROVIDER: '{pronunciation_provider_name}'. "
            "Only 'azure' is supported in this version."
        )

    enable_llm = os.getenv("ENABLE_LLM", "true").lower() != "false"

    if enable_llm:
        llm_api_key = os.getenv("LLM_API_KEY", "")
        if not llm_api_key:
            raise RuntimeError(
                "LLM_API_KEY must be set when ENABLE_LLM is true. "
                "Set ENABLE_LLM=false to disable LLM feedback."
            )
        llm_model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
        llm_base_url = os.getenv("LLM_BASE_URL") or None
        llm_provider = OpenAILLMProvider(
            api_key=llm_api_key, model=llm_model, base_url=llm_base_url
        )
    else:
        # Build a stub that is never called (enable_llm=False bypasses the LLM call
        # in PronunciationService.analyze, so any non-None object is fine here).
        llm_api_key = os.getenv("LLM_API_KEY", "disabled")
        llm_model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
        llm_base_url = os.getenv("LLM_BASE_URL") or None
        llm_provider = OpenAILLMProvider(
            api_key=llm_api_key if llm_api_key else "disabled",
            model=llm_model,
            base_url=llm_base_url,
        )

    return PronunciationService(
        comparison_engine=TextComparisonEngine(),
        llm_provider=llm_provider,
        pronunciation_provider=pronunciation_provider,
        enable_llm=enable_llm,
    )
