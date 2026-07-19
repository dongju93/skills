# Intentionally vulnerable fixture for security-review evals. Do not deploy.
import subprocess
import sys


def ping_host(host: str) -> str:
    # User-controlled host is interpolated into a shell string.
    completed = subprocess.run(
        f"ping -c 1 {host}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout + completed.stderr


if __name__ == "__main__":
    print(ping_host(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"))
