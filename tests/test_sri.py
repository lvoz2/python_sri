"""Test parts of the SRI class, irrespective of MIME type of any linked content in a
<link> or <script> tag if testing HTML
"""

import pathlib
import random
import ssl
import time
from typing import Any
from urllib import request

import pytest

from python_sri import SRI

test_domain = "https://lvoz2.github.io/"
css_sri = "sha256-dO7jYfk102fOhrUJM3ihI4I9y7drqDrJgzyrHgX1ChA="
js_sri = "sha256-rucZS1gOWuZjatfQlHrI22U0hXgbUKCCyH1W5+tUQh4="
pwd = pathlib.Path("tests") if pathlib.Path("tests").exists() else pathlib.Path(".")


def random_space() -> str:
    return " " * random.randrange(0, 10)


def run_sri(
    directory: str | pathlib.Path, base_path: str, alg: str, in_html: str, req_path: str
) -> str:
    sri = SRI(
        test_domain,
        static={"directory": directory, "url_path": base_path},
        hash_alg=alg,
    )
    return sri.hash_html(req_path, in_html)


def test_static_bad_type() -> None:
    with pytest.raises(TypeError):
        SRI("https://example.com", static="foo")  # type: ignore[arg-type]


def test_static_dir_str_does_not_exist() -> None:
    with pytest.raises(ValueError):
        SRI(
            "https://example.com",
            static={"url_path": "/", "directory": str(pwd / "static" / "foo")},
        )


def test_static_missing_dir() -> None:
    with pytest.raises(ValueError):
        SRI("https://example.com", static={"url_path": "/"})


def test_static_missing_url_path() -> None:
    with pytest.raises(ValueError):
        SRI("https://example.com", static={"directory": pwd / "static"})


def test_hash_alg_bad_value() -> None:
    with pytest.raises(ValueError):
        SRI("https://example.com", hash_alg="sha1")


def test_get_hash() -> None:
    sha256 = SRI("https://example.com", hash_alg="sha256").hash_alg == "sha256"
    sha384 = SRI("https://example.com", hash_alg="sha384").hash_alg == "sha384"
    sha512 = SRI("https://example.com", hash_alg="sha512").hash_alg == "sha512"
    assert all((sha256, sha384, sha512)) is True


def test_get_in_dev() -> None:
    true = SRI("https://example.com", hash_alg="sha256", in_dev=True).in_dev
    false = not SRI("https://example.com", hash_alg="sha256").in_dev
    assert all((true, false)) is True


def test_full_file_using_static() -> None:
    with open(pwd / "static" / "index.html", "r", encoding="utf-8") as f:
        in_html = f.read()
    with open(pwd / "sri_output" / "index.html", "r", encoding="utf-8") as f:
        test_html = f.read().strip()
    out_html = run_sri(pwd / "static", "/static", "sha384", in_html, "/index.html")
    assert out_html == test_html


def test_full_file_using_http() -> None:
    with open(pwd / "static" / "index.html", "r", encoding="utf-8") as f:
        in_html = f.read()
    with open(pwd / "sri_output" / "http.html", "r", encoding="utf-8") as f:
        test_html = f.read().strip()
    sri = SRI(test_domain, timeout=5, headers={}, context=ssl.create_default_context())
    out_html = sri.hash_html("/", in_html)
    assert out_html == test_html


def test_full_file_twice() -> None:
    with open(pwd / "static" / "index.html", "r", encoding="utf-8") as f:
        in_html = f.read()
    with open(pwd / "sri_output" / "index.html", "r", encoding="utf-8") as f:
        test_html = f.read().strip()
    sri = SRI(
        test_domain,
        static={"directory": pwd / "static", "url_path": "/static"},
        hash_alg="sha384",
    )
    sri.hash_html("/index.html", in_html)
    out_html = sri.hash_html("/index.html", in_html)
    assert out_html == test_html


def test_bad_html() -> None:
    in_html = "<html></body>"
    with pytest.raises(AssertionError):
        run_sri(pwd / "static", "/", "sha384", in_html, "/")


def test_empty_html() -> None:
    in_html = ""
    assert run_sri(pwd / "static", "/", "sha384", in_html, "/") == ""


def test_empty_cache() -> None:
    inst = SRI(
        test_domain,
        static={"directory": pwd / "static", "url_path": "/static"},
        in_dev=True,
    )
    in_html = f'<script integrity="{js_sri}" src="js/test.js">'
    for _ in range(100):
        inst.hash_html("/", in_html)
    assert (
        all(
            (
                inst.hash_file_path.cache_info().currsize == 0,  # pylint: disable=E1120
                inst.hash_file_object.cache_info().currsize  # pylint: disable=E1120
                == 0,
                inst.hash_url.cache_info().currsize == 0,  # pylint: disable=E1120
            )
        )
        is True
    )


def test_cache() -> None:
    inst = SRI(
        test_domain,
        static={"directory": pwd / "static", "url_path": "/static"},
        in_dev=False,
    )
    in_html = f'<script integrity="{js_sri}" src="js/test.js">'
    for _ in range(100):
        inst.hash_html("/", in_html)
    assert (
        all(
            (
                inst.hash_file_path.cache_info().currsize == 0,  # pylint: disable=E1120
                inst.hash_file_object.cache_info().currsize  # pylint: disable=E1120
                == 0,
                inst.hash_url.cache_info().currsize == 0,  # pylint: disable=E1120
            )
        )
        is True
    )


