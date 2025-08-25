"""Generic (ie, not framework specific) class to implement SRI hashing

The class has many functions to simplify adding SRI hashes, from adding directly to
given HTML via a decorator all the way to computing a hash given some data.
"""

import functools
from collections.abc import Callable
from typing import Optional, ParamSpec

from . import sri

Params = ParamSpec("Params")
__all__ = ["GenericSRI"]


class GenericSRI(sri.SRI):
    """Generic SubResource Integrity hash creation class

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
    domain: The domain used by this instance for constructing absolute URLs from
        relative URLs
    hash_alg: Non editable property returning the selected hashing algorithm.
    in_dev: Non editable property returning the same value as provided by the in_dev
        parameter
    """

    # Functions for creating/inserting SRI hashes
    # Starts with some decorators for ease, then each step has its own func
    # Ends with either the hash of a file descriptor or the content of some site
    # Hashing a URL has not been implemented yet

    def html_uses_sri(
        self, route: str, clear: Optional[bool] = None
    ) -> Callable[[Callable[Params, str]], Callable[Params, str]]:
        """A decorator to simplify adding SRI hashes to HTML

        @html_uses_sri(route, clear)
        route: The route that this function is defined for. Used to interpret relative
            URLs
        clear: An optional argument, that can override in_dev, controlling whether to
            clear caches after running.
        """

        def decorator(func: Callable[Params, str]) -> Callable[Params, str]:
            @functools.wraps(func)
            def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> str:
                nonlocal clear
                nonlocal route
                html: str = func(*args, **kwargs)
                return self._hash_html(route, html, clear)

            return wrapper

        return decorator

    def hash_html(self, route: str, html: str, clear: Optional[bool] = None) -> str:
        """Parse some HTML, adding in a SRI hash where applicable

        route: The URL path of the view calling hash_html
        html: The HTML document to add SRI hashes to, as a string
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness

        returns: New HTML with SRI hashes
        """
        return self._hash_html(route, html, clear)
