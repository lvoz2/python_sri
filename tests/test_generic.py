from python_sri import GenericSRI


def test_decorator() -> None:
    sri = GenericSRI("https://example.com/")
    in_html = "<div></div>"
    test_html = "<div></div>"

    @sri.html_uses_sri("/")
    def html() -> str:
        nonlocal in_html
        return in_html

    out_html = html()
    assert test_html == out_html
