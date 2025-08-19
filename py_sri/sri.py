"""Main class to implement SRI hashing

The class has many functions to simplify adding SRI hashes, from adding directly to
given HTML via a decorator all the way to computing a hash given some data.
"""

import base64
import functools
import hashlib
import io
import pathlib
import re
import sys
from typing import Any, Callable, Literal, Optional, cast
from urllib import parse as url_parse

from . import parser


class SRI:
    """SubResource Integrity hash creation class

    When adding SRI hashes to HTML, this module only supports relative URLs for security
        reasons

    Parameters:
    domain: The domain that the application is served on. This is only used by functions
        that accept HTML. The protocol (or scheme) is always HTTPS, as this should
        already be implemented at a minimum, even though not explitly required for SRI
    Keyword only:
    static: Either None, disabling using the filesystem, or a dictionary with the keys
        "directory" and "url_path", the former being a path-like object and the latter a
        string, that is used to convert a URL into a filesystem path for reading files
    hash_alg: A string describing the desired hashing algorithm to choose. Defaults to
        "sha384". Currently limited to "sha256", "sha384", and "sha512"
    in_dev: A boolean value, defaulting to False, describing whether to, by default,
        clear method caches upon method completion. This is useful when developing a
        website, as it ensures fresh changes to files do not break the site. Can be
        overridden by the clear parameter on an individual method, which by default
        inherits the value of this parameter.

    Properties:
    available_algs: Tuple of available hashing algorithms
    hash_alg: Non editable property returning the selected hashing algorithm.
    in_dev: Non editable property returning the same value as provided by the in_dev
        parameter
    """

    __slots__ = (
        "domain",
        "__static_dir",
        "__static_url",
        "__hash_alg",
        "__in_dev",
        "__sri_ptrn",
        "__parser",
    )
    available_algs: tuple[str, str, str] = ("sha256", "sha384", "sha512")

    def __init__(
        self,
        domain: str,
        *,
        static: Optional[dict[str, str | pathlib.Path]] = None,
        hash_alg: str = "sha384",
        in_dev: bool = False,
    ) -> None:
        self.domain = domain
        if static is not None:
            if not isinstance(static, dict):
                raise TypeError("static must either be None or a dictionary")
            if "directory" not in static:
                raise ValueError("A directory must be given in the static dictionary")
            elif isinstance(static["directory"], str):
                static["directory"] = pathlib.Path(static["directory"])
            if "url_path" not in static:
                raise ValueError("A url_path must be given in the static dictionary")
            else:
                if not isinstance(static["url_path"], pathlib.Path) and len(
                    static["url_path"]
                ) - 1 != static["url_path"].rfind("/"):
                    static["url_path"] += "/"
        self.__static_dir: Optional[pathlib.Path] = (
            None
            if static is None
            else (
                static["directory"]
                if isinstance(static["directory"], pathlib.Path)
                else None
            )
        )
        if self.__static_dir is not None and not self.__static_dir.is_dir():
            raise ValueError(
                "Provided static directory does not exist or is not a directory"
            )
        self.__static_url: Optional[str] = (
            None
            if static is None
            else (static["url_path"] if isinstance(static["url_path"], str) else None)
        )
        # Normalize string to best fit the three values
        # of sha256, sha384, sha512
        ptrn = re.compile("[\\W_]+")
        hash_alg = ptrn.sub("", hash_alg.casefold())
        if hash_alg not in self.available_algs:
            raise ValueError("Hash algorithm is not allowed to be used for SRI hashes")
        self.__hash_alg: Literal["sha256", "sha384", "sha512"] = cast(
            Literal["sha256", "sha384", "sha512"], hash_alg
        )
        # If in_dev is True, then the caches need clearing after each run for freshness
        self.__in_dev = in_dev
        self.__sri_ptrn = re.compile(
            "sha(256-[-A-Za-z0-9+/]{43}=?|"
            + "384-[-A-Za-z0-9+/]{64}|512-[-A-Za-z0-9+/]{86}(={2})?)"
        )
        self.__parser = parser.Parser()

    def __hash__(self) -> int:
        if self.__static_dir is None:
            return hash((self.domain, None, self.__hash_alg, self.__in_dev))
        return hash(
            (
                self.domain,
                self.__static_dir,
                self.__static_url,
                self.__hash_alg,
                self.__in_dev,
            )
        )

    @property
    def hash_alg(self) -> Literal["sha256", "sha384", "sha512"]:
        return self.__hash_alg

    @property
    def in_dev(self) -> bool:
        return self.__in_dev

    def clear_cache(self) -> None:
        self.hash_file_path.cache_clear()
        self.hash_file_object.cache_clear()
        self.hash_url.cache_clear()

    # Functions for creating/inserting SRI hashes
    # Starts with some decorators for ease, then each step has its own func
    # Ends with either the hash of a file descriptor or the content of some site
    # Hashing a URL has not been implemented yet

    def html_uses_sri(
        self, route: str, clear: Optional[bool] = None
    ) -> Callable[[Callable[..., str]], Callable[..., str]]:
        """A decorator to simplify adding SRI hashes to HTML

        @html_uses_sri(route, clear)
        route: The route that this function is defined for. Used to interpret relative
            URLs
        clear: An optional argument, that can override in_dev, controlling whether to
            clear caches after running.
        """

        def decorator(func: Callable[..., str]) -> Callable[..., str]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> str:
                nonlocal clear
                nonlocal route
                html: str = func(*args, **kwargs)
                return self.hash_html(route, html, clear)

            return wrapper

        return decorator

    def hash_html(self, route: str, html: str, clear: Optional[bool] = None) -> str:
        """Parse some HTML, adding in a SRI hash where applicable

        html: The HTML document to operate from
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness

        returns: New HTML with SRI hashes
        """
        if clear is None:
            clear = self.__in_dev
        self.__parser.empty()
        self.__parser.feed(html)
        sri_tags: list[parser.Element] = self.__parser.sri_tags
        base_url = url_parse.urljoin(self.domain, route)
        for tag in sri_tags:
            integrity: Optional[str] = tag["integrity"]
            if integrity is None:
                integrity = ""
            # Check if integrity attribute already has a SRI hash (sha256-HASH,
            # sha384-HASH, sha512-HASH), where HASH could be 43 or 44 (sha256), 64
            # (sha384), or 79, 80 or 81 (sha512) chars in length
            if re.fullmatch(self.__sri_ptrn, integrity) is not None:
                # It is a SRI hash
                continue
            # Check if tag can actually utilise SRI, otherwise remove integrity attr and
            # add data-sri-error attribute with the error message
            if ("href" if tag.name == "link" else "src") not in tag:
                del tag["integrity"]
                tag["data-sri-error"] = "No URL to resource provided"
                continue
            if tag.name == "link" and (
                tag["rel"] not in ["stylesheet", "preload"]
                or (tag["rel"] == "preload" and tag["as"] not in ["script", "style"])
            ):
                del tag["integrity"]
                # In the <link> tag of this message, include the as="val" attribute if
                # rel="preload"
                as_attr = "" if tag["as"] is None else tag["as"]
                tag["data-sri-error"] = (
                    "Integrity attribute not supported with "
                    + f'<link rel="{tag["rel"]}"'
                    + ((' as="' + as_attr + '"') if tag["rel"] == "preload" else "")
                    + "> values"
                )
                continue
            # No checks for URL validity, except that it does not have a domain name
            # If the URL is not valid, then browsers will notify devs that it is not
            # Once the URL is valid, then it should just work here
            src: Optional[str] = tag[attr := "href" if tag.name == "link" else "src"]
            if src is None or len(src.strip()) == 0:
                del tag["integrity"]
                tag["data-sri-error"] = f"No URL found in {attr} attribute"
                continue
            src = src.strip()
            hash_str: str = ""
            parsed_url: url_parse.ParseResult = url_parse.urlparse(src)
            if parsed_url.netloc != "":
                # URL is an absolute URL which is currently not supported due to
                # difficulty proving the domain is owned by the app so that CDN content
                # is not hashed on page load, which would defeat the purpose of SRI
                del tag["integrity"]
                tag["data-sri-error"] = (
                    "py-sri does not currently support the addition of SRI hashes to "
                    + "absolute URLs. If this resource is owned by the website, use "
                    + "a relative URL instead for SRI hashes"
                )
                continue
            # Conversion to absolute URL is required for getting resources via network
            # and to match against a static path to find resources on the filesystem
            as_absolute_url: str = url_parse.urljoin(base_url, src)
            if self.__static_dir is not None and self.__static_url is not None:
                # Fetch via filesystem read
                url_path = url_parse.urlparse(as_absolute_url).path
                new_path: str = url_path.removeprefix(self.__static_url)
                if new_path == url_path:
                    # Absolute URL did not point to the configured static path
                    del tag["integrity"]
                    tag["data-sri-error"] = (
                        "Resource in URL not in configured static directory"
                    )
                    continue
                fs_path: pathlib.Path = self.__static_dir / pathlib.Path(new_path)
                hash_str = self.hash_file_path(fs_path, False)
            else:
                # Fetch via HTTP GET request
                pass
            if hash_str == "":
                # Unknown error or no message passed up
                del tag["integrity"]
                tag["data-sri-error"] = (
                    "An unknown error occured, or no static configuration found"
                )
                continue
            elif len(hash_str) >= 3 and hash_str[:3] == "sha":
                # Valid hash
                tag["integrity"] = hash_str
            else:
                # Hash function has errored, message is in hash_str
                del tag["integrity"]
                tag["data-sri-error"] = hash_str
                continue
        if clear:
            self.clear_cache()
        return self.__parser.stringify()

    @functools.lru_cache(maxsize=64)
    def hash_file_path(
        self, path: str | pathlib.Path, clear: Optional[bool] = None
    ) -> str:
        """Hashes a file, using the file's path

        path: The path to the file to hash (a string or pathlib.Path)
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness

        returns: The SRI hash (eg sha256-HASH), or an empty string if the path does not
            exist or is not a file
        """
        if clear is None:
            clear = self.__in_dev
        if isinstance(path, pathlib.Path):
            if not path.is_file():
                return "File not found"
            with open(path, "rb") as f:
                if clear:
                    self.clear_cache()
                return self.hash_file_object(f, False)
        elif isinstance(path, str) and url_parse.urlparse(path).netloc == "":
            path_inst = pathlib.Path(path)
            if not path_inst.is_file():
                return "File not found"
            with open(path_inst, "rb") as f:
                if clear:
                    self.clear_cache()
                return self.hash_file_object(f, False)
        raise TypeError("Given file path does not seem like a usable file path")

    @functools.lru_cache(maxsize=64)
    def hash_file_object(
        self, file: io.BufferedIOBase, clear: Optional[bool] = None
    ) -> str:
        """Hashes a file, using a file object

        file: The file object, opened in binary mode (b)
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness

        returns: The SRI hash (eg sha256-HASH)
        """
        if clear is None:
            clear = self.__in_dev
        if sys.version_info.minor < 11:
            # hashlib.file_digest was added in Python 3.11
            with file:
                res = self.hash_data(file.read())
        else:
            alg = self.__hash_alg
            f_digest = hashlib.file_digest(file, alg)  # type: ignore[attr-defined]
            digest: bytes = f_digest.digest()
            b64: str = base64.b64encode(digest).decode(encoding="ascii")
            res = f"{self.__hash_alg}-{b64}"
        if clear:
            self.clear_cache()
        return res

    @functools.lru_cache(maxsize=64)
    def hash_url(
        self,  # pylint: disable=W0613
        url: str,  # pylint: disable=W0613
        *args: Any,
        clear: Optional[bool] = None,
        **kwargs: Any,
    ) -> str:
        """Hashes the content of a url (NOT IMPLEMENTED YET)

        url: The URL
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness
        Extra arguments are given to urllib.request.urlopen()

        returns: The SRI hash (eg sha256-HASH)
        """
        if clear is None:
            clear = self.__in_dev
        # Insert implementation here
        if clear:
            self.clear_cache()
        return (
            "Currently, only file hashing is supported, but soon URL hashing will "
            + "be implemented"
        )

    def hash_data(self, data: bytes | bytearray | memoryview) -> str:
        """Create an SRI hash from some data

        data: A bytes-like object to hash

        returns: The SRI hash (eg sha256-HASH)
        """
        sha_hash = hashlib.new(self.__hash_alg)
        sha_hash.update(data)
        digest: bytes = sha_hash.digest()
        b64: str = base64.b64encode(digest).decode(encoding="ascii")
        return f"{self.__hash_alg}-{b64}"
