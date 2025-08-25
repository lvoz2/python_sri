"""Flask specific class to implement SRI hashing

The class has many functions to simplify adding SRI hashes, from adding directly to
given HTML via a decorator all the way to computing a hash given some data.
"""

import functools
import os
import ssl
from collections.abc import Callable
from typing import Optional, ParamSpec
from urllib import parse as url_parse

import flask

from . import sri

Params = ParamSpec("Params")
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

    def __init__(
        self,
        app: flask.Flask,
        domain: str,
        *,
        hash_alg: str = "sha384",
        in_dev: bool = False,
        **kwargs: Optional[float | dict[str, str] | ssl.SSLContext],
    ) -> None:
        static: Optional[dict[str, str | os.PathLike[str]]] = (
            None
            if app.static_folder is None or app.static_url_path is None
            else {"directory": app.static_folder, "url_path": app.static_url_path}
        )
        super().__init__(
            domain, static=static, hash_alg=hash_alg, in_dev=in_dev, **kwargs
        )

    def html_uses_sri(
        self, clear_or_func: Optional[bool] | Callable[Params, str]
    ) -> (
        Callable[Params, str] | Callable[[Callable[Params, str]], Callable[Params, str]]
    ):
        """A decorator to simplify adding SRI hashes to HTML

        @html_uses_sri
        @html_uses_sri(clear)
        clear: An optional argument, that can override in_dev, controlling whether to
            clear caches after running.
        """
        if isinstance(clear_or_func, bool) or clear_or_func is None:
            clear = clear_or_func

            def decorator(func: Callable[Params, str]) -> Callable[Params, str]:
                @functools.wraps(func)
                def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> str:
                    nonlocal clear
                    route = url_parse.urlparse(flask.request.url).path
                    html: str = func(*args, **kwargs)
                    return self._hash_html(route, html, clear)

                return wrapper

            return decorator
        else:
            func: Callable[Params, str] = clear_or_func

            @functools.wraps(func)
            def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> str:
                route = url_parse.urlparse(flask.request.url).path
                html: str = func(*args, **kwargs)
                return self._hash_html(route, html, None)

            return wrapper

    def hash_html(self, html: str, clear: Optional[bool] = None) -> str:
        """Parse some HTML, adding in a SRI hash where applicable

        html: The HTML document to add SRI hashes to, as a string
        clear: Whether to clear the cache after running. Defaults to the value of in_dev
            Use the in_dev property to control automatic clearing for freshness

        returns: New HTML with SRI hashes, as a string
        """
        route = url_parse.urlparse(flask.request.url).path
        return self._hash_html(route, html, clear)
