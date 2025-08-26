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
from html.parser import HTMLParser
from typing import Optional

__all__ = ["Element", "Parser"]


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


class ProcessingInstruction(Special):
    """A HTML Processing Instruction, as a class"""

    __slots__ = ()

    def __init__(self, content: str) -> None:
        super().__init__("?", content)


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
        quote: str = '"',
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
        self.__quote = quote
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
    def xml_self_closing(self) -> bool:
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
                + ("" if value is None else "=" + self.__quote + value + self.__quote)
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

    __slots__ = ("__tag_stack", "__flat_tree", "sri_tags", "__in_xml")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.__tag_stack: collections.deque[Element] = collections.deque()
        self.__flat_tree: collections.deque[Element | EndTag | Special | str] = (
            collections.deque()
        )
        self.sri_tags: list[Element] = []
        self.__in_xml = False
        # Finds primarily the element/attribute names in a svg tag block. Uses this spec
        # https://www.w3.org/TR/REC-xml/#NT-Name for definition. Only used inside XML
        self.__bits_regex = re.compile(
            "([:A-Z_a-z\xc0-\xd6\xd8-\xf6\u00f8-\u02ff\u0370-\u037d\u037f-\u1fff\u200c"
            + "-\u200d\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff\uf900-\ufdcf\ufdf0-\ufffd"
            + "\U00010000-\U000effff][:A-Z_a-z\xc0-\xd6\xd8-\xf6\u00f8-\u02ff\u0370-"
            + "\u037d\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff"
            + "\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000effff-.0-9\xb7\u0300-\u036f"
            + "\u203f-\u2040]*)(=['\"].+?['\"])?"
        )

    def reset(self) -> None:
        super().reset()
        if hasattr(self, "sri_tags"):
            self.__tag_stack.clear()
            self.__flat_tree.clear()
            self.sri_tags = []
            self.__in_xml = False

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

    # Below this comment are functions for building the HTML tree
    # First we override feed as we only will ever parse full sections
    def feed(self, data: str) -> None:
        self.reset()
        self.rawdata = data  # pylint: disable=attribute-defined-outside-init
        self.goahead(True)

    def __start_tag(
        self, name: str, attrs: list[tuple[str, Optional[str]]], self_closing: bool
    ) -> None:
        """Actual handler for start tags and self closing start tags"""
        if name in ["svg"]:
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
                    key = attr_in_bits.group(0).split("=")[0]
                    attrs[i] = (key, attrs[i][1])
        # Void elements don't require closing tags
        void: bool = self.__is_void(name)
        tag = Element(name, attrs, void)
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
        if name.casefold() in ["svg"]:
            self.__in_xml = False
        if self.__is_void(name.casefold()):
            return
        if len(self.__tag_stack) == 0:
            return
        if name != self.__tag_stack[-1].name:
            return
        old: Element = self.__tag_stack.pop()
        self.__flat_tree.append(EndTag(name, old))

    # Self closing does not actually exist in standard HTML, so replace with a start
    # tag. See https://html.spec.whatwg.org/multipage/parsing.html#parse-error-non-void-
    # html-element-start-tag-with-trailing-solidus for spec
    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, Optional[str]]]
    ) -> None:
        self.__start_tag(tag, attrs, True)

    def handle_data(self, data: str) -> None:
        self.__add_to_tree(data)

    def handle_entityref(self, name: str) -> None:
        self.__add_to_tree(f"&{name};", True)

    def handle_charref(self, name: str) -> None:
        self.__add_to_tree(f"&#{name};", True)

    def handle_comment(self, data: str) -> None:
        # In the source for HTMLParser, certain chars are progressively removed from the
        # data given upon processing failure
        for char in "--!":
            if self.rawdata.endswith(data):
                raise ValueError(
                    "Given HTML is malformed and could not be fully processed by "
                    + "Python's html.parser.HTMLParser class. The unprocessed HTML is "
                    + f"as follows: {data}"
                )
            data += char
        data = data[:-3]
        self.__add_to_tree(Comment(data))

    def handle_decl(self, decl: str) -> None:
        if self.rawdata.endswith(decl):
            raise ValueError(
                "Given HTML is malformed and could not be fully processed by Python's "
                + "html.parser.HTMLParser class. The unprocessed HTML is as follows: "
                + decl
            )
        self.__add_to_tree(Declaration(decl))

    def handle_pi(self, data: str) -> None:
        if self.rawdata.endswith(data):
            raise ValueError(
                "Given HTML is malformed and could not be fully processed by Python's "
                + "html.parser.HTMLParser class. The unprocessed HTML is as follows: "
                + data
            )
        self.__add_to_tree(ProcessingInstruction(data))

    def unknown_decl(self, data: str) -> None:
        if self.rawdata.endswith(data):
            raise ValueError(
                "Given HTML is malformed and could not be fully processed by Python's "
                + "html.parser.HTMLParser class. The unprocessed HTML is as follows: "
                + data
            )
        if self.__in_xml and data.startswith("CDATA["):
            self.__add_to_tree(UnknownDecl(f"{data}]"))
        elif not self.__in_xml and data.startswith("CDATA["):
            self.__add_to_tree(Comment(f"[{data}]]"))
        else:  # pragma: no cover  # This is an impossible situation to get here
            raise AssertionError(
                "Somehow this got called without data starting with CDATA["
            )
