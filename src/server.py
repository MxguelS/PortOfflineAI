import json
import subprocess
import time
import urllib.error
import urllib.request

from src.config import PROJECT_ROOT


class LlamaServer:
    """Gestiona el proceso local de llama-server."""

    def __init__(self, config, runtime_path, model_path):
        self.config = config
        self.runtime_path = runtime_path
        self.model_path = model_path
        self.process = None

    def start(self):
        """Inicia llama-server."""
        host = self.config["runtime"]["host"]
        port = self.config["runtime"]["port"]

        command = [
            str(self.runtime_path),
            "-m",
            str(self.model_path),
            "--host",
            str(host),
            "--port",
            str(port),
            "--reasoning",
            "off",
            "--parallel",
            "1",
            "--ctx-size",
            "8192",
        ]

        self.process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def wait_until_ready(self, timeout=180):
        """Espera hasta que llama-server esté disponible."""
        host = self.config["runtime"]["host"]
        port = self.config["runtime"]["port"]

        health_url = f"http://{host}:{port}/health"
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.process is None:
                return False

            if self.process.poll() is not None:
                return False

            try:
                with urllib.request.urlopen(
                    health_url,
                    timeout=2,
                ) as response:
                    data = json.loads(
                        response.read().decode("utf-8")
                    )

                    if data.get("status") == "ok":
                        return True

            except (urllib.error.URLError, TimeoutError):
                pass

            time.sleep(1)

        return False

    def stop(self):
        """Detiene llama-server."""
        if self.process is None:
            return

        if self.process.poll() is not None:
            return

        self.process.terminate()

        try:
            self.process.wait(timeout=10)

        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()