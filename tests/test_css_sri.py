"""Test SRI.hash_html with various arguments, where linked content is always CSS"""

import pathlib
import random
import string

from python_sri import SRI

test_domain = "http://127.0.0.1"
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


def test_preload() -> None:
    in_html = '<link rel="preload" as="style" integrity href="css/test.css">'
    test_html = (
        f'<link rel="preload" as="style" integrity="{css_sri}" href="css/test.css">'
    )
    out_html = run_sri(pwd / "static", "/", "SHA_256", in_html, "/index.html")
    assert out_html == test_html


def test_preload_and_self_close_spaces() -> None:
    in_html = (
        '<link rel="preload" as="script" integrity href="css/test.css"'
        + random_space()
        + "/"
        + random_space()
        + ">"
    )
    test_html = (
        f'<link rel="preload" as="script" integrity="{css_sri}" href="css/test.css">'
    )
    out_html = run_sri(pwd / "static", "/", "sHa-256", in_html, "/index.html")
    assert out_html == test_html


def test_bad_as_preload() -> None:
    in_html = '<link rel="preload" as="style" integrity href="css/test.css">'
    test_html = (
        f'<link rel="preload" as="style" integrity="{css_sri}" href="css/test.css">'
    )
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_root_relative_url() -> None:
    in_html = '<link rel="stylesheet" integrity href="/static/css/test.css">'
    test_html = (
        f'<link rel="stylesheet" integrity="{css_sri}" href="/static/css/test.css">'
    )
    out_html = run_sri(
        pwd / "static", "/static", "sha256", in_html, "/foo/bar/index.html"
    )
    assert out_html == test_html


def test_single_dot_url() -> None:
    in_html = '<link rel="stylesheet" integrity href="./css/test.css">'
    test_html = f'<link rel="stylesheet" integrity="{css_sri}" href="./css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_double_dot_url() -> None:
    in_html = '<link rel="stylesheet" integrity href="../css/test.css">'
    test_html = f'<link rel="stylesheet" integrity="{css_sri}" href="../css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/foo/index.html")
    assert out_html == test_html


def test_no_leading_dots_and_slashes() -> None:
    in_html = '<link rel="stylesheet" integrity href="css/test.css">'
    test_html = f'<link rel="stylesheet" integrity="{css_sri}" href="css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_http() -> None:
    in_html = '<link rel="stylesheet" integrity href="js/test.js">'
    test_html = (
        '<link rel="stylesheet" href="js/test.js" data-sri-error="An unknown error '
        + 'occured, or no static configuration found">'
    )
    sri = SRI(test_domain, hash_alg="sha256")
    out_html = sri.hash_html("/index.html", in_html)
    assert out_html == test_html


def test_no_integrity() -> None:
    in_html = '<link rel="stylesheet" href="css/test.css">'
    test_html = '<link rel="stylesheet" href="css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_random_integrity() -> None:
    in_html = (
        '<link rel="stylesheet" integrity="'
        + "".join(random.choices(string.printable.replace('"', ""), k=100))
        + '" href="css/test.css">'
    )
    test_html = f'<link rel="stylesheet" integrity="{css_sri}" href="css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_valid_integrity() -> None:
    in_html = '<link rel="stylesheet" integrity="{css_sri}" href="css/test.css">'
    test_html = f'<link rel="stylesheet" integrity="{css_sri}" href="css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_invalid_integrity() -> None:
    in_html = f'<link rel="stylesheet" integrity="{js_sri}" href="css/test.css">'
    test_html = f'<link rel="stylesheet" integrity="{js_sri}" href="css/test.css">'
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_local_404() -> None:
    in_html = '<link rel="stylesheet" integrity href="foo/bar.css">'
    test_html = (
        '<link rel="stylesheet" href="foo/bar.css" data-sri-error="File not found">'
    )
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_absolute() -> None:
    in_html = (
        '<link rel="stylesheet" integrity href="https://cdn.jsdelivr.net/npm/bootstrap@'
        + '5.3.7/dist/css/bootstrap.min.css">'
    )
    test_html = (
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist'
        + '/css/bootstrap.min.css" data-sri-error="python_sri does not currently support '
        + "the addition of SRI hashes to absolute URLs. If this resource is owned by "
        + 'the website, use a relative URL instead for SRI hashes">'
    )
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_src_instead_of_href() -> None:
    in_html = '<link rel="stylesheet" integrity src="css/test.css">'
    test_html = (
        '<link rel="stylesheet" src="css/test.css" data-sri-error="No URL to resource '
        + 'provided">'
    )
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_bad_static_url() -> None:
    in_html = '<link rel="stylesheet" integrity href="/css/test.css">'
    test_html = (
        '<link rel="stylesheet" href="/css/test.css" data-sri-error="Resource in URL '
        + 'not in configured static directory">'
    )
    out_html = run_sri(pwd / "static", "/static", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_unsupported_as_value() -> None:
    in_html = '<link rel="preload" as="font" integrity href="css/test.css">'
    test_html = (
        '<link rel="preload" as="font" href="css/test.css" data-sri-error="Integrity '
        + 'attribute not supported with <link rel="preload" as="font"> values">'
    )
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html


def test_decorator() -> None:
    inst = SRI(
        test_domain,
        static={"directory": pwd / "static", "url_path": "/static"},
    )
    in_html = f'<link integrity="{css_sri}" href="css/test.css">'
    test_html = f'<link integrity="{css_sri}" href="css/test.css">'

    @inst.html_uses_sri("/")
    def test() -> str:
        nonlocal in_html
        return in_html

    assert test_html == test()


def test_empty_src() -> None:
    in_html = '<link rel="stylesheet" integrity href="    ">'
    test_html = (
        '<link rel="stylesheet" href="    " data-sri-error="No URL found in href '
        + 'attribute">'
    )
    out_html = run_sri(pwd / "static", "/", "sha256", in_html, "/index.html")
    assert out_html == test_html
