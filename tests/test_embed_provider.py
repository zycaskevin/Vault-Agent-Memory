"""Embedding provider telemetry and retry tests."""

from __future__ import annotations

import json
import urllib.error

import pytest


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_ollama_embedding_provider_records_batch_metrics(monkeypatch):
    from vault.embed import OllamaEmbeddingProvider

    calls = []

    def fake_urlopen(req, timeout):
        calls.append((req.full_url, timeout))
        return _FakeResponse({"embeddings": [[1.0, 0.0], [0.0, 1.0]]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaEmbeddingProvider(dim=None, max_retries=0)

    vectors = provider.encode(["alpha", "beta"])
    metrics = provider.get_metrics()

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert provider.dim == 2
    assert calls[0][0].endswith("/api/embed")
    assert metrics["encode_calls"] == 1
    assert metrics["encoded_texts"] == 2
    assert metrics["http_requests"] == 1
    assert metrics["http_retries"] == 0
    assert metrics["http_failures"] == 0
    assert metrics["last_latency_ms"] >= 0


def test_ollama_embedding_provider_retries_single_request(monkeypatch):
    from vault.embed import OllamaEmbeddingProvider

    attempts = {"count": 0}

    def fake_urlopen(req, timeout):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise urllib.error.URLError("temporary")
        return _FakeResponse({"embedding": [0.5, 0.5]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaEmbeddingProvider(dim=None, max_retries=1, retry_backoff=0)

    vectors = provider.encode("alpha")
    metrics = provider.get_metrics()

    assert vectors == [[0.5, 0.5]]
    assert provider.dim == 2
    assert metrics["encode_calls"] == 1
    assert metrics["encoded_texts"] == 1
    assert metrics["http_requests"] == 2
    assert metrics["http_retries"] == 1
    assert metrics["http_failures"] == 0


def test_ollama_embedding_provider_honors_retry_after(monkeypatch):
    from vault.embed import OllamaEmbeddingProvider

    attempts = {"count": 0}
    sleeps = []

    def fake_urlopen(req, timeout):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise urllib.error.HTTPError(
                req.full_url,
                429,
                "rate limited",
                {"Retry-After": "0.75"},
                None,
            )
        return _FakeResponse({"embedding": [0.25, 0.75]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", sleeps.append)
    provider = OllamaEmbeddingProvider(
        dim=None,
        max_retries=1,
        retry_backoff=0,
        max_retry_after=1.0,
    )

    vectors = provider.encode("alpha")
    metrics = provider.get_metrics()

    assert vectors == [[0.25, 0.75]]
    assert sleeps == [0.75]
    assert metrics["http_requests"] == 2
    assert metrics["http_retries"] == 1
    assert metrics["http_retry_after_delays"] == 1
    assert metrics["http_failures"] == 0


def test_embedding_provider_metrics_reset():
    from vault.embed import EmbeddingProvider

    provider = EmbeddingProvider(dim=3)
    provider._record_encode(2, 0)
    assert provider.get_metrics()["encode_calls"] == 1

    provider.reset_metrics()

    assert provider.get_metrics() == {
        "encode_calls": 0,
        "encoded_texts": 0,
        "http_requests": 0,
        "http_retries": 0,
        "http_retry_after_delays": 0,
        "http_failures": 0,
        "last_latency_ms": 0.0,
    }


def test_openai_embedding_provider_parses_indexed_response(monkeypatch):
    from vault.embed import OpenAIEmbeddingProvider

    calls = []

    def fake_urlopen(req, timeout):
        calls.append(
            {
                "url": req.full_url,
                "timeout": timeout,
                "auth": req.get_header("Authorization"),
                "payload": json.loads(req.data.decode()),
            }
        )
        return _FakeResponse(
            {
                "data": [
                    {"index": 1, "embedding": [0.0, 3.0, 4.0]},
                    {"index": 0, "embedding": [3.0, 4.0, 0.0]},
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAIEmbeddingProvider(
        model="text-embedding-3-small",
        credential="placeholder",
        base_url="https://example.test/v1",
        dim=3,
        max_retries=0,
    )

    vectors = provider.encode(["alpha", "beta"])

    assert vectors == [[0.6, 0.8, 0.0], [0.0, 0.6, 0.8]]
    assert provider.dim == 3
    assert provider.provider_id == "openai:https://example.test/v1:text-embedding-3-small:d3"
    assert calls[0]["url"] == "https://example.test/v1/embeddings"
    assert calls[0]["auth"] == "Bearer placeholder"
    assert calls[0]["payload"] == {
        "model": "text-embedding-3-small",
        "input": ["alpha", "beta"],
        "encoding_format": "float",
    }


def test_cohere_embedding_provider_parses_float_embeddings(monkeypatch):
    from vault.embed import CohereEmbeddingProvider

    calls = []

    def fake_urlopen(req, timeout):
        calls.append(
            {
                "url": req.full_url,
                "auth": req.get_header("Authorization"),
                "payload": json.loads(req.data.decode()),
            }
        )
        return _FakeResponse({"embeddings": {"float": [[5.0, 0.0], [0.0, 12.0]]}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = CohereEmbeddingProvider(
        model="embed-v4.0",
        credential="placeholder",
        base_url="https://cohere.test/v2",
        input_type="search_query",
        dim=2,
        max_retries=0,
    )

    vectors = provider.encode(["alpha", "beta"])

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert provider.provider_id == "cohere:https://cohere.test/v2:embed-v4.0:search_query:d2"
    assert calls[0]["url"] == "https://cohere.test/v2/embed"
    assert calls[0]["auth"] == "Bearer placeholder"
    assert calls[0]["payload"] == {
        "model": "embed-v4.0",
        "texts": ["alpha", "beta"],
        "input_type": "search_query",
        "embedding_types": ["float"],
        "output_dimension": 2,
    }


def test_voyage_embedding_provider_parses_indexed_response(monkeypatch):
    from vault.embed import VoyageEmbeddingProvider

    calls = []

    def fake_urlopen(req, timeout):
        calls.append(
            {
                "url": req.full_url,
                "auth": req.get_header("Authorization"),
                "payload": json.loads(req.data.decode()),
            }
        )
        return _FakeResponse(
            {
                "data": [
                    {"index": 1, "embedding": [0.0, 8.0, 6.0]},
                    {"index": 0, "embedding": [6.0, 8.0, 0.0]},
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = VoyageEmbeddingProvider(
        model="voyage-3.5",
        credential="placeholder",
        base_url="https://voyage.test/v1",
        input_type="query",
        dim=3,
        max_retries=0,
    )

    vectors = provider.encode(["alpha", "beta"])

    assert vectors == [[0.6, 0.8, 0.0], [0.0, 0.8, 0.6]]
    assert provider.provider_id == "voyage:https://voyage.test/v1:voyage-3.5:query:d3"
    assert calls[0]["url"] == "https://voyage.test/v1/embeddings"
    assert calls[0]["auth"] == "Bearer placeholder"
    assert calls[0]["payload"] == {
        "model": "voyage-3.5",
        "input": ["alpha", "beta"],
        "input_type": "query",
        "output_dtype": "float",
        "output_dimension": 3,
    }


@pytest.mark.parametrize(
    ("provider_name", "env_name", "expected_model"),
    [
        ("openai", "OPENAI_API_KEY", "text-embedding-3-small"),
        ("cohere", "COHERE_API_KEY", "embed-v4.0"),
        ("voyage", "VOYAGE_API_KEY", "voyage-3.5"),
    ],
)
def test_create_embedding_provider_api_defaults(monkeypatch, provider_name, env_name, expected_model):
    from vault.embed import create_embedding_provider

    monkeypatch.setenv(env_name, "test-key")
    provider = create_embedding_provider(provider=provider_name, model_key="mix")

    assert provider.model == expected_model
    assert provider.is_semantic is True
    assert provider.provider_id.startswith(f"{provider_name}:")


@pytest.mark.parametrize(
    ("provider_cls", "provider_name", "env_name"),
    [
        ("OpenAIEmbeddingProvider", "openai", "OPENAI_API_KEY"),
        ("CohereEmbeddingProvider", "cohere", "COHERE_API_KEY"),
        ("VoyageEmbeddingProvider", "voyage", "VOYAGE_API_KEY"),
    ],
)
def test_api_embedding_provider_missing_key_fails_closed(monkeypatch, provider_cls, provider_name, env_name):
    import vault.embed as embed

    monkeypatch.delenv(env_name, raising=False)
    provider = getattr(embed, provider_cls)(credential="")

    with pytest.raises(RuntimeError, match=f"{env_name} is required"):
        provider.encode("alpha")
