import re
from typing import List, Optional, Union

from httpx import Headers

from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues

from ..base_llm.chat.transformation import BaseLLMException

_DATA_URL_BASE64_PATTERN = re.compile(r"^(data:[^;]+;base64,)(.*)$", re.IGNORECASE)


def normalize_fireworks_base64_data_url(image_url: str) -> str:
    """
    Normalize base64 data URLs for Fireworks compatibility.

    - Leaves non-data URLs unchanged.
    - Converts URL-safe base64 chars to standard base64 chars.
    - Adds missing '=' padding when required.
    """
    match = _DATA_URL_BASE64_PATTERN.match(image_url)
    if not match:
        return image_url

    prefix, payload = match.groups()

    normalized_payload = payload.replace("-", "+").replace("_", "/")
    padding_needed = len(normalized_payload) % 4
    if padding_needed:
        normalized_payload += "=" * (4 - padding_needed)

    return f"{prefix}{normalized_payload}"


class FireworksAIException(BaseLLMException):
    pass


class FireworksAIMixin:
    """
    Common Base Config functions across Fireworks AI Endpoints
    """

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return FireworksAIException(
            status_code=status_code,
            message=error_message,
            headers=headers,
        )

    def _get_api_key(self, api_key: Optional[str]) -> Optional[str]:
        dynamic_api_key = api_key or (
            get_secret_str("FIREWORKS_API_KEY")
            or get_secret_str("FIREWORKS_AI_API_KEY")
            or get_secret_str("FIREWORKSAI_API_KEY")
            or get_secret_str("FIREWORKS_AI_TOKEN")
        )
        return dynamic_api_key

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        api_key = self._get_api_key(api_key)
        if api_key is None:
            raise ValueError("FIREWORKS_API_KEY is not set")

        return {"Authorization": "Bearer {}".format(api_key), **headers}
