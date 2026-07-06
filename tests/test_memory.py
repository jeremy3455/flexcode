from conversational_agent.memory import ConversationMemory


def test_add_and_get_history():
    mem = ConversationMemory(max_messages=10)
    mem.add("user", "Hola")
    mem.add("assistant", "Hola, ¿cómo estás?")
    history = mem.get_history()
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hola"}
    assert history[1] == {"role": "assistant", "content": "Hola, ¿cómo estás?"}


def test_max_messages():
    mem = ConversationMemory(max_messages=3)
    for i in range(5):
        mem.add("user", str(i))
    assert len(mem) == 3
    history = mem.get_history()
    assert history[0]["content"] == "2"
    assert history[2]["content"] == "4"


def test_clear():
    mem = ConversationMemory(max_messages=10)
    mem.add("user", "msg1")
    mem.add("assistant", "msg2")
    mem.clear()
    assert len(mem) == 0
    assert mem.get_history() == []


def test_last():
    mem = ConversationMemory(max_messages=10)
    assert mem.last() is None
    mem.add("user", "ultimo mensaje")
    assert mem.last() is not None
    assert mem.last().role == "user"
    assert mem.last().content == "ultimo mensaje"


def test_len():
    mem = ConversationMemory(max_messages=10)
    assert len(mem) == 0
    mem.add("user", "a")
    assert len(mem) == 1
    mem.add("assistant", "b")
    assert len(mem) == 2
