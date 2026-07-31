"""Entry point for running the Bonsai backend locally."""

import os

from app import create_app

test_mode = os.environ.get("BONSAI_TEST_MODE", "").lower() in ("1", "true", "yes")
# in_memory_db is deliberately not set here: even with mocked LLM calls,
# the dev server should always see your real, persistent data.
app = create_app(test=test_mode)

if __name__ == "__main__":
    # Defaults to loopback-only, matching Flask's own default. Docker Compose
    # sets this to 0.0.0.0, since binding to 127.0.0.1 inside a container
    # would be unreachable from the host despite the port mapping.
    host = os.environ.get("BONSAI_HOST", "127.0.0.1")
    app.run(debug=True, port=5000, host=host)
