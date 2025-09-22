"""FastAPI specific class to implement SRI hashing

The class has many functions to simplify adding SRI hashes, from adding directly to
given HTML via a decorator all the way to computing a hash given some data.
"""

import functools
import inspect
import os
import ssl
from collections.abc import Callable
from typing import Any, Concatenate, Optional, ParamSpec, TypeVar, cast

import fastapi
import starlette

from . import sri

P = ParamSpec("P")
T = TypeVar("T")
__all__ = ["FastAPISRI"]


class FastAPISRI(sri.SRI):
    """FastAPI specific SubResource Integrity hash creation class

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

    __slots__: tuple[str, ...] = tuple()

    def __init__(
        self,
        *,
        domain: str = "",
        quote: Optional[str] = None,
        static: Optional[dict[str, str | os.PathLike[str]]] = None,
        hash_alg: str = "sha384",
        in_dev: bool = False,
        **kwargs: Optional[float | dict[str, str] | ssl.SSLContext],
    ) -> None:
        super().__init__(
            domain,
            quote=quote,
            static=static,
            hash_alg=hash_alg,
            in_dev=in_dev,
            **kwargs,
        )
        self.domain = domain

    def __hash_html(
        self, data: T, req: starlette.requests.Request, clear: Optional[bool]
    ) -> T:
        if not isinstance(data, str):
            return data
        route = req.url.path
        if self.domain == "":
            self.domain = req.url.netloc
        return cast(T, self._hash_html(route, data, clear))

    def html_uses_sri(self, clear: Optional[bool] = None) -> Callable[
        [Callable[P, T]],
        Callable[Concatenate[starlette.requests.Request, P], T] | Callable[P, T],
    ]:
        """A decorator to simplify adding SRI hashes to HTML

        @html_uses_sri(clear)
        clear: An optional argument, that can override in_dev, controlling whether to
            clear caches after running.
        """

        def decorator(
            func: Callable[P, T],
        ) -> Callable[Concatenate[starlette.requests.Request, P], T] | Callable[P, T]:
            anno: Optional[dict[str, type[Any]]] = (  # type: ignore[explicit-any]
                getattr(func, "__annotations__", None)
            )
            vals = None if anno is None else tuple(anno.values())
            if (
                anno is not None
                and vals is not None
                and (fastapi.Request in vals or starlette.requests.Request in vals)
            ):
                loc = vals.index(
                    fastapi.Request
                    if fastapi.Request in vals
                    else starlette.requests.Request
                )
                key = tuple(anno.keys())[loc]

                @functools.wraps(func)
                def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    nonlocal key
                    if key in kwargs:
                        req = kwargs[key]
                    # FastAPI currently unpacks a dict, so the following block is not
                    # expected to ever run until this is changed
                    else:  # pragma: no cover
                        nonlocal loc
                        req = args[loc]
                    assert isinstance(req, fastapi.Request | starlette.requests.Request)
                    data: T = func(*args, **kwargs)
                    return self.__hash_html(data, req, clear)

                return cast(Callable[P, T], wrapper)

            else:

                @functools.wraps(func)
                def wrapper(
                    req: starlette.requests.Request, *args: P.args, **kwargs: P.kwargs
                ) -> T:
                    data: T = func(*args, **kwargs)
                    return self.__hash_html(data, req, clear)

                o_sig = inspect.signature(wrapper)
                params = list(o_sig.parameters.values())
                params.insert(
                    0,
                    inspect.Parameter(
                        "req",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=starlette.requests.Request,
                    ),
                )
                n_sig = o_sig.replace(parameters=params)
                # Mypy didn't like the returned wrapper, with wrapper having the type
                # Arg(Request, 'request') in place of just Request, so silenced with
                # cast(type, var)
                new_wrapper = cast(
                    Callable[Concatenate[starlette.requests.Request, P], T],
                    wrapper,
                )
                new_wrapper.__signature__ = n_sig  # type: ignore[attr-defined]
                if getattr(new_wrapper, "__annotations__", None) not in (None, {}):
                    new_wrapper.__annotations__ = {
                        "req": starlette.requests.Request,
                        **new_wrapper.__annotations__,
                    }
                return new_wrapper

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
