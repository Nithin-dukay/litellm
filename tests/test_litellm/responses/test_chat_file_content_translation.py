from litellm.completion_extras.litellm_responses_transformation.transformation import (
    LiteLLMResponsesTransformationHandler,
)


def test_convert_chat_completion_messages_to_responses_api_maps_file_to_input_file():
    handler = LiteLLMResponsesTransformationHandler()

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What is the secret word in this PDF? Reply with just the word.",
                },
                {
                    "type": "file",
                    "file": {
                        "file_data": "data:application/pdf;base64,ZmFrZV9wZGY=",
                        "filename": "secret-word.pdf",
                    },
                },
            ],
        }
    ]

    input_items, instructions = handler.convert_chat_completion_messages_to_responses_api(
        messages
    )

    assert instructions is None
    assert len(input_items) == 1

    user_message = input_items[0]
    assert user_message["type"] == "message"
    assert user_message["role"] == "user"

    content = user_message["content"]
    assert content[0] == {
        "type": "input_text",
        "text": "What is the secret word in this PDF? Reply with just the word.",
    }
    assert content[1] == {
        "type": "input_file",
        "file_data": "data:application/pdf;base64,ZmFrZV9wZGY=",
        "filename": "secret-word.pdf",
    }

    assert content[1]["type"] != "input_text"
