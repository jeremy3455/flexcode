from unittest.mock import MagicMock, patch

from conversational_agent.agent import Agent, AgentConfig


def test_generate_pdf_with_content_improvement():
    with patch("conversational_agent.agent.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client

        # First LLM call: returns tool_call for generate_pdf
        first = MagicMock()
        first.choices = [MagicMock()]
        tc = MagicMock()
        tc.id = "call_1"
        tc.function.name = "generate_pdf"
        tc.function.arguments = '{"title": "Reporte", "content": "genera un pdf"}'
        first.choices[0].message.content = None
        first.choices[0].message.tool_calls = [tc]

        # Second LLM call: _generate_doc_content generates proper content
        second = MagicMock()
        second.choices = [MagicMock()]
        second.choices[0].message.content = "Contenido profesional del reporte de ventas."
        second.choices[0].message.tool_calls = None

        # Third LLM call: final response after tool result
        third = MagicMock()
        third.choices = [MagicMock()]
        third.choices[0].message.content = (
            "PDF generado: [Reporte.pdf](/descargar/Reporte.pdf)"
        )
        third.choices[0].message.tool_calls = None

        client.chat.completions.create.side_effect = [first, second, third]

        agent = Agent(AgentConfig(api_key="fake", model="test"))
        reply = agent.ask("genera un pdf de un reporte de ventas")
        assert "Reporte.pdf" in reply
        assert client.chat.completions.create.call_count == 3


def test_explicit_pdf_without_content_generates_via_llm():
    with patch("conversational_agent.agent.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client

        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].message.content = (
            "Contenido del reporte generado por el LLM."
        )
        chunk.choices[0].message.tool_calls = None
        client.chat.completions.create.return_value = chunk

        agent = Agent(AgentConfig(api_key="fake", model="test"))
        reply = agent.ask("/pdf Reporte de ventas")
        assert "Reporte" in reply
