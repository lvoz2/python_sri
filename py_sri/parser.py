from __future__ import annotations

import collections
import warnings
from html.parser import HTMLParser
from typing import Optional


# Base class for not text or Element HTML content
class Special:
    def __init__(self, prefix: str, content: str, suffix: str = "") -> None:
        self.prefix = prefix
        self.content = content
        self.suffix = suffix

    def stringify(self) -> str:
        return f"<{self.prefix}{self.content}{self.suffix}>"

    def __repr__(self) -> str:
        return self.stringify()


class Comment(Special):
    def __init__(self, content: str) -> None:
        super().__init__("!--", content, "--")


class Declaration(Special):
    def __init__(self, content: str) -> None:
        super().__init__("!", content)


class ProcessingInstruction(Special):
    def __init(self, content: str) -> None:
        super().__init__("?", content)


class UnknownDecl(Special):
    def __init__(self, content: str) -> None:
        super().__init__("![", content, "]")


class Tag:
    def __init__(self, name: str) -> None:
        self.name = name

    def stringify(self) -> str:
        return f"<{self.name}>"

    def __repr__(self) -> str:
        return self.stringify()


class Element(Tag):
    def __init__(
        self,
        name: str,
        text: str,
        attrs: Optional[list[tuple[str, Optional[str]]]] = None,
        void: bool = False,
    ) -> None:
        super().__init__(name)
        self.__attrs = None if attrs is None else {key: value for key, value in attrs}
        self.__attrs_changed: set[str] = set()
        # Remove self-closing forward slash at the end, if any,
        # to keep compliance with spec
        self.__text = text[:-1].rstrip().removesuffix("/").rstrip() + ">"
        self.void = void
        self.children: list[Element | Special | str] = []
        self.content: Optional[str] = None

    def set_attr(self, attr: str, val: str) -> None:
        if self.__attrs is None:
            self.__attrs = {}
        self.__attrs[attr] = val
        self.__attrs_changed.add(attr)

    def append(self, child: Element | Special | str, add_to_str: bool = False) -> None:
        if add_to_str and len(self.children) > 0 and isinstance(self.children[-1], str) and isinstance(child, str):
            self.children[-1] += child
        else:
            self.children.append(child)

    def stringify(self) -> str:
        if len(self.__attrs_changed) == 0 and self.__text != "":
            return self.__text
        self_closing: bool = self.__text.find("/") > 0
        attrs_start: int = self.__text.find(" ") + 1
        attrs_end: int = self.__text.find(">") - int(self_closing)
        attrs = self.__text[attrs_start:attrs_end].split(" ")
        new_attrs: list[str] = []
        if not (len(attrs) == 0 and attrs[0] == ""):
            for attr in attrs:
                if (attr_kv := attr.split("="))[0] in self.__attrs_changed:
                    if self.__attrs is not None:
                        val: Optional[str] = self.__attrs[attr_kv[0]]
                        new_attrs.append(
                            attr_kv[0] + ("" if val is None else "=" + val)
                        )
                else:
                    new_attrs.append(attr)
        start_tag: str = (
            "<"
            + self.name
            + ("" if len(new_attrs) == 0 else " " + " ".join(new_attrs))
            + ">"
        )
        return start_tag


class EndTag(Tag):
    def __init__(self, name: str, start_tag: Element) -> None:
        super().__init__(name)
        self.start_tag = start_tag

    def stringify(self) -> str:
        return f"</{self.name}>"

    def __repr__(self) -> str:
        return self.stringify()


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.__tree: tuple[list[Optional[Declaration]], list[Optional[Element]]] = ([None], [None])
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
        html: str = ""
        if self.__tree[0][0] is not None:
            html += self.__tree[0][0].stringify()
            html += "\n"
        if self.__tree[1][0] is None:
            return html
        if self.__flat_tree[0] != self.__tree[1][0]:
            raise RuntimeError(
                "Start of HTML tree does not correspond between tree types"
            )
        tag_stack: collections.deque[Element] = collections.deque()
        for node in self.__flat_tree:
            if isinstance(node, Element):
                if not node.void:
                    tag_stack.append(node)
            elif isinstance(node, EndTag):
                if node.start_tag != (start := tag_stack.pop()):
                    raise ValueError(
                        "Invalid HTML: End tag does not correspond to start tag "
                        + f"properly. Expected start: {node.start_tag}, actual "
                        + f"start: {start}, end: {node}"
                    )
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
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ]

    # Below this comment are functions for building the HTML tree
    # SVG is XML, which has tags that are case sensitive. All names are lowercase,
    # so we need to replace with valid tags if its svg
    def __convert_svg(self, name: str) -> str:
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
            if add_to_str and len(self.__flat_tree) > 0 and isinstance(self.__flat_tree[-1], str) and isinstance(data, str):
                self.__flat_tree[-1] += data
            else:
                self.__flat_tree.append(data)

    def handle_starttag(
        self, name: str, attrs: list[tuple[str, Optional[str]]]
    ) -> None:
        self.__start_tag(name, attrs, False)

    def handle_endtag(self, name: str) -> None:
        name = self.__convert_svg(name)
        if self.__is_void(name.casefold()):
            return
        if name != (start_name := self.__tag_stack[-1].name):
            raise AssertionError(
                "End tag does not match up with corresponding start tag, "
                + f"causing invalid HTML. Start tag: {start_name}, End tag: {name}"
            )
        old: Element = self.__tag_stack.pop()
        self.__flat_tree.append(EndTag(name, old))

    def handle_startendtag(
        self, name: str, attrs: list[tuple[str, Optional[str]]]
    ) -> None:
        self.__start_tag(name, attrs, True)

    def handle_data(self, data: str) -> None:
        self.__add_to_tree(data)

    def handle_entityref(self, ref: str) -> None:
        self.__add_to_tree(f"&{ref};", True)

    def handle_charref(self, ref: str) -> None:
        self.__add_to_tree(f"&#{ref};", True)

    def handle_comment(self, content: str) -> None:
        self.__add_to_tree(Comment(content))

    def handle_decl(self, content: str) -> None:
        if self.__tree[0][0] is not None:
            warnings.warn("Multiple HTML declarations found, overriding")
        self.__tree[0][0] = Declaration(content)

    def handle_pi(self, content: str) -> None:
        self.__add_to_tree(ProcessingInstruction(content))

    def unknown_decl(self, content: str) -> None:
        self.__add_to_tree(UnknownDecl(content))
