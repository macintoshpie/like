__version__ = "0.1.0"

import os

from flask import Flask, g, jsonify

from like.views.utils import ErrorResponse


def init_app():
    # basic setup
    if not os.environ.get("SECRET_KEY"):
        raise Exception("Missing SECRET_KEY environment variable")
    app.secret_key = os.environ.get("SECRET_KEY")

    @app.errorhandler(ErrorResponse)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()


# template_folder = os.path.abspath('like/templates')
static_folder = os.path.abspath('like/static/build')
app = Flask(__name__, static_url_path='', static_folder=static_folder)
init_app()

import like.views.api  # noqa: F401
import like.views.app  # noqa: F401
