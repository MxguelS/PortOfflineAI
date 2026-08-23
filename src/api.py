import json
import urllib.request


def send_message(config, messages):
    """Envía la conversación a la API local."""
    host = config["runtime"]["host"]
    port = config["runtime"]["port"]

    url = f"http://{host}:{port}/v1/chat/completions"

    payload = {
        "model": config["model"]["name"],
        "messages": messages,
        "max_tokens": 2048,
    }

    request_data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=180,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    message = result["choices"][0]["message"]["content"]

    usage = result.get("usage", {})
    timings = result.get("timings", {})

    metrics = {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get(
            "completion_tokens",
            0,
        ),
        "total_tokens": usage.get("total_tokens", 0),
        "tokens_per_second": timings.get(
            "predicted_per_second",
            0,
        ),
        "finish_reason": result["choices"][0].get(
            "finish_reason",
            "unknown",
        ),
    }

    return message, metrics