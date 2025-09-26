"""Flask specific class to implement SRI hashing

The class has many functions to simplify adding SRI hashes, from adding directly to
given HTML via a decorator all the way to computing a hash given some data.
"""

import functools
import os
import ssl
from collections.abc import Callable
from typing import Optional, ParamSpec, overload
from urllib import parse as url_parse

import flask

from . import sri

P = ParamSpec("P")
__all__ = ["FlaskSRI"]


class FlaskSRI(sri.SRI):
    """Flask specific SubResource Integrity hash creation class

    When adding SRI hashes to HTML, this module only supports relative URLs for security
        reasons

    Parameters:
    app: A Flask application (flask.Flask instance)
    domain: The domain that the application is served on. This is only used by functions
        that accept HTML. The protocol (or scheme) is always HTTPS, as this should
        already be implemented at a minimum, even though not explitly required for SRI
    Keyword only:
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

    __slots__ = ("__app",)

    def __init__(
        self,
        app: flask.Flask,
        domain: str,
        *,
        quote: Optional[str] = None,
        hash_alg: str = "sha384",
        in_dev: bool = False,
        **kwargs: Optional[float | dict[str, str] | ssl.SSLContext],
    ) -> None:
        static: Optional[dict[str, str | os.PathLike[str]]] = (
            None
            if app.static_folder is None or app.static_url_path is None
            else {"directory": app.static_folder, "url_path": app.static_url_path}
        )
        self.__app = app  # pylint: disable=unused-private-member
        super().__init__(
            domain,
            quote=quote,
            static=static,
            hash_alg=hash_alg,
            in_dev=in_dev,
            **kwargs,
        )

    @overload
    def html_uses_sri(
        self, clear_or_func: Optional[bool] = None
    ) -> Callable[[Callable[P, str]], Callable[P, str]]: ...

    @overload
    def html_uses_sri(self, clear_or_func: Callable[P, str]) -> Callable[P, str]: ...

    def html_uses_sri(
        self, clear_or_func: Optional[bool] | Callable[P, str] = None
    ) -> Callable[P, str] | Callable[[Callable[P, str]], Callable[P, str]]:
        """A decorator to simplify adding SRI hashes to HTML

        @html_uses_sri
        @html_uses_sri(clear)
        clear: An optional argument, that can override in_dev, controlling whether to
            clear caches after running.
        """
        if clear_or_func is True or clear_or_func is False or clear_or_func is None:
            clear = clear_or_func

            def decorator(func: Callable[P, str]) -> Callable[P, str]:
                @functools.wraps(func)
                def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
                    nonlocal clear
                    route = url_parse.urlparse(flask.request.url).path
                    html: str = func(*args, **kwargs)
                    return self._hash_html(route, html, clear)

                return wrapper

            return decorator
        elif callable(clear_or_func):
            func: Callable[P, str] = clear_or_func

            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
                route = url_parse.urlparse(flask.request.url).path
                html: str = func(*args, **kwargs)
                return self._hash_html(route, html, None)

            return wrapper
        else:
            raise TypeError(
                f"Invalid argument type given ({type(clear_or_func)}), must be a "
                + "callable, boolean or None"
            )

    def hash_html(self, html: str, clear: Optional[bool] = None) -> str:
        """Parse some HTML, adding in a SRI hash where applicable

        html: The HTML document to add SRI hashes to, as a string
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness

        returns: New HTML with SRI hashes, as a string
        """
        route = url_parse.urlparse(flask.request.url).path
        return self._hash_html(route, html, clear)
