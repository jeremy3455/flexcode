from unittest.mock import MagicMock, patch

import pytest

from conversational_agent.agent import Agent, AgentConfig


@pytest.fixture
def mock_openai():
    with patch("conversational_agent.agent.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_ask_normal_response(mock_openai):
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].message.content = "Respuesta normal"
    mock_chunk.choices[0].message.tool_calls = None
    mock_openai.chat.completions.create.return_value = mock_chunk

    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    reply = agent.ask("Hola")
    assert reply == "Respuesta normal"


def test_ask_explicit_search_command():
    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    with patch("conversational_agent.agent.web_search", return_value="Resultado de busqueda"):
        reply = agent.ask("/buscar inteligencia artificial")
    assert "inteligencia artificial" in reply
    assert "Resultado de busqueda" in reply


def test_ask_explicit_code_command():
    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    with patch("conversational_agent.agent.execute_python", return_value="42"):
        reply = agent.ask("/code print(21*2)")
    assert "42" in reply


def test_ask_explicit_image_command():
    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    with patch("conversational_agent.agent.generate_image", return_value="https://example.com/img.png"):
        reply = agent.ask("/imagen un gato")
    assert "https://example.com/img.png" in reply


def test_load_messages():
    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    messages = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola, ¿cómo estás?"},
    ]
    agent.load_messages(messages)
    assert len(agent.memory) == 2


def test_reset():
    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    agent.memory.add("user", "Hola")
    agent.reset()
    assert len(agent.memory) == 0


def test_tool_calling(mock_openai):
    first_chunk = MagicMock()
    first_chunk.choices = [MagicMock()]
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "calculate"
    tool_call.function.arguments = '{"expression": "2 + 2"}'
    first_chunk.choices[0].message.content = None
    first_chunk.choices[0].message.tool_calls = [tool_call]

    second_chunk = MagicMock()
    second_chunk.choices = [MagicMock()]
    second_chunk.choices[0].message.content = "El resultado es 4"
    second_chunk.choices[0].message.tool_calls = None

    mock_openai.chat.completions.create.side_effect = [first_chunk, second_chunk]

    agent = Agent(AgentConfig(api_key="fake", model="test-model"))
    with patch("conversational_agent.agent.calculate", return_value="4"):
        reply = agent.ask("Cuanto es 2+2?")
    assert "4" in reply or "El resultado es 4" in reply
