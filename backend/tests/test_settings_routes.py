"""Tests for the /api/settings REST routes."""


def test_get_settings_creates_defaults_on_first_call(client, db) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    body = response.get_json()
    assert body["feedbackTone"] == "encouraging"
    assert body["thumbnailGenerationEnabled"] is True
    assert body["modelProvider"]["tier"] == "hosted"
    assert body["modelProvider"]["hasApiKey"] is False
    assert "apiKey" not in body["modelProvider"]


def test_put_settings_updates_provided_fields(client, db) -> None:
    response = client.put("/api/settings", json={"name": "Nigel Story", "feedbackTone": "straightforward"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Nigel Story"
    assert body["feedbackTone"] == "straightforward"


def test_put_settings_stores_api_key_but_never_returns_it(client, db) -> None:
    response = client.put(
        "/api/settings",
        json={"modelProvider": {"tier": "hosted", "hostedProvider": "anthropic", "apiKey": "sk-super-secret"}},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["modelProvider"]["hasApiKey"] is True
    assert "apiKey" not in body["modelProvider"]


def test_put_settings_partial_update_preserves_omitted_fields(client, db) -> None:
    client.put("/api/settings", json={"name": "Nigel Story"})

    response = client.put("/api/settings", json={"feedbackTone": "straightforward"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Nigel Story"
    assert body["feedbackTone"] == "straightforward"


def test_put_settings_partial_model_provider_update_preserves_stored_api_key(client, db) -> None:
    client.put(
        "/api/settings",
        json={"modelProvider": {"tier": "hosted", "hostedProvider": "anthropic", "apiKey": "sk-super-secret"}},
    )

    response = client.put("/api/settings", json={"modelProvider": {"tier": "byom"}})

    assert response.status_code == 200
    body = response.get_json()
    assert body["modelProvider"]["tier"] == "byom"
    assert body["modelProvider"]["hasApiKey"] is True


def test_put_settings_stores_byom_endpoint_and_model(client, db) -> None:
    response = client.put(
        "/api/settings",
        json={
            "modelProvider": {
                "tier": "byom",
                "byomEndpoint": "http://localhost:11434",
                "byomModel": "llama3",
            }
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["modelProvider"]["byomEndpoint"] == "http://localhost:11434"
    assert body["modelProvider"]["byomModel"] == "llama3"


def test_put_settings_stores_hosted_model(client, db) -> None:
    response = client.put(
        "/api/settings",
        json={"modelProvider": {"tier": "hosted", "hostedModel": "claude-3-5-sonnet-20241022"}},
    )

    assert response.status_code == 200
    assert response.get_json()["modelProvider"]["hostedModel"] == "claude-3-5-sonnet-20241022"


def test_put_settings_stores_embedding_model(client, db) -> None:
    response = client.put("/api/settings", json={"embeddingModel": "text-embedding-3-small"})

    assert response.status_code == 200
    assert response.get_json()["embeddingModel"] == "text-embedding-3-small"


def test_put_settings_partial_update_preserves_embedding_model(client, db) -> None:
    client.put("/api/settings", json={"embeddingModel": "text-embedding-3-small"})

    response = client.put("/api/settings", json={"name": "Nigel Story"})

    assert response.get_json()["embeddingModel"] == "text-embedding-3-small"


def test_put_settings_stores_tavily_key_but_never_returns_it(client, db) -> None:
    response = client.put("/api/settings", json={"tavilyApiKey": "tvly-super-secret"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["hasTavilyApiKey"] is True
    assert "tavilyApiKey" not in body


def test_put_settings_partial_update_preserves_tavily_key(client, db) -> None:
    client.put("/api/settings", json={"tavilyApiKey": "tvly-super-secret"})

    response = client.put("/api/settings", json={"name": "Nigel Story"})

    assert response.get_json()["hasTavilyApiKey"] is True


def test_get_settings_defaults_deep_search_to_false(client, db) -> None:
    response = client.get("/api/settings")

    assert response.get_json()["deepSearchEnabled"] is False


def test_put_settings_enables_deep_search(client, db) -> None:
    response = client.put("/api/settings", json={"deepSearchEnabled": True})

    assert response.status_code == 200
    assert response.get_json()["deepSearchEnabled"] is True


def test_put_settings_partial_update_preserves_deep_search_enabled(client, db) -> None:
    client.put("/api/settings", json={"deepSearchEnabled": True})

    response = client.put("/api/settings", json={"name": "Nigel Story"})

    assert response.get_json()["deepSearchEnabled"] is True
