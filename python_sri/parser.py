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
import warnings
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
        while content.count("[") > content.count("]"):
            content += "]"
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

    __slots__ = ("__attrs", "__attrs_changed", "__text", "void", "__quote", "children")

    def __init__(
        self,
        name: str,
        text: str,
        attrs: Optional[list[tuple[str, Optional[str]]]] = None,
        void: bool = False,
        quote: str = '"',
    ) -> None:
        super().__init__(name)
        self.__attrs: dict[str, Optional[str]] = {} if attrs is None else dict(attrs)
        self.__attrs_changed: set[str] = set()
        # Remove self-closing forward slash at the end, if any,
        # to keep compliance with spec
        self.__text = text[:-1].rstrip().removesuffix("/").rstrip() + ">"
        self.void = void
        self.__quote = quote
        self.children: list[Element | Special | str] = []

    def __getitem__(self, attr: str) -> Optional[str]:
        if attr not in self.__attrs:
            return None
        return self.__attrs[attr]

    def __setitem__(self, attr: str, value: str) -> None:
        self.__attrs[attr] = value
        self.__attrs_changed.add(attr)

    def __delitem__(self, attr: str) -> None:
        if attr not in self.__attrs:
            return None
        self.__attrs_changed.add(attr)
        del self.__attrs[attr]

    def __contains__(self, attr: str) -> bool:
        return attr in self.__attrs

    @property
    def quote(self) -> str:
        return self.__quote

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
        if len(self.__attrs_changed) == 0 and self.__text != "":
            return self.__text
        attrs = self.__attrs
        new_attrs: list[str] = []
        for attr, value in attrs.items():
            new_attrs.append(
                attr
                + ("" if value is None else "=" + self.__quote + value + self.__quote)
            )
        start_tag: str = (
            "<"
            + self.name
            + ("" if len(new_attrs) == 0 else " " + " ".join(new_attrs))
            + ">"
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

    __slots__ = ("__tree", "__tag_stack", "__flat_tree", "sri_tags")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.__tree: tuple[list[Optional[Declaration]], list[Optional[Element]]] = (
            [None],
            [None],
        )
        self.__tag_stack: collections.deque[Element] = collections.deque()
        self.__flat_tree: collections.deque[Element | EndTag | Special | str] = (
            collections.deque()
        )
        self.sri_tags: list[Element] = []

    def empty(self) -> None:
        self.__tree = ([None], [None])
        self.__tag_stack.clear()
        self.__flat_tree.clear()
        self.sri_tags = []

    def stringify(self) -> str:
        """Converts the HTML tree into a HTML string

        returns: HTML, as a string
        """
        html: str = ""
        if self.__tree[0][0] is not None:
            html += self.__tree[0][0].stringify()
            html += "\n"
        if self.__tree[1][0] is None:
            return html
        tag_stack: collections.deque[Element] = collections.deque()
        finished = False
        for node in self.__flat_tree:
            if isinstance(node, Element):
                if not node.void:
                    tag_stack.append(node)
            elif isinstance(node, EndTag):
                if not finished:
                    tag_stack.pop()
                else:
                    continue
                finished = node.name[1:] == self.__flat_tree[0].name
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
    # SVG is XML, which has tags that are case sensitive. All names are lowercase,
    # so we need to replace with valid tags if its svg
    def __convert_svg(self, name: str) -> str:
        """Converts SVG tag names to camelCase, leaving HTML tags alone"""
        svg_elems: dict[str, str] = {
            "animatemotion": "animateMotion",
            "animatetransform": "animateTransform",
            "clippath": "clipPath",
            "feblend": "feBlend",
            "fecolormatrix": "feColorMatrix",
            "fecomponenttransfer": "feComponentTransfer",
            "fecomposite": "feComposite",
            "feconvolvematrix": "feConvolveMatrix",
            "fediffuselighting": "feDiffuseLighting",
            "fedisplacementmap": "feDisplacementMap",
            "fedistantlight": "feDistantLight",
            "fedropshadow": "feDropShadow",
            "feflood": "feFlood",
            "fefunca": "feFuncA",
            "fefuncb": "feFuncB",
            "fefuncg": "feFuncG",
            "fefuncr": "feFuncR",
            "fegaussianblur": "feGaussianBlur",
            "feimage": "feImage",
            "femerge": "feMerge",
            "femergenode": "feMergeNode",
            "femorphology": "feMorphology",
            "feoffset": "feOffset",
            "fepointlight": "fePointLight",
            "fespecularlighting": "feSpecularLighting",
            "fespotlight": "feSpotlight",
            "fetile": "feTile",
            "feturbulence": "feTurbulaence",
            "foreignobject": "foreignObject",
            "lineargradient": "linearGradient",
            "radialgradient": "radialGradient",
            "textpath": "textPath",
        }
        if name not in svg_elems:
            return name
        return svg_elems[name]

    def __start_tag(
        self, name: str, attrs: list[tuple[str, Optional[str]]], self_closing: bool
    ) -> None:
        """Actual handler for start tags and self closing start tags"""
        name = self.__convert_svg(name)
        text: Optional[str] = self.get_starttag_text()
        # Void elements don't require closing tags
        void: bool = self.__is_void(name)
        tag = Element(name, ("" if text is None else text), attrs, void)
        self.__flat_tree.append(tag)
        if self.__tree[1][0] is None:
            self.__tree[1][0] = tag
        else:
            # Add into tree
            self.__tag_stack[-1].append(tag)
        if self_closing and not void:
            # Self closing does not actually exist in standard HTML,
            # so replace with a pair of start and end tags
            self.__flat_tree.append(EndTag(name, tag))
        if not (void or self_closing):
            self.__tag_stack.append(tag)
        if tag.name not in ["script", "link"]:
            return
        for attr, _ in attrs:
            if attr == "integrity":
                self.sri_tags.append(tag)

    def __add_to_tree(self, data: Special | str, add_to_str: bool = False) -> None:
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
        name: str = self.__convert_svg(tag)
        if self.__is_void(name.casefold()):
            return
        if name != (start_name := self.__tag_stack[-1].name):
            return
        old: Element = self.__tag_stack.pop()
        self.__flat_tree.append(EndTag(name, old))

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
        self.__add_to_tree(Comment(data))

    def handle_decl(self, decl: str) -> None:
        if self.__tree[0][0] is not None:
            warnings.warn("Multiple HTML declarations found, overriding")
        self.__tree[0][0] = Declaration(decl)

    def handle_pi(self, data: str) -> None:
        self.__add_to_tree(ProcessingInstruction(data))

    def unknown_decl(self, data: str) -> None:
        self.__add_to_tree(UnknownDecl(data))
