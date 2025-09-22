import abc
from collections.abc import Hashable, Iterable, Iterator, Mapping, MutableMapping
from typing import Optional, Protocol, TypeVar

# From typeshed, used to make Headers as close as possible to dict, but is hashable
K = TypeVar("K")
V_co = TypeVar("V_co", covariant=True)


class SupportsKeysAndGetItem(Protocol[K, V_co]):
    def keys(self) -> Iterable[K]: ...
    def __getitem__(self, key: K, /) -> V_co: ...


class Headers(abc.ABC, Hashable, Mapping[str, str]):
    """Request headers class that mimics dict, albeit with a few missing items

    A key reasin for this class' existence is for hashability of all the args to
        SRI.hash_url, needed for @functools.lru_cache to work

    Args:
    headers: Optional dict of header values. Defaults to the empty dict ({})

    Properties:
    headers: The headers contained

    Methods:
    freeze(): Freeze the object, preventing any changes (ie convert from being mutable
        to being immutable)
    """

    __slots__ = ("_headers", "_frozen")

    def __init__(
        self,
        headers: Optional[
            dict[str, str]
            | Iterable[tuple[str, str]]
            | Iterable[list[str]]
            | SupportsKeysAndGetItem[str, str]
        ] = None,
    ) -> None:
        if headers is None:
            self._headers: dict[str, str] = {}
        elif isinstance(headers, dict):
            self._headers = headers
        else:
            self._headers = dict(headers)
        self._frozen = True

    def __getitem__(self, header: str, /) -> str:
        return self._headers[header]

    def __contains__(self, header: object) -> bool:
        return header in self._headers

    def __len__(self) -> int:
        return len(self._headers)

    def __iter__(self) -> Iterator[str]:
        return iter(self._headers)

    def __repr__(self) -> str:
        header_type = (
            "FrozenHeaders" if isinstance(self, FrozenHeaders) else "MutableHeaders"
        )
        return f"{header_type}({repr(self._headers)})"

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError("Must implement __hash__ dunder method in subclasses")

    @abc.abstractmethod
    def freeze(self) -> "FrozenHeaders":
        raise NotImplementedError("Must implement freeze in concrete subclasses")


class FrozenHeaders(Headers):
    def __hash__(self) -> int:
        self._frozen = True
        return hash((tuple(self._headers.items()), self._frozen))

    def freeze(self) -> "FrozenHeaders":
        self._frozen = True
        return self


class MutableHeaders(Headers, MutableMapping[str, str]):
    def __init__(
        self,
        headers: Optional[
            dict[str, str]
            | Iterable[tuple[str, str]]
            | Iterable[list[str]]
            | SupportsKeysAndGetItem[str, str]
        ] = None,
    ) -> None:
        super().__init__(headers)
        self._frozen = False

    def __setitem__(self, header: str, value: str) -> None:
        self._headers[header] = value

    def __delitem__(self, header: str) -> None:
        del self._headers[header]

    def __hash__(self) -> int:
        self._frozen = True
        self.__class__ = FrozenHeaders  # type: ignore[assignment]
        assert isinstance(self, FrozenHeaders) and not isinstance(self, MutableHeaders)
        return hash((tuple(self._headers.items()), self._frozen))

    def freeze(self) -> "FrozenHeaders":
        self._frozen = True
        self.__class__ = FrozenHeaders  # type: ignore[assignment]
        assert isinstance(self, FrozenHeaders) and not isinstance(self, MutableHeaders)
        return self
