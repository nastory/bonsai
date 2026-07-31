"""Entry point for running the Bonsai backend locally."""

import os

from app import create_app

test_mode = os.environ.get("BONSAI_TEST_MODE", "").lower() in ("1", "true", "yes")
app = create_app(test=test_mode)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
