import inspect
import json

import fastapi
import starlette
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from python_sri import FastAPISRI

app = fastapi.FastAPI()


client = TestClient(app)


def test_no_request_decorator() -> None:
    sri = FastAPISRI(domain="https://example.com/")
    route = "/decorator/no_request"
    in_html = "<div></div>"

    @app.get(route, response_class=HTMLResponse)
    @sri.html_uses_sri()
    def html() -> str:
        nonlocal in_html
        return in_html

    test_html = "<div></div>"
    response = client.get(route)
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html


def test_request_decorator() -> None:
    sri = FastAPISRI(domain="https://example.com/")
    route = "/decorator/request"
    in_html = "<div></div>"

    @app.get(route, response_class=HTMLResponse)
    @sri.html_uses_sri()
    def html(req: fastapi.Request) -> str:  # pylint: disable=unused-argument
        nonlocal in_html
        return in_html

    test_html = "<div></div>"
    response = client.get(route)
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html


def test_no_request_decorator_with_query_params() -> None:
    sri = FastAPISRI(domain="https://example.com/")
    route = "/decorator/no_request_query/{num}"
    in_html = "<div></div>"
    used_num = 5

    def html(num: int) -> str:
        nonlocal in_html
        nonlocal used_num
        assert used_num == num
        return in_html

    # Register manually as if it was a decorator
    new_html = app.get(route, response_class=HTMLResponse)(sri.html_uses_sri()(html))
    test_html = "<div></div>"
    response = client.get(route.replace("{num}", str(used_num)))
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html

    # Create test signature
    test_sig = inspect.Signature(
        parameters=(
            inspect.Parameter(
                "req",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=starlette.requests.Request,
            ),
            inspect.Parameter(
                "num",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=int,
            ),
        ),
        return_annotation=str,
    )

    anno = html.__annotations__
    anno["req"] = starlette.requests.Request
    assert anno == new_html.__annotations__
    assert test_sig == inspect.signature(new_html)


def test_no_annotations() -> None:
    sri = FastAPISRI(domain="https://example.com/")
    route = "/decorator/no_annotation"
    in_html = "<div></div>"

    @app.get(route, response_class=HTMLResponse)
    @sri.html_uses_sri()
    def html():  # type: ignore[no-untyped-def]
        nonlocal in_html
        return in_html

    test_html = "<div></div>"
    response = client.get(route)
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html
    assert not hasattr(html, "__annotations__") or getattr(
        html, "__annotations__", None
    ) in (None, {})


def test_api_response() -> None:
    sri = FastAPISRI(domain="https://example.com/")
    route = "/api/test"
    in_data = {"foo": "bar"}

    @app.get(route)
    @sri.html_uses_sri()
    def foo(req: fastapi.Request) -> dict[str, str]:  # pylint: disable=unused-argument
        nonlocal in_data
        return in_data

    test_html = "".join(json.dumps(in_data).split())
    response = client.get(route)
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html


def test_empty_domain() -> None:
    sri = FastAPISRI()
    route = "/domain"
    in_html = "<div></div>"

    @app.get(route, response_class=HTMLResponse)
    @sri.html_uses_sri()
    def html(req: fastapi.Request) -> str:  # pylint: disable=unused-argument
        nonlocal in_html
        return in_html

    test_html = "<div></div>"
    response = client.get(route)
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html


def test_hash_html() -> None:
    sri = FastAPISRI(domain="https://example.com/")
    route = "/hash_html"
    in_html = "<div></div>"

    @app.get(route, response_class=HTMLResponse)
    def html(req: fastapi.Request) -> str:  # pylint: disable=unused-argument
        nonlocal in_html
        nonlocal route
        nonlocal sri
        return sri.hash_html(route, in_html)

    test_html = "<div></div>"
    response = client.get(route)
    assert response.status_code == 200
    out_html = response.text
    assert test_html == out_html
