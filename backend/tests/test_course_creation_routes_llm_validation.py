"""Route-level test: a malformed real LLM response should surface as a 502, not a 500 crash."""


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_create_course_returns_502_when_llm_output_is_invalid(real_llm_client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("not json at all"))

    response = real_llm_client.post("/api/courses", data={"message": "I want to learn GPU programming"})

    assert response.status_code == 502
