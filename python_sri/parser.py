"""Classes to parse a HTML document, so we can find HTML tags to create SRI hashes for

Classes:
All classes have a stringify() method, which converts the class to a string for
    conversion to HTML

Special: Base class for non-tag classes
Comment: HTML Comments, like <!-- comment -->
Declaration: HTML Declarations, like <!doctype html>
ProcessingInstruction: HTML Processing Instructions, like <? instruction >
UnknownDecl: Unknown HTML Declarations, like CDATA etc

Tag: Base class for HTML opening and closing tags. Holds the element name
Element: A HTML opening tag. Holds element info, such as the attributes
EndTag: A HTML closing tag. Stores a reference to its corresponding opener (an Element)

Parser: A subclass of html.parser.HTMLParser, which performs the actual parsing and
    starts the stringification to convert back to HTML
"""

from __future__ import annotations

import collections
import re
import warnings
from html import entities
from html.parser import HTMLParser
from typing import Literal, Optional

__all__ = ["Element", "HTMLWarning", "Parser"]


# Base class for warnings about bad HTML
class HTMLWarning(UserWarning):
    pass


# Base class for not text or Element HTML content
class Special:
    """Base class for non-tag HTML classes

    Parameters and Properties:
    prefix: The prefix, ie the !-- in a comment or the ! in a declaration
    content: The actual data in the class
    suffix: The suffix, if required, ie the -- at the end of a comment or the ] after an
        unknown declaration
    """

    __slots__ = ("prefix", "content", "suffix")

    def __init__(self, prefix: str, content: str, suffix: str = "") -> None:
        self.prefix = prefix
        self.content = content
        self.suffix = suffix

    def stringify(self) -> str:
        return f"<{self.prefix}{self.content}{self.suffix}>"

    def __repr__(self) -> str:
        return self.stringify()


class Comment(Special):
    """A HTML Comment, as a class"""

    __slots__ = ()

    def __init__(self, content: str) -> None:
        super().__init__("!--", content, "--")


class Declaration(Special):
    """A HTML Declaration, as a class"""

    __slots__ = ()

    def __init__(self, content: str) -> None:
        super().__init__("!", content)


class UnknownDecl(Special):
    """An unknown HTML Declaration, as a class"""

    __slots__ = ()

    def __init__(self, content: str) -> None:
        super().__init__("![", content, "]")


class Tag:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def stringify(self) -> str:
        return f"<{self.name}>"

    def __repr__(self) -> str:
        return self.stringify()


class Element(Tag):
    """A HTML Element

    Parameters:
    name: The name of the element (eg: html for <html> tags)
    text: The original textual representation of the Element (eg <html> for <html> tags)
    attrs: An optional list of tuples representing the attributes of the Element
    void: Whether the Element is a void element. A void element is an element that does
        not require a closing tag (like <link> or <meta>)

    Properties:
    void: The same as the void parameter
    children: A list of more Elements or non-tags (Special) or strings (data in an
        element) that are children of this Element
    """

    __slots__ = (
        "__attrs",
        "__attrs_changed",
        "void",
        "__quote",
        "__self_closing",
        "children",
    )

    def __init__(
        self,
        name: str,
        attrs: Optional[list[tuple[str, Optional[str]]]] = None,
        void: bool = False,
        quote: Optional[str] = None,
    ) -> None:
        super().__init__(name)
        deduped_attrs = {}
        if attrs is not None:
            for attr in attrs:
                if attr[0] not in deduped_attrs:
                    deduped_attrs[attr[0]] = attr[1]
        self.__attrs: dict[str, Optional[str]] = deduped_attrs
        self.__attrs_changed: set[str] = set()
        self.void = void
        self.__quote = '"' if quote is None or len(quote) == 0 else quote
        self.__self_closing = False
        self.children: list[Element | Special | str] = []

    def __getitem__(self, attr: str) -> Optional[str]:
        return self.__attrs[attr]

    def __setitem__(self, attr: str, value: str) -> None:
        self.__attrs[attr] = value
        self.__attrs_changed.add(attr)

    def __delitem__(self, attr: str) -> None:
        self.__attrs_changed.add(attr)
        del self.__attrs[attr]

    def __contains__(self, attr: str) -> bool:
        return attr in self.__attrs

    @property
    def quote(self) -> str:
        return self.__quote

    @property
    def xml_self_closing(self) -> bool:  # pragma: no cover # This is not used at all
        # but it is necessary for the following setter
        return self.__self_closing

    # This setter only enables self_closing, no matter what, essentially locking that
    # property to True after an attempt to set it
    @xml_self_closing.setter
    def xml_self_closing(self, new: bool) -> None:  # pylint: disable=unused-argument
        self.__self_closing = True

    def append(self, child: Element | Special | str, add_to_str: bool = False) -> None:
        if (
            add_to_str
            and len(self.children) > 0
            and isinstance(self.children[-1], str)
            and isinstance(child, str)
        ):
            self.children[-1] += child
        else:
            self.children.append(child)

    def stringify(self) -> str:
        attrs = self.__attrs
        new_attrs: list[str] = []
        for attr, value in attrs.items():
            new_attrs.append(
                attr
                + "="
                + self.__quote
                + ("" if value is None else value)
                + self.__quote
            )
        start_tag: str = (
            ("<" + self.name)
            + ("" if len(new_attrs) == 0 else " " + " ".join(new_attrs))
            + ((" /" if self.__self_closing else "") + ">")
        )
        return start_tag


