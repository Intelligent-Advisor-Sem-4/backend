from enum import Enum
import os
from typing import Optional


class LLMProvider(Enum):
    GEMINI = "gemini"
    WRITER = "writer"


class GeminiModel(Enum):
    FLASH_LITE = "gemini-2.0-flash-lite"
    FLASH = "gemini-1.5-flash"
    PRO = "gemini-2.0-pro"


class WriterModel(Enum):
    PALMYRA_FIN = "writer/palmyra-fin-70b-32k"


def _create_client(llm_provider: LLMProvider):
    """Create and return a client for the specified LLM provider"""
    if llm_provider == LLMProvider.GEMINI:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return genai.Client(api_key=api_key)


    elif llm_provider == LLMProvider.WRITER:
        from openai import OpenAI
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable not set")
        return OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")

    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")


def generate_content_with_llm(
        prompt: str,
        llm_provider: LLMProvider = LLMProvider.GEMINI,
        gemini_model: Optional[GeminiModel] = GeminiModel.FLASH_LITE,
        writer_model: Optional[WriterModel] = WriterModel.PALMYRA_FIN,
        temperature: float = 0.3,
        max_tokens: int = 1024,
):
    """Generate content using specified LLM provider

    Args:
        prompt: The text prompt to send to the model
        llm_provider: Which LLM provider to use
        gemini_model: Which Gemini model to use (if provider is GEMINI)
        writer_model: Which Writer model to use (if provider is WRITER)
        temperature: Controls randomness (0.0-1.0, lower is more deterministic)
        max_tokens: Maximum tokens in the response

    Returns:
        Generated text response
    """
    try:
        if llm_provider == LLMProvider.GEMINI:
            model_name = gemini_model.value if gemini_model else GeminiModel.FLASH_LITE.value
            model_client = _create_client(llm_provider)
            response = model_client.models.generate_content(model=model_name, contents=prompt)
            return response.text

        elif llm_provider == LLMProvider.WRITER:
            model_name = writer_model.value if writer_model else WriterModel.PALMYRA_FIN.value
            model_client = _create_client(llm_provider)
            response = model_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    except Exception as e:
        print(f"Error generating content with {llm_provider}: {e}")
        return None
