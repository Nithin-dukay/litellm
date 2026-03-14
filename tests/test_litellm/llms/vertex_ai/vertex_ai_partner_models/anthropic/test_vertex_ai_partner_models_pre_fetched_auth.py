"""
Test that pre-fetched Authorization headers are respected for Vertex AI Partner Models (Claude).
Regression test for Issue #23572.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from litellm.llms.vertex_ai.vertex_ai_partner_models.main import (
    VertexAIPartnerModels,
)


def test_pre_fetched_auth_header_skips_ensure_access_token():
    """
    Test that when Authorization header is pre-provided via extra_headers,
    _ensure_access_token is NOT called (avoiding ADC requirement).
    """
    partner_models = VertexAIPartnerModels()

    # Mock dependencies
    mock_anthropic = MagicMock()
    mock_anthropic.completion.return_value = {"id": "test-response"}

    # Pre-fetched token
    pre_fetched_token = "Bearer ya29.custom-token-from-wif"
    headers = {"Authorization": pre_fetched_token}

    with patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.VertexLLM"
    ) as mock_vertex_llm_class, patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.AnthropicChatCompletion",
        return_value=mock_anthropic,
    ):
        mock_vertex_llm_instance = mock_vertex_llm_class.return_value
        mock_ensure_access_token = mock_vertex_llm_instance._ensure_access_token

        result = partner_models.completion(
            model="claude-3-5-sonnet-v2@20241022",
            messages=[{"role": "user", "content": "Hello"}],
            model_response=MagicMock(),
            print_verbose=MagicMock(),
            encoding=MagicMock(),
            logging_obj=MagicMock(),
            api_base="https://us-central1-aiplatform.googleapis.com/v1/projects/test-project/locations/us-central1/publishers/anthropic/models/claude-3-5-sonnet-v2@20241022",
            optional_params={},
            custom_prompt_dict={},
            headers=headers,
            timeout=60,
            litellm_params={},
            vertex_project="test-project",
            vertex_location="us-central1",
            vertex_credentials=None,
            acompletion=False,
            client=None,
        )

        # _ensure_access_token should NOT be called when Authorization is pre-provided
        mock_ensure_access_token.assert_not_called()

        # AnthropicChatCompletion should be called with the pre-fetched token
        mock_anthropic.completion.assert_called_once()
        call_kwargs = mock_anthropic.completion.call_args.kwargs

        # Verify the Authorization header was passed through
        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == pre_fetched_token


def test_pre_fetched_auth_header_not_overwritten_for_claude():
    """
    Test that pre-provided Authorization header is NOT overwritten
    when calling Claude models on Vertex AI.
    Regression test for Issue #23572.
    """
    partner_models = VertexAIPartnerModels()

    # Mock dependencies
    mock_anthropic = MagicMock()
    mock_anthropic.completion.return_value = {"id": "test-response"}

    # Pre-fetched token (e.g., from WIF)
    pre_fetched_token = "Bearer ya29.custom-wif-token"
    headers = {"Authorization": pre_fetched_token}

    with patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.VertexLLM"
    ) as mock_vertex_llm_class, patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.AnthropicChatCompletion",
        return_value=mock_anthropic,
    ):
        partner_models.completion(
            model="claude-3-5-sonnet-v2@20241022",
            messages=[{"role": "user", "content": "Hello"}],
            model_response=MagicMock(),
            print_verbose=MagicMock(),
            encoding=MagicMock(),
            logging_obj=MagicMock(),
            api_base="https://us-central1-aiplatform.googleapis.com/v1/projects/test-project/locations/us-central1/publishers/anthropic/models/claude-3-5-sonnet-v2@20241022",
            optional_params={},
            custom_prompt_dict={},
            headers=headers,
            timeout=60,
            litellm_params={},
            vertex_project="test-project",
            vertex_location="us-central1",
            vertex_credentials=None,
            acompletion=False,
            client=None,
        )

        # Verify the Authorization header was NOT overwritten
        mock_anthropic.completion.assert_called_once()
        call_kwargs = mock_anthropic.completion.call_args.kwargs

        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        # Should still be the pre-fetched token, NOT the ADC token
        assert call_kwargs["headers"]["Authorization"] == pre_fetched_token


def test_no_auth_header_calls_ensure_access_token():
    """
    Test that when NO Authorization header is provided,
    _ensure_access_token IS called (normal ADC flow).
    """
    partner_models = VertexAIPartnerModels()

    # Mock dependencies
    mock_anthropic = MagicMock()
    mock_anthropic.completion.return_value = {"id": "test-response"}

    with patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.VertexLLM"
    ) as mock_vertex_llm_class, patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.AnthropicChatCompletion",
        return_value=mock_anthropic,
    ):
        mock_vertex_llm_instance = mock_vertex_llm_class.return_value
        mock_vertex_llm_instance._ensure_access_token.return_value = (
            "adc-token",
            "test-project",
        )

        result = partner_models.completion(
            model="claude-3-5-sonnet-v2@20241022",
            messages=[{"role": "user", "content": "Hello"}],
            model_response=MagicMock(),
            print_verbose=MagicMock(),
            encoding=MagicMock(),
            logging_obj=MagicMock(),
            api_base="https://us-central1-aiplatform.googleapis.com/v1/projects/test-project/locations/us-central1/publishers/anthropic/models/claude-3-5-sonnet-v2@20241022",
            optional_params={},
            custom_prompt_dict={},
            headers=None,  # No pre-fetched token
            timeout=60,
            litellm_params={},
            vertex_project="test-project",
            vertex_location="us-central1",
            vertex_credentials=None,
            acompletion=False,
            client=None,
        )

        # _ensure_access_token SHOULD be called when no Authorization header
        mock_vertex_llm_instance._ensure_access_token.assert_called_once()

        # AnthropicChatCompletion should be called with the ADC token
        mock_anthropic.completion.assert_called_once()
        call_kwargs = mock_anthropic.completion.call_args.kwargs

        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer adc-token"


def test_openai_like_handler_with_pre_fetched_auth():
    """
    Test that pre-fetched Authorization headers work for OpenAI-like models
    (e.g., Llama on Vertex AI).
    """
    partner_models = VertexAIPartnerModels()

    # Mock dependencies
    mock_openai_handler = MagicMock()
    mock_openai_handler.completion.return_value = {"id": "test-response"}

    # Pre-fetched token
    pre_fetched_token = "Bearer ya29.custom-token"
    headers = {"Authorization": pre_fetched_token}

    with patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.VertexLLM"
    ) as mock_vertex_llm_class, patch(
        "litellm.llms.vertex_ai.vertex_ai_partner_models.main.base_llm_http_handler",
        mock_openai_handler,
    ):
        mock_vertex_llm_instance = mock_vertex_llm_class.return_value
        mock_ensure_access_token = mock_vertex_llm_instance._ensure_access_token

        result = partner_models.completion(
            model="meta/llama-3.1-405b-instruct-maas",
            messages=[{"role": "user", "content": "Hello"}],
            model_response=MagicMock(),
            print_verbose=MagicMock(),
            encoding=MagicMock(),
            logging_obj=MagicMock(),
            api_base="https://us-central1-aiplatform.googleapis.com/v1/projects/test-project/locations/us-central1/publishers/meta/models/llama-3.1-405b-instruct-maas",
            optional_params={},
            custom_prompt_dict={},
            headers=headers,
            timeout=60,
            litellm_params={},
            vertex_project="test-project",
            vertex_location="us-central1",
            vertex_credentials=None,
            acompletion=False,
            client=None,
        )

        # _ensure_access_token should NOT be called
        mock_ensure_access_token.assert_not_called()

        # OpenAI handler should be called with the pre-fetched token
        mock_openai_handler.completion.assert_called_once()
        call_kwargs = mock_openai_handler.completion.call_args.kwargs

        # Verify the api_key parameter contains the extracted token
        assert "api_key" in call_kwargs
        # The token is extracted (without "Bearer " prefix)
        assert call_kwargs["api_key"] == "ya29.custom-token"
