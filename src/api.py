import json
import socket
import urllib.error
import urllib.request


REQUEST_TIMEOUT = 180


class APIError(Exception):
    """Error controlado al comunicarse con llama-server."""


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
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except (TimeoutError, socket.timeout) as error:
        raise APIError(
            "Model response timed out. "
            "Try reducing the active context."
        ) from error

    except urllib.error.HTTPError as error:
        raise APIError(
            f"llama-server returned HTTP {error.code}."
        ) from error

    except urllib.error.URLError as error:
        raise APIError(
            "Could not connect to llama-server."
        ) from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise APIError(
            "llama-server returned an invalid response."
        ) from error

    try:
        choice = result["choices"][0]

        message = choice["message"]["content"]

    except (KeyError, IndexError, TypeError) as error:
        raise APIError(
            "llama-server returned an unexpected response."
        ) from error

    usage = result.get("usage", {})
    timings = result.get("timings", {})

    metrics = {
        "prompt_tokens": usage.get(
            "prompt_tokens",
            0,
        ),
        "completion_tokens": usage.get(
            "completion_tokens",
            0,
        ),
        "total_tokens": usage.get(
            "total_tokens",
            0,
        ),
        "tokens_per_second": timings.get(
            "predicted_per_second",
            0,
        ),
        "finish_reason": choice.get(
            "finish_reason",
            "unknown",
        ),
    }

    return message, metrics