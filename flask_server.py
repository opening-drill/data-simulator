import os

from flask import Flask

app = Flask(__name__)


@app.get("/")
def index():
    return "ok", 200


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=False,
        use_reloader=False,
    )
