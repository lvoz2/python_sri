import flask
import pytest

from python_sri import FlaskSRI


def test_request_decorator_no_call() -> None:
    app = flask.Flask(__name__)
    app.testing = True
    client = app.test_client()
    sri = FlaskSRI(app, "https://example.com/")
    route = "/no_call"
    in_html = "<div></div>"
    test_html = in_html

    @app.get(route)
    @sri.html_uses_sri
    def html() -> str:
        nonlocal in_html
        return in_html

    res = client.get(route)
    assert test_html == res.text


def test_request_decorator_call() -> None:
    app = flask.Flask(__name__)
    app.testing = True
    client = app.test_client()
    sri = FlaskSRI(app, "https://example.com/")
    route = "/call"
    in_html = "<div></div>"
    test_html = in_html

    @app.get(route)
    @sri.html_uses_sri()
    def html() -> str:
        nonlocal in_html
        return in_html

    res = client.get(route)
    assert test_html == res.text


def test_invalid_decorator_arg_type() -> None:
    app = flask.Flask(__name__)
    app.testing = True
    sri = FlaskSRI(app, "https://example.com/")
    route = "/arg_type"
    in_html = "<div></div>"
    with pytest.raises(TypeError, match="Invalid argument type given"):

        @app.get(route)
        @sri.html_uses_sri(5)  # type: ignore[call-overload, misc]
        def html() -> str:
            nonlocal in_html
            return in_html


def test_hash_html() -> None:
    app = flask.Flask(__name__)
    app.testing = True
    client = app.test_client()
    sri = FlaskSRI(app, "https://example.com/")
    route = "/hash"
    in_html = "<div></div>"
    test_html = in_html

    @app.get(route)
    def html() -> str:
        nonlocal in_html
        nonlocal sri
        return sri.hash_html(in_html)

    res = client.get(route)
    assert test_html == res.text
