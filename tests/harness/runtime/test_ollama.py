import httpx

from harness.runtime.base import RuntimeRequest
from harness.runtime.ollama import OllamaRuntime
from harness.schemas import FailureCategory


def _streaming_client(lines: list[str], status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            content=("\n".join(lines) + "\n").encode("utf-8"),
            request=request,
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stream_yields_normalized_chunks_and_metadata():
    client = _streaming_client(
        [
            '{"response":"안녕","done":false}',
            '{"response":"하세요","done":true,"total_duration":1000,"eval_count":2}',
        ]
    )
    runtime = OllamaRuntime(client=client)

    chunks = list(
        runtime.stream(RuntimeRequest(model_tag="local-model:latest", prompt="hello"))
    )

    assert [chunk.text for chunk in chunks] == ["안녕", "하세요"]
    assert chunks[-1].done is True
    assert chunks[-1].metadata["total_duration"] == 1000
    assert chunks[-1].metadata["eval_count"] == 2


def test_generate_records_ttft_latency_and_preserves_ollama_metadata():
    client = _streaming_client(
        [
            '{"response":"milestone","done":false}',
            (
                '{"response":" plan","done":true,'
                '"total_duration":2000000000,'
                '"load_duration":1000000,'
                '"prompt_eval_count":5,'
                '"prompt_eval_duration":500000000,'
                '"eval_count":10,'
                '"eval_duration":1000000000}'
            ),
        ]
    )
    runtime = OllamaRuntime(client=client)

    response = runtime.generate(
        RuntimeRequest(model_tag="local-model:latest", prompt="make a plan")
    )

    assert response.error is None
    assert response.text == "milestone plan"
    assert response.metrics.ttft_ms is not None
    assert response.metrics.latency_ms is not None
    assert response.metrics.tokens_per_second == 10.0
    assert response.metadata["total_duration"] == 2000000000
    assert response.metadata["load_duration"] == 1000000
    assert response.metadata["prompt_eval_count"] == 5
    assert response.metadata["prompt_eval_duration"] == 500000000
    assert response.metadata["eval_count"] == 10
    assert response.metadata["eval_duration"] == 1000000000


def test_generate_categorizes_timeout_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    runtime = OllamaRuntime(client=httpx.Client(transport=httpx.MockTransport(handler)))

    response = runtime.generate(
        RuntimeRequest(model_tag="local-model:latest", prompt="hello", timeout_seconds=1)
    )

    assert response.error is not None
    assert response.error.category == FailureCategory.TIMEOUT
    assert response.metrics.latency_ms is not None


def test_generate_categorizes_http_errors():
    client = _streaming_client(["server error"], status_code=500)
    runtime = OllamaRuntime(client=client)

    response = runtime.generate(
        RuntimeRequest(model_tag="local-model:latest", prompt="hello")
    )

    assert response.error is not None
    assert response.error.category == FailureCategory.EXTERNAL_DEPENDENCY


def test_generate_categorizes_missing_model_404():
    client = _streaming_client(["not found"], status_code=404)
    runtime = OllamaRuntime(client=client)

    response = runtime.generate(
        RuntimeRequest(model_tag="missing-model:latest", prompt="hello")
    )

    assert response.error is not None
    assert response.error.category == FailureCategory.MODEL_NOT_INSTALLED


def test_generate_categorizes_invalid_stream_json():
    client = _streaming_client(["not-json"])
    runtime = OllamaRuntime(client=client)

    response = runtime.generate(
        RuntimeRequest(model_tag="local-model:latest", prompt="hello")
    )

    assert response.error is not None
    assert response.error.category == FailureCategory.PARSER_ERROR

