import json
import re
from typing import Any
from app.llm.base import LLMClient, LLMBadResponseError
from app.llm.schemas import ExtractionResult


def extract_json_from_text(text: str) -> str:
    """Extracts JSON string from text, stripping Markdown fences and surrounding commentary."""
    if not text or not text.strip():
        raise LLMBadResponseError("Received empty response from LLM")

    cleaned = text.strip()

    # 1. Strip Markdown code fences if present
    fence_pattern = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.MULTILINE)
    match = fence_pattern.search(cleaned)
    if match:
        cleaned = match.group(1).strip()

    # 2. If valid JSON direct parse works, return it
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    # 3. Find outermost curly braces if surrounded by commentary
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1].strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Return whatever was extracted or original cleaned text to let json.loads provide exact error
    return cleaned


def parse_extraction_response(raw_text: str) -> ExtractionResult:
    """Parses and validates LLM output into an ExtractionResult object."""
    json_str = extract_json_from_text(raw_text)
    try:
        data = json.loads(json_str)
    except Exception as e:
        raise LLMBadResponseError(f"JSON decode failed: {e}. Raw text: {raw_text[:200]!r}") from e

    try:
        return ExtractionResult.model_validate(data)
    except Exception as e:
        raise LLMBadResponseError(f"Schema validation failed: {e}. Parsed data: {data}") from e


async def extract_with_repair(
    llm_client: LLMClient,
    payload: dict[str, Any],
) -> tuple[ExtractionResult | None, str | None]:
    """Attempts extraction. If first attempt produces invalid JSON or schema, performs one repair attempt.
    Returns (result, None) on success, or (None, error_message) on complete failure.
    """
    first_response = ""
    try:
        first_response = await llm_client.extract(payload)
        return parse_extraction_response(first_response), None
    except Exception as first_error:
        # One repair retry attempt
        repair_payload = dict(payload)
        repair_payload["prompt"] = (
            f"Your previous JSON output was invalid and failed with error:\n"
            f"{str(first_error)}\n\n"
            f"Previous output was:\n{first_response}\n\n"
            f"Please output ONLY valid JSON adhering strictly to the extraction schema, with no markdown fences or commentary."
        )

        try:
            second_response = await llm_client.extract(repair_payload)
            return parse_extraction_response(second_response), None
        except Exception as second_error:
            # Safe failure containment: state remains completely untouched
            return None, f"Extraction failed after repair: {second_error}"
