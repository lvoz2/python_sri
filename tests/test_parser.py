"""Test conformance of the parser to the HTML5 spec (only in no-quirks mode that is)"""

import pathlib

import pytest

from python_sri.parser import Element, HTMLWarning, Parser

parser = Parser()
pwd = pathlib.Path("tests") if pathlib.Path("tests").exists() else pathlib.Path(".")


# Below are test cases to test the Element class, where Parser does not interact with it
def test_get_attribute() -> None:
    e = Element("div", [("id", "foo")])
    assert e["id"] == "foo"


def test_set_attribute() -> None:
    e = Element("div")
    e["id"] = "foo"
    assert e["id"] == "foo"


def test_del_attribute() -> None:
    e = Element("div", [("id", "foo")])
    del e["id"]
    with pytest.raises(KeyError, match="^'id'$"):
        print(e["id"])


def test_contains_attribute() -> None:
    e = Element("div", [("id", "foo")])
    assert "id" in e


def test_get_quote_style() -> None:
    e = Element("div")
    assert e.quote == '"'


# Below are test cases to test various parts of the Parser class
def test_full_file_parse() -> None:
    with open(pwd / "static" / "index.html", "r", encoding="utf-8") as f:
        in_html = f.read()
    with open(pwd / "output" / "parser.html", "r", encoding="utf-8") as f:
        test_html = f.read()
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_invalid_decl_outside_foreign() -> None:
    in_html = "<![CDATA[<test>]]>"
    test_html = "<!--[CDATA[<test>]]-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_invalid_decl() -> None:
    in_html = "<!type html>"
    test_html = "<!--type html-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unfinished_html() -> None:
    in_html = ("<div>", "</div>")
    test_html = "<div></div>"
    parser.feed(in_html[0])
    parser.feed(in_html[1], False)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unmatched_xml_end_tag() -> None:
    in_html = '<svg><circle cx="50" cy="50" r="40"></svg>'
    with pytest.raises(
        ValueError,
        match="End tag does not match up with start tag inside foreign \\(XML\\) "
        + "content",
    ):
        parser.feed(in_html)


def test_unmatched_end_tag_at_finish() -> None:
    in_html = "<div></div></p>"
    test_html = "<div></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unmatched_end_tag() -> None:
    in_html = "<div></p></div>"
    test_html = "<div></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_no_identifier() -> None:
    in_html = "<!DOCTYPE html PUBLIC>"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_single_quote__for_identifier_string() -> None:
    in_html = "<!DOCTYPE html PUBLIC 'foo'>"
    test_html = "<!DOCTYPE html PUBLIC 'foo'>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_no_leading_quote_in_identifier_string() -> None:
    in_html = "<!DOCTYPE html PUBLIC foo'>"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_legacy_doctype() -> None:
    in_html = "<!DOCTYPE html SYSTEM 'about:legacy-compat'>"
    test_html = "<!DOCTYPE html SYSTEM 'about:legacy-compat'>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_single_quote_public_and_system_identifier() -> None:
    in_html = (
        "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN' 'http://www.w3.org/TR/xhtml1"
        + "/DTD/xhtml1-transitional.dtd'>"
    )
    test_html = (
        "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN' 'http://www.w3.org/TR/xhtml1"
        + "/DTD/xhtml1-transitional.dtd'>"
    )
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_invalid_char_quote_public_and_system_identifier() -> None:
    in_html = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" http://www.w3.org/TR/xhtml1'
        + "/DTD/xhtml1-transitional.dtd>"
    )
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_eof_in_unexpected_question_mark_instead_of_tag_name() -> None:
    in_html = "<?xml-stylesheet "
    test_html = "<!--?xml-stylesheet -->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_invalid_cdata_no_close_chars() -> None:
    in_html = "<![CDATA[<test>"
    test_html = "<!--[CDATA[<test>]]-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_invalid_cdata_one_close_char() -> None:
    in_html = "<![CDATA[<test>]"
    test_html = "<!--[CDATA[<test>]]-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_invalid_cdata_two_close_char() -> None:
    in_html = "<![CDATA[<test>]]"
    test_html = "<!--[CDATA[<test>]]-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_cdata_end_without_starting_cdata() -> None:
    # This is mostly for the alternative when using Python < 3.13 and a CDATA is found
    # Found CDATAs prevent following "]" or "]]" strings making their way into the tree
    in_html = "<div>]]</div>"
    test_html = "<div>]]</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