def test_multiple_decl() -> None:
    with pytest.warns(
        UserWarning, match="Multiple HTML declarations found, overriding"
    ):
        in_html = "<!DOCTYPE html><html><!doctype html></html>"
        test_html = "<!doctype html>\n<html></html>"
        out_html = run_sri(pwd / "static", "/", "sha384", in_html, "/")
        assert test_html == out_html


def test_file_path_str() -> None:
    path = str(pwd / "static" / "js" / "test.js")
    inst = SRI(test_domain, hash_alg="sha256")
    assert inst.hash_file_path(path) == js_sri


def test_file_path_str_404() -> None:
    path = str(pwd / "static" / "js" / "main.js")
    inst = SRI(test_domain, hash_alg="sha256")
    with pytest.raises(ValueError, match=f"File not found at path {path}"):
        inst.hash_file_path(path)


def test_http() -> None:
    inst = SRI(test_domain, hash_alg="sha256")
    assert inst.hash_url("/static/js/test.js", route="/") == js_sri


def test_hash_data() -> None:
    path = pwd / "static" / "js" / "test.js"
    inst = SRI(test_domain, hash_alg="sha256")
    with open(path, "rb") as f:
        assert inst.hash_data(f.read()) == js_sri


def test_file_object() -> None:
    path = pwd / "static" / "js" / "test.js"
    inst = SRI(test_domain, hash_alg="sha256")
    with open(path, "rb") as f:
        assert inst.hash_file_object(f) == js_sri


def test_bad_file_path() -> None:
    path = "https://example.com"
    inst = SRI(test_domain, hash_alg="sha256")
    with pytest.raises(TypeError):
        assert inst.hash_file_path(path)


def test_clear_file_path_str() -> None:
    path = str(pwd / "static" / "js" / "test.js")
    inst = SRI(test_domain, hash_alg="sha256")
    assert inst.hash_file_path(path, True) == js_sri


def test_clear_file_path_obj() -> None:
    path = pwd / "static" / "js" / "test.js"
    inst = SRI(test_domain, hash_alg="sha256")
    assert inst.hash_file_path(path, True) == js_sri


def test_clear_file_object() -> None:
    path = pwd / "static" / "js" / "test.js"
    inst = SRI(test_domain, hash_alg="sha256")
    with open(path, "rb") as f:
        assert inst.hash_file_object(f, True) == js_sri


def test_clear_url() -> None:
    inst = SRI(test_domain, hash_alg="sha256")
    assert inst.hash_url("/static/js/test.js", route="/", clear=True) == js_sri


def test_processing_instruction() -> None:
    in_html = "<div><?proc color='red'></div>"
    test_html = "<div><?proc color='red'></div>"
    out_html = run_sri(pwd / "static", "/", "sha384", in_html, "/")
    assert test_html == out_html


def test_not_https() -> None:
    in_html = '<link rel="stylesheet" href="/" integrity></link>'
    inst = SRI("http://neverssl.com/")
    with pytest.raises(ValueError, match="URL scheme/protocol must be HTTPS"):
        inst.hash_html("/", in_html)


def test_url_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_urlopen(*args: Any, **kwargs: Any) -> None:  # pylint: disable=W0613
        time.sleep(0.25)
        raise TimeoutError("timed out")

    monkeypatch.setattr(request, "urlopen", mock_urlopen)
    inst = SRI(test_domain)
    in_html = '<link rel="stylesheet" href="/" integrity></link>'
    test_html = '<link rel="stylesheet" href="/" data-sri-error="Timeout exceeded">'
    out_html = inst.hash_html("/", in_html)
    assert test_html == out_html


def test_bad_ssl() -> None:
    inst = SRI("https://wrong.host.badssl.com/")
    in_html = '<link rel="stylesheet" href="/" integrity></link>'
    test_html = (
        '<link rel="stylesheet" href="/" data-sri-error="Some other urllib error '
        + "occured. Reason: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify "
        + "failed: Hostname mismatch, certificate is not valid for 'wrong.host."
        + "badssl.com'. (_ssl.c:10"
    )
    end_test_html = ")\">"
    out_html = inst.hash_html("/", in_html)
    assert out_html.startswith(test_html) and out_html.endswith(end_test_html)


def test_missing_route() -> None:
    inst = SRI("https://example.com/")
    with pytest.raises(
        TypeError,
        match="Relative paths must include the route being used so that an absolute "
        + "URL can be constructed",
    ):
        inst.hash_url("/")


def test_bad_content_type() -> None:
    inst = SRI("https://lvoz2.github.io/python_sri/")
    in_html = '<link rel="stylesheet" href="/" integrity></link>'
    test_html = (
        '<link rel="stylesheet" href="/" data-sri-error="URL linked to in href/src '
        + 'attribute had an invalid Content-Type">'
    )
    out_html = inst.hash_html("/", in_html)
    assert test_html == out_html
