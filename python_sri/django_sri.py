"""Django specific class to implement SRI hashing

The class has many functions to simplify adding SRI hashes, from adding directly to
given HTML via a decorator all the way to computing a hash given some data.
"""

import functools
import os
import pathlib
import ssl
from collections.abc import Callable
from typing import Concatenate, Optional, ParamSpec, cast
from urllib import parse as url_parse

from django import http as dj_http
from django.conf import settings as dj_settings
from django.contrib.staticfiles import finders as static_finders

from . import sri

Params = ParamSpec("Params")


class DjangoSRI(sri.SRI):
    """Django specific SubResource Integrity hash creation class

    When adding SRI hashes to HTML, this module only supports relative URLs for security
        reasons

    Parameters:
    domain: The domain that the application is served on. This is only used by functions
        that accept HTML. The protocol (or scheme) is always HTTPS, as this should
        already be implemented at a minimum, even though not explitly required for SRI
    Keyword only:
    use_static_override: An override to the automatic detection of static file
        configuration. Defaults to "True", denoting that this instance will
        automatically configure itself with your Django staticfiles configuration
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

    __slots__ = ("__use_finder",)

    def __init__(
        self,
        domain: str,
        *,
        use_static_override: bool = True,
        hash_alg: str = "sha384",
        in_dev: bool = False,
        **kwargs: Optional[float | dict[str, str] | ssl.SSLContext],
    ) -> None:
        static: Optional[dict[str, str | os.PathLike[str]]] = {}
        if hasattr(dj_settings, "STATIC_URL") and static is not None:
            if (
                hasattr(dj_settings, "STATIC_ROOT")
                and dj_settings.STATIC_ROOT is not None
            ):
                static["url_path"] = dj_settings.STATIC_URL
                static["directory"] = dj_settings.STATIC_ROOT
                self.__use_finder = False
            else:
                static["directory"] = "static"
                self.__use_finder = True
        if not static:  # According to Pylint, empty dicts are falsey
            static = None
        super().__init__(
            domain, static=static, hash_alg=hash_alg, in_dev=in_dev, **kwargs
        )
        self._use_static = static is not None and use_static_override

    def _absolute_to_fs(self, url: str) -> pathlib.Path:
        """Converts an absolute URL (https://domain.com/path) to a filesystem path

        url: The absolute URL to convert

        Returns: A filesystem path (pathlib.Path). No guarantee to whether the path
            exists
        """
        if not self._use_static or self._static_url is None or self._static_dir is None:
            raise ValueError(
                "No static configuration, so conversions to filesystem paths are "
                + "disabled"
            )
        url_path = url_parse.urlparse(url).path
        new_path: str = url_path.removeprefix(self._static_url)
        if new_path == url_path:
            # Absolute URL did not point to the configured static path
            raise ValueError("Resource in URL not in configured static directory")
        if self.__use_finder:
            path: Optional[str] = static_finders.find(new_path)
            if path is None:
                raise ValueError("Resource in URL not found")
            return pathlib.Path(path)
        return self._static_dir / pathlib.Path(new_path)

    def html_uses_sri(self, clear: Optional[bool] = None) -> Callable[
        [Callable[Concatenate[dj_http.HttpRequest, Params], dj_http.HttpResponse]],
        Callable[Concatenate[dj_http.HttpRequest, Params], dj_http.HttpResponse],
    ]:
        """A decorator to simplify adding SRI hashes to HTML

        @html_uses_sri(route, clear)
        route: The route that this function is defined for. Used to interpret relative
            URLs
        clear: An optional argument, that can override in_dev, controlling whether to
            clear caches after running.
        """

        def decorator(
            func: Callable[
                Concatenate[dj_http.HttpRequest, Params], dj_http.HttpResponse
            ],
        ) -> Callable[Concatenate[dj_http.HttpRequest, Params], dj_http.HttpResponse]:
            @functools.wraps(func)
            def wrapper(
                request: dj_http.HttpRequest,
                *args: Params.args,
                **kwargs: Params.kwargs,
            ) -> dj_http.HttpResponse:
                nonlocal clear
                response: dj_http.HttpResponse = func(request, *args, **kwargs)
                # Pulled from django source, in django.http.response.HttpResponse.text()
                res_html = response.content.decode(response.charset or "utf-8")
                html = self._hash_html(request.path, res_html, clear)
                response.content = html.encode(response.charset or "utf-8")
                return response

            # Mypy didn't like return wrapper, with wrapper having the type
            # Arg(HttpRequest, 'request') in place of just HttpRequest, so silenced with
            # cast(type, var)
            return cast(
                Callable[
                    Concatenate[dj_http.HttpRequest, Params], dj_http.HttpResponse
                ],
                wrapper,
            )

        return decorator

    def hash_html(
        self, route: str, response: dj_http.HttpResponse, clear: Optional[bool] = None
    ) -> dj_http.HttpResponse:
        res_html = response.content.decode(response.charset or "utf-8")
        html = self._hash_html(route, res_html, clear)
        response.content = html.encode(response.charset or "utf-8")
        return response

    def hash_response(
        self, route: str, response: dj_http.HttpResponse, clear: Optional[bool] = None
    ) -> dj_http.HttpResponse:
        return self.hash_html(route, response, clear)