# The following are from the spec doc itself (Last checked 27/08/2025)
# https://html.spec.whatwg.org/multipage/parsing.html#parse-errors
def test_abrupt_closing_of_empty_comment() -> None:
    in_html = "<!-->"
    test_html = "<!---->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_abrupt_doctype_public_identifier() -> None:
    in_html = '<!DOCTYPE html PUBLIC "foo>'
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_abrupt_doctype_system_identifier() -> None:
    in_html = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "foo>'
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_absence_of_digits_in_numeric_character_reference_decimal() -> None:
    in_html = "<div>&#qux;</div>"
    test_html = "<div>&#qux;</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_absence_of_digits_in_numeric_character_reference_hex() -> None:
    in_html = "<div>&#xqux;</div>"
    test_html = "<div>&#xqux;</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_cdata_in_html_content() -> None:
    in_html = "<![CDATA[<test>]]>"
    test_html = "<!--[CDATA[<test>]]-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_cdata_in_xml() -> None:
    in_html = "<svg><![CDATA[<test>]]></svg>"
    test_html = "<svg><![CDATA[<test>]]></svg>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_character_reference_outside_unicode_range() -> None:
    in_html = "<div>&#x20ffff;</div>"
    test_html = "<div>&#xFFFD;</div>"
    with pytest.warns(
        UnicodeWarning,
        match="Character reference outside valid Unicode range. This has been replaced "
        + "with &#xFFFD; \\(case sensitive\\) in the output, as per spec",
    ):
        parser.feed(in_html)
        out_html = parser.stringify()
        assert test_html == out_html


def test_control_character_in_input_stream() -> None:
    in_html = "<div>\u0009</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert in_html == out_html


def test_control_character_reference() -> None:
    in_html = "<div>&#x0090;</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert in_html == out_html


def test_duplicate_attribute() -> None:
    in_html = '<div id="first" id="second"></div>'
    test_html = '<div id="first"></div>'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_end_tag_with_attributes() -> None:
    in_html = '<div></div id="first" id="second">'
    test_html = "<div></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_end_tag_with_trailing_solidus() -> None:
    in_html = "<div></div/>"
    test_html = "<div></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_before_start_tag_name() -> None:
    in_html = "<div></div><"
    test_html = "<div></div><"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_before_end_tag_name() -> None:
    in_html = "<div></div></"
    test_html = "<div></div></"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_cdata_no_close_chars() -> None:
    in_html = "<svg><![CDATA[<test>"
    test_html = "<svg><![CDATA[<test>]]>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_cdata_one_close_char() -> None:
    in_html = "<svg><![CDATA[<test>]"
    test_html = "<svg><![CDATA[<test>]]>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_cdata_two_close_char() -> None:
    in_html = "<svg><![CDATA[<test>]]"
    test_html = "<svg><![CDATA[<test>]]>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_comment() -> None:
    in_html = "<!-- test "
    test_html = "<!-- test -->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_comment_end_one_dash() -> None:
    in_html = "<!-- test -"
    test_html = "<!-- test --->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_comment_end_two_dash() -> None:
    in_html = "<!-- test --"
    test_html = "<!-- test ---->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_doctype() -> None:
    in_html = "<!DOCTYPE"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_eof_in_script_html_comment_like_text() -> None:
    in_html = "<script><!-- foo"
    test_html = "<script><!-- foo"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_eof_in_tag() -> None:
    in_html = "<div><div id="
    test_html = "<div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_incorrectly_closed_comment() -> None:
    in_html = "<div><!-- test --!></div>"
    test_html = "<div><!-- test --></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_incorrectly_opened_comment() -> None:
    in_html = "<!ELEMENT br EMPTY>"
    test_html = "<!--ELEMENT br EMPTY-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_invalid_character_sequence_after_doctype_name() -> None:
    in_html = "<!DOCTYPE html TEST>"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_invalid_first_character_of_tag_name() -> None:
    in_html = "<42></42>"
    test_html = "<42><!--42-->"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_attribute_value() -> None:
    in_html = "<div id=></div>"
    test_html = '<div id=""></div>'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_doctype_name() -> None:
    in_html = "<!doctype>"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_missing_doctype_public_identifier() -> None:
    in_html = "<!DOCTYPE html PUBLIC >"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_missing_doctype_system_identifier() -> None:
    in_html = "<!DOCTYPE html SYSTEM >"
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_missing_end_tag_name() -> None:
    in_html = "</>"
    test_html = ""
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_quote_before_doctype_public_identifier() -> None:
    in_html = '<!DOCTYPE html PUBLIC -//W3C//DTD HTML 4.01//EN">'
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_missing_quote_before_doctype_system_identifier() -> None:
    in_html = (
        "<!DOCTYPE html SYSTEM http://www.w3.org/TR/xhtml1/DTD/xhtml1-"
        + 'transitional.dtd">'
    )
    with pytest.raises(
        ValueError,
        match="Given HTML is not fully compliant with the current spec, and would "
        + "trigger quirks mode, which is not supported by python_sri's inbuilt parser",
    ):
        parser.feed(in_html)