class EndTag(Tag):

    __slots__ = ("start_tag",)

    def __init__(self, name: str, start_tag: Element) -> None:
        super().__init__(f"/{name}")
        self.start_tag = start_tag


class Parser(HTMLParser):
    """A HTML Parser, that converts between a HTML string and a tree representation

    Properties:
    sri_tags: A list of Elements, where each Element is either a link or script, and has
        an integrity attribute. Used later to compute SRI hashes
    """

    __slots__ = (
        "__tag_stack",
        "__flat_tree",
        "sri_tags",
        "__in_xml",
        "__quote",
        "__foreign_content_start_tags",
        "__seen_content_before_preamble",
        "__unicode_range",
        "__seen_preamble",
        "__control_chars",
        "__non_chars",
        "__surrogates",
        "__bad_self_closing",
    )

    def __init__(self, quote: Optional[str] = None) -> None:
        super().__init__(convert_charrefs=False)
        self.rawdata = ""
        self.__quote = "" if quote is None else quote
        self.__tag_stack: collections.deque[Element] = collections.deque()
        self.__flat_tree: collections.deque[Element | EndTag | Special | str] = (
            collections.deque()
        )
        self.sri_tags: list[Element] = []
        self.__in_xml = False
        # Finds primarily the element/attribute names in a foreign content (XML) block.
        # Uses this spec: (next line)
        # https://www.w3.org/TR/REC-xml/#NT-Name for definition. Only used inside XML
        self.__bits_regex = re.compile(
            "([:A-Z_a-z\xc0-\xd6\xd8-\xf6\u00f8-\u02ff\u0370-\u037d\u037f-\u1fff\u200c"
            + "-\u200d\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd"
            + "\U00010000-\U000effff][:A-Z_a-z\xc0-\xd6\xd8-\xf6\u00f8-\u02ff\u0370-"
            + "\u037d\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff"
            + "\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000effff-.0-9\xb7\u0300-\u036f"
            + "\u203f-\u2040]*)(=((['\"].+?['\"])|(.+?)))?"
        )
        # Allowed quote marks surrounding attribute values
        self.__quotes: tuple[str, str] = ('"', "'")
        self.__foreign_content_start_tags: tuple[str, str] = ("svg", "math")
        self.__seen_content_before_preamble: bool = False
        self.__unicode_range: tuple[int, int] = (0x0, 0x10FFFF)
        self.__seen_preamble = False
        # self.__non_chars = re.compile(
        # "[\ufdd0-\ufdef\ufffe\uffff\U0001fffe\U0001ffff\U0002fffe\U0002ffff"
        # + "\U0003fffe\U0003ffff\U0004fffe\U0004ffff\U0005fffe\U0005ffff\U0006fffe"
        # + "\U0006ffff\U0007fffe\U0007ffff\U0008fffe\U0008ffff\U0009fffe\U0009ffff"
        # + "\U000afffe\U000affff\U000bfffe\U000bffff\U000cfffe\U000cffff\U000dfffe"
        # + "\U000dffff\U000efffe\U000effff\U000ffffe\U000fffff\U0010fffe\U0010ffff]"
        # )
        self.__surrogates = re.compile("[\ud800-\udbff\udc00-\udfff]")
        self.__surrogate_range = ((0xD800, 0xDBFF), (0xDC00, 0xDFFF))
        self.__bad_self_closing: collections.deque[
            tuple[Element, Optional[Element]]
        ] = collections.deque()

    def reset(self) -> None:
        super().reset()
        if hasattr(self, "sri_tags"):
            self.__tag_stack.clear()
            self.__flat_tree.clear()
            self.sri_tags = []
            self.__in_xml = False
            self.__seen_content_before_preamble = False
            self.__seen_preamble = False
            self.__bad_self_closing.clear()

    def stringify(self) -> str:
        """Converts the HTML tree into a HTML string

        returns: HTML, as a string
        """
        html: str = ""
        tag_stack: collections.deque[Element] = collections.deque()
        for node in self.__flat_tree:
            if isinstance(node, Element):
                if not node.void:
                    tag_stack.append(node)
            elif isinstance(node, EndTag):
                tag_stack.pop()
            html += str(node)
        return html

    def __is_void(self, name: str) -> bool:
        return name in [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "keygen",
            "link",
            "menuitem",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
            # From bs4 source, these aren't HTML5 but still treat differently
            "basefont",
            "bgsound",
            "command",
            "frame",
            "image",
            "isindex",
            "nextid",
            "spacer",
        ]

    def __quirks(self) -> None:
        # if self.__seen_preamble:
        raise ValueError(
            "Given HTML is not fully compliant with the current spec, and would "
            + "trigger quirks mode, which is not supported by python_sri's inbuilt "
            + "parser"
        )

    # Below this comment are functions for building the HTML tree
    # First we override feed as we only will ever parse full sections (if run from
    # sri.SRI). We also reset the state of parser for a clean slate per run (if clean)
    # If not clean, then feed behaves the same as the underlying implementation, which
    # is html.parser.HTMLParser.feed(html)
    def feed(self, data: str, clean: bool = True) -> None:
        if re.search(self.__surrogates, data) is not None:
            warnings.warn(
                "Surrogate character in given HTML, causing the spec defined surrogate-"
                + "in-input-stream parse error. This should not happen in normal usage",
                category=HTMLWarning,
            )
        if clean:
            self.reset()
            self.rawdata = data
            self.goahead(True)
        else:
            self.rawdata += data
            self.goahead(False)
        self.__bad_self_closing.reverse()
        for bad_closing, _ in self.__bad_self_closing:
            self.__flat_tree.append(EndTag(bad_closing.name, bad_closing))
        self.__bad_self_closing.clear()
        if len(self.rawdata.strip()) > 0:
            self.__add_to_tree(self.rawdata, True)

    def __start_tag(
        self, name: str, attrs: list[tuple[str, Optional[str]]], self_closing: bool
    ) -> None:
        """Actual handler for start tags and self closing start tags"""
        self.__seen_content_before_preamble = True
        if name in self.__foreign_content_start_tags:
            self.__in_xml = True
        text: Optional[str] = self.get_starttag_text()
        if self.__in_xml and text is not None:
            # Attempt to parse a start tag case sensitive
            bits = list(
                re.finditer(self.__bits_regex, text.strip().strip("<>/").strip())
            )
            name = bits[0].group(0)
            if len(bits) >= 2:
                for i, attr_in_bits in enumerate(bits[1:]):
                    key, value = tuple(attr_in_bits.group(0).split("="))
                    attrs[i] = (key, attrs[i][1])
                    if (
                        len(self.__quote) == 0
                        and len(value) > 0
                        and value[0] in self.__quotes
                    ):
                        self.__quote = value[0]
        # Void elements don't require closing tags
        void: bool = self.__is_void(name)
        tag = Element(name, attrs, void, self.__quote)
        if not void and self_closing and not self.__in_xml:
            self.__bad_self_closing.append(
                (tag, None if len(self.__tag_stack) == 0 else self.__tag_stack[-1])
            )
        if self.__in_xml and self_closing:
            # XML allows self closing tags, so we will set the element to self closing
            tag.xml_self_closing = True
        self.__flat_tree.append(tag)
        if not (void or self_closing):
            self.__tag_stack.append(tag)
        if tag.name not in ["script", "link"]:
            return
        for attr, _ in attrs:
            if attr == "integrity":
                self.sri_tags.append(tag)

    def __add_to_tree(self, data: Special | str, add_to_str: bool = False) -> None:
        """Adds a non-element to the tree. As non elements will never be edited, some
        can be added into the last element if that element is a string (ie put a
        comment into some data that will not be displayed anyway)
        """
        if isinstance(data, Declaration):
            self.__flat_tree.append(data)
            return
        if not (
            isinstance(data, Comment) or (isinstance(data, str) and data.isspace())
        ):
            self.__seen_content_before_preamble = True
        if len(self.__tag_stack) > 0:
            self.__tag_stack[-1].append(data, add_to_str)
        if (
            add_to_str
            and len(self.__flat_tree) > 0
            and isinstance(self.__flat_tree[-1], str)
            and isinstance(data, str)
        ):
            self.__flat_tree[-1] += data
        else:
            self.__flat_tree.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self.__start_tag(tag, attrs, False)

    def handle_endtag(self, tag: str) -> None:
        if self.__in_xml:
            # Attempt to parse an end tag case sensitive
            # Make attrs mutable
            start_name: str = self.__tag_stack[-1].name
            if tag == start_name.casefold():
                name = start_name
            else:
                raise ValueError(
                    "End tag does not match up with start tag inside foreign (XML) "
                    + "content"
                )
        else:
            name = tag
        if name.casefold() in self.__foreign_content_start_tags:
            self.__in_xml = False
        if self.__is_void(name.casefold()):
            return
        if len(self.__tag_stack) == 0:
            return
        if name != self.__tag_stack[-1].name:
            return
        old: Element = self.__tag_stack.pop()
        if (
            len(self.__bad_self_closing) > 0
            and old == (bad_self_close_tup := self.__bad_self_closing[-1])[1]
        ):
            self.__flat_tree.append(
                EndTag(bad_self_close_tup[0].name, bad_self_close_tup[0])
            )
            self.__bad_self_closing.pop()
        self.__flat_tree.append(EndTag(name, old))

    # Self closing does not actually exist in standard HTML, so replace with a start
    # tag. See https://html.spec.whatwg.org/multipage/parsing.html#parse-error-non-void-
    # html-element-start-tag-with-trailing-solidus for spec
    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, Optional[str]]]
    ) -> None:
        self.__start_tag(tag, attrs, True)

    def handle_data(self, data: str) -> None:
        # If an invalid charref is found, html.parser.HTMLParser.goahead's while loop is
        # broken out of after sending the string "&#" to be processed
        if len(self.__tag_stack) > 0 and self.__tag_stack[-1].name == "script":
            self.__add_to_tree(data, True)
            return
        added = False
        if (
            len(self.__flat_tree) > 0
            and isinstance(self.__flat_tree[-1], str)
            and self.__flat_tree[-1].endswith("<")
        ):
            data = f"<{data}"
            added = True
        if data.strip() in ("]", "]]") and len(self.__flat_tree) > 0:
            # This prevents additional closing square braces from an unfinished CDATA
            # being added into the result
            if isinstance(self.__flat_tree[-1], UnknownDecl):
                return
            elif isinstance(self.__flat_tree[-1], Comment) and self.__flat_tree[
                -1
            ].content.casefold().startswith("[cdata"):
                return
        if data.startswith("<!--"):
            if data in ("<!-->", "<!--->"):
                data = "<!---->"
            elif data.endswith("--!>"):
                data = data[:-4] + "-->"
            else:
                data += "-->"
        elif data.casefold().startswith("<![cdata["):
            if data.endswith("]]>"):  # pragma: no cover
                assert False, "We should never get here!"
            self.unknown_decl(data[3:])
            return
        elif data.casefold().startswith("<!doctype"):
            self.__seen_preamble = True
            self.__quirks()
            return  # pragma: no cover  # self.__quirks() raises an exception, but this
            # may change at a later time
        elif data.startswith("</"):
            pass
        elif data.startswith("<?"):
            data = data[1:]
            if (  # pragma: no branch # Tested in other places instead
                added
                and len(self.__flat_tree) > 0
                and isinstance(self.__flat_tree[-1], str)
            ):
                self.__flat_tree[-1] = self.__flat_tree[-1][:-1]
            self.__add_to_tree(Comment(data))
            return
        elif (
            not data.startswith("<!")
            and data != "<"
            and data.startswith("<")
            and self.rawdata.endswith(data)
        ):
            if (  # pragma: no branch # This is just an extra step that happens commonly
                added
                and len(self.__flat_tree) > 0
                and isinstance(self.__flat_tree[-1], str)
            ):
                self.__flat_tree[-1] = self.__flat_tree[-1][:-1]
            return
        if added:
            data = data[1:]
        if (
            len(self.__flat_tree) > 0
            and isinstance(self.__flat_tree[-1], str)
            and self.__flat_tree[-1].endswith("&#")
            and ";" in data
        ):
            self.__flat_tree[-1] = self.__flat_tree[-1][:-2]
            loc = data.find(";")
            self.handle_charref(data[:loc])
            rawdata = self.rawdata[len(self.rawdata) - len(data) + loc + 1 :]
            self.rawdata = rawdata
            self.goahead(True)
        else:
            self.__add_to_tree(data)

    def handle_entityref(self, name: str) -> None:
        actual = ""
        rest = f"{name}"
        for char in name:
            actual += char
            rest = rest[1:]
            if f"{actual};" in entities.html5:
                self.__add_to_tree(f"&{actual};{rest}", True)
                return
        self.__add_to_tree(f"&amp;{name}&semi;", True)

    def handle_charref(self, name: str) -> None:
        if name.lower().startswith("x") and len(name) >= 2:
            try:
                num = int(name[1:], base=16)
            except ValueError:
                # It is not a valid reference, so it goes in the output as a string
                self.__add_to_tree(f"&#{name};", True)
                return
        else:
            try:
                num = int(name)
            except ValueError:
                # It is not a valid reference, so it goes in the output as a string
                self.__add_to_tree(f"&#{name};", True)
                return
        if not (self.__unicode_range[0] <= num and num <= self.__unicode_range[1]):
            # Outside Unicode range, so replace with U+FFFD as per spec
            # See error titled 'character-reference-outside-unicode-range'
            name = "xFFFD"
            warnings.warn(
                "Character reference outside valid Unicode range. This has been "
                + "replaced with &#xFFFD; (case sensitive) in the output, as per spec",
                category=UnicodeWarning,
            )
        elif (
            self.__surrogate_range[0][0] <= num and num <= self.__surrogate_range[0][1]
        ) or (
            self.__surrogate_range[1][0] <= num and num <= self.__surrogate_range[1][1]
        ):
            # Charref is a surrogate, so replace with U+FFFD as per spec
            # See error titled 'surrogate-character-reference'
            name = "xFFFD"
            warnings.warn(
                "Character reference is a surrogate. This has been "
                + "replaced with &#xFFFD; (case sensitive) in the output, as per spec",
                category=UnicodeWarning,
            )
        elif num == 0x0:
            # Charref is null, so replace with U+FFFD as per spec
            # See error titled 'null-character-reference'
            name = "xFFFD"
            warnings.warn(
                "Character reference is null (U+0000). This has been "
                + "replaced with &#xFFFD; (case sensitive) in the output, as per spec",
                category=UnicodeWarning,
            )
        self.__add_to_tree(f"&#{name};", True)

    def handle_comment(self, data: str) -> None:
        # In the source for HTMLParser, certain chars are progressively removed from the
        # data given upon processing failure. Chars are "--!". We add these, and if all
        # are added and it doesn't end with the new data, undo the additions
        for char in "--!":
            if len(data) > 0 and self.rawdata.endswith(data):
                # We have built the desired ending of the comment
                break
            data += char
        else:
            data = data[:-3]
        self.__add_to_tree(Comment(data))

    def __doctype_public_system_identifier(
        self, rest_of_decl: str, parts: list[str], i: int, quote: str
    ) -> list[str] | Literal[True]:
        """Parses a string and the parts of a HTML declaration, minus the doctype bit

        Returns either True, indicating the declaration overrall is good, else a new
            list of parts for further processing
        """
        assert len(rest_of_decl) >= 2, "Declaration content must be longer than 2 chars"
        identifier_end = rest_of_decl[1:].find(quote) + 2
        if identifier_end == 1:
            self.__quirks()
        identifier = rest_of_decl[:identifier_end]
        rest_of_decl = rest_of_decl[identifier_end:]
        if len(rest_of_decl) == 0:
            return True
        id_parts = identifier.split()
        for j, id_part in enumerate(id_parts):
            if j != 0:
                parts[i] += f" {id_part}"
                if quote in id_part:
                    end = id_part.find(quote) + 1
                    parts[i + 1] = parts[i + 1][end:]
                    if parts[i + 1] == "":
                        del parts[i + 1]
                else:
                    del parts[i + 1]
        return parts

    # Has to start with "doctype" (case insensitive)
    def handle_decl(self, decl: str) -> None:
        if self.__seen_content_before_preamble and not self.__seen_preamble:
            raise ValueError(
                "Only whitespace and HTML comments are allowed before the DOCTYPE"
            )
        else:
            self.__seen_preamble = True
        if len(decl) > 7 and not decl[7].isspace():
            decl = decl[:7] + " " + decl[7:]
        parts = decl[7:].strip().split()
        if not (len(parts) >= 1 and parts[0].lower() == "html"):
            # This is not a conforming HTML5 document
            self.__quirks()
        if len(parts) == 1:
            # It is a conforming HTML5 document
            self.__add_to_tree(Declaration(decl))
            return
        elif parts[1].upper().startswith("PUBLIC"):
            identifier_type = "public"
        elif parts[1].upper().startswith("SYSTEM"):
            identifier_type = "system"
        else:
            self.__quirks()
            return  # pragma: no cover # In the future self.__quirks may not raise an
            # exception
        if len(parts[1]) > 6:
            if len(parts) == 2:
                parts = [parts[0]] + [parts[1][:6]] + [parts[1][6:]]
            else:
                parts = [parts[0]] + [parts[1][:6]] + [parts[1][6:]] + parts[2:]
            decl = decl[:19] + " " + decl[19:]
        if len(parts) < 3:
            self.__quirks()
            return  # pragma: no cover # In the future self.__quirks may not raise an
            # exception
        if parts[2].startswith("'"):
            quote = "'"
        elif parts[2].startswith('"'):
            quote = '"'
        else:
            self.__quirks()
            return  # pragma: no cover # In the future self.__quirks may not raise an
            # exception
        if (
            identifier_type == "system"
            and parts[2] == f"{quote}about:legacy-compat{quote}"
            and len(parts) == 3
        ):
            # It is a conforming HTML5 legacy declaration, as per current spec
            self.__add_to_tree(Declaration(decl))
            return
        rest_of_parts = " ".join(parts[2:])
        parts_or_good: Literal[True] | list[str] = (
            self.__doctype_public_system_identifier(rest_of_parts, parts, 2, quote)
        )
        if isinstance(parts_or_good, bool):
            self.__add_to_tree(Declaration(decl))
            return
        else:
            parts = parts_or_good
        if identifier_type == "system":
            decl_parts = decl.split()
            self.__add_to_tree(Declaration(decl_parts[0] + " " + " ".join(parts[:3])))
            return
        if parts[3].startswith("'"):
            quote = "'"
        elif parts[3].startswith('"'):
            quote = '"'
        else:
            self.__quirks()
            return  # pragma: no cover # In the future self.__quirks may not raise an
            # exception
        rest_of_parts = " ".join(parts[3:])
        parts_or_good = self.__doctype_public_system_identifier(
            rest_of_parts, parts, 3, quote
        )
        decl_parts = decl.split()
        self.__add_to_tree(Declaration(decl_parts[0] + " " + " ".join(parts[:5])))

    def handle_pi(self, data: str) -> None:
        self.__add_to_tree(Comment(f"?{data}"))

    def unknown_decl(self, data: str) -> None:
        while data.endswith("]"):
            data = data[:-1]
        if self.__in_xml and data.casefold().startswith("cdata["):
            self.__add_to_tree(UnknownDecl(f"{data}]"))
        elif not self.__in_xml and data.casefold().startswith("cdata["):
            self.__add_to_tree(Comment(f"[{data}]]"))
        else:  # pragma: no cover  # This is an impossible situation to get here
            raise AssertionError(
                "Somehow this got called without data starting with CDATA["
            )