def test_missing_semicolon_after_character_reference() -> None:
    in_html = "<div>&notin</div>"
    test_html = "<div>&not;in</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_whitespace_after_doctype_public_keyword() -> None:
    in_html = '<!DOCTYPE html PUBLIC"-//W3C//DTD HTML 4.01//EN">'
    test_html = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_whitespace_after_doctype_system_keyword() -> None:
    in_html = (
        '<!DOCTYPE html SYSTEM"http://www.w3.org/TR/xhtml1/DTD/xhtml1-'
        + 'transitional.dtd">'
    )
    test_html = (
        '<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-'
        + 'transitional.dtd">'
    )
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_whitespace_before_doctype_name() -> None:
    in_html = "<!DOCTYPEhtml><html></html>"
    test_html = "<!DOCTYPE html><html></html>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_whitespace_between_attributes() -> None:
    in_html = '<div id="foo"class="bar"></div>'
    test_html = '<div id="foo" class="bar"></div>'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_missing_whitespace_between_doctype_public_and_system_identifiers() -> None:
    in_html = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN""http://www.w3.org/TR/xhtml1/'
        + 'DTD/xhtml1-transitional.dtd">'
    )
    test_html = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/xhtml1'
        + '/DTD/xhtml1-transitional.dtd">'
    )
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_nested_comment() -> None:
    in_html = "<!-- <!-- nested --> --><!DOCTYPE html>"
    test_html = "<!-- <!-- nested --> --><!DOCTYPE html>"
    with pytest.raises(
        ValueError,
        match="Only whitespace and HTML comments are allowed before the DOCTYPE",
    ):
        parser.feed(in_html)
        out_html = parser.stringify()
        assert test_html == out_html


def test_noncharacter_character_reference() -> None:
    in_html = "<div>&#xfffff;</div>"
    test_html = "<div>&#xfffff;</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_noncharacter_in_input_stream() -> None:
    in_html = "<div>\U000fffff</div>"
    test_html = "<div>\U000fffff</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_non_void_html_element_start_tag_with_trailing_solidus() -> None:
    in_html = "<div/><span></span><span></span>"
    test_html = "<div><span></span><span></span></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_null_character_reference() -> None:
    in_html = "<div>&#x00;</div>"
    test_html = "<div>&#xFFFD;</div>"
    with pytest.warns(
        UnicodeWarning,
        match="Character reference is null \\(U\\+0000\\). This has been replaced "
        + "with &#xFFFD; \\(case sensitive\\) in the output, as per spec",
    ):
        parser.feed(in_html)
        out_html = parser.stringify()
        assert test_html == out_html


def test_surrogate_character_reference() -> None:
    in_html = "<div>&#xdca0;</div>"
    test_html = "<div>&#xFFFD;</div>"
    with pytest.warns(
        UnicodeWarning,
        match="Character reference is a surrogate. This has been replaced "
        + "with &#xFFFD; \\(case sensitive\\) in the output, as per spec",
    ):
        parser.feed(in_html)
        out_html = parser.stringify()
        assert test_html == out_html


def test_surrogate_in_input_stream() -> None:
    in_html = "<div>\udca0</div>"
    test_html = "<div>\udca0</div>"
    with pytest.warns(
        HTMLWarning,
        match="Surrogate character in given HTML, causing the spec defined surrogate-"
        + "in-input-stream parse error. This should not happen in normal usage",
    ):
        parser.feed(in_html)
        out_html = parser.stringify()
        assert test_html == out_html


def test_unexpected_character_after_doctype_system_identifier() -> None:
    in_html = (
        '<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-'
        + 'transitional.dtd" hello_world>'
    )
    test_html = (
        '<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-'
        + 'transitional.dtd">'
    )
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unexpected_character_in_attribute_name() -> None:
    in_html = "<div id'bar'></div>"
    test_html = "<div id'bar'=\"\"></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unexpected_character_in_unquoted_attribute_value() -> None:
    in_html = "<div foo=b'ar'></div>"
    test_html = "<div foo=\"b'ar'\"></div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unexpected_equals_sign_before_atrribute_name() -> None:
    in_html = '<div foo="bar" ="baz"></div>'
    test_html = '<div foo="bar" ="baz"=""></div>'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unexpected_null_character() -> None:
    in_html = "<div>\x00</div>"
    test_html = "<div>\x00</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unexpected_question_mark_instead_of_tag_name() -> None:
    in_html = '<?xml-stylesheet type="text/css" href="style.css"?>'
    test_html = '<!--?xml-stylesheet type="text/css" href="style.css"?-->'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unexpected_solidus_in_tag() -> None:
    in_html = '<div / id="foo"></div>'
    test_html = '<div id="foo"></div>'
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html


def test_unknown_named_character_reference() -> None:
    in_html = "<div>&hello;</div>"
    test_html = "<div>&amp;hello&semi;</div>"
    parser.feed(in_html)
    out_html = parser.stringify()
    assert test_html == out_html
