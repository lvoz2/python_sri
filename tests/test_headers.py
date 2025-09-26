import pytest

from python_sri import FrozenHeaders, Headers, MutableHeaders


def test_headers_args_and_contains() -> None:
    h = MutableHeaders({"Content-Type": "text/html"})
    assert "Content-Type" in h


def test_headers_no_args() -> None:
    h = MutableHeaders()
    assert "Content-Type" not in h


def test_headers_get() -> None:
    h = MutableHeaders({"Content-Type": "text/html"})
    assert h["Content-Type"] == "text/html"


def test_headers_set() -> None:
    h = MutableHeaders()
    h["Content-Type"] = "text/html"
    assert h["Content-Type"] == "text/html"


def test_headers_del() -> None:
    h = MutableHeaders({"Content-Type": "text/html"})
    del h["Content-Type"]
    with pytest.raises(KeyError, match="Content-Type"):
        print(h["Content-Type"])


def test_frozen_headers_set() -> None:
    h = FrozenHeaders()
    with pytest.raises(TypeError, match="object does not support item assignment"):
        h["Content-Type"] = "text/html"  # type: ignore[index]  # pylint: disable=unsupported-assignment-operation


def test_frozen_headers_del() -> None:
    h = FrozenHeaders({"Content-Type": "text/html"})
    with pytest.raises(TypeError, match="object does not support item deletion"):
        del h["Content-Type"]  # type: ignore[attr-defined]  # pylint: disable=unsupported-delete-operation


def test_frozen_hash() -> None:
    raw = {"Content-Type": "text/html"}
    h = FrozenHeaders(raw)
    assert hash(h) == hash((tuple(raw.items()), True))


def test_mutable_hash() -> None:
    raw = {"Content-Type": "text/html"}
    h = MutableHeaders(raw)
    assert hash(h) == hash((tuple(raw.items()), isinstance(h, FrozenHeaders)))


def test_frozen_freeze() -> None:
    raw = {"Content-Type": "text/html"}
    h = FrozenHeaders(raw)
    assert h is h.freeze()


def test_mutable_freeze() -> None:
    raw = {"Content-Type": "text/html"}
    h = MutableHeaders(raw)
    assert h is h.freeze()


def test_header_len() -> None:
    raw = {"content-type": "application/json"}
    h = MutableHeaders(raw)
    assert len(raw) == len(h)


def test_header_iter() -> None:
    raw = {"content-type": "application/json"}
    h = MutableHeaders(raw)
    assert list(iter(raw)) == list(iter(h))


def test_header_repr() -> None:
    raw = {"content-type": "application/json"}
    h = MutableHeaders(raw)
    assert f"MutableHeaders({repr(raw)})" == repr(h)


def test_tuple_arg() -> None:
    raw = {"content-type": "application/json"}
    test_h = MutableHeaders(raw)
    out_h = MutableHeaders(tuple(raw.items()))
    assert list(test_h.items()) == list(out_h.items())


def test_abstract_instantiation() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class Headers"):
        Headers()  # type: ignore[abstract]  # pylint: disable=abstract-class-instantiated


class THeaders(Headers):
    def __hash__(self) -> int:  # pylint: disable=useless-parent-delegation
        return super().__hash__()  # type: ignore[safe-super]

    def freeze(self) -> FrozenHeaders:
        return super().freeze()  # type: ignore[safe-super]


def test_abstract_hash() -> None:
    h = THeaders()
    with pytest.raises(
        NotImplementedError, match="Must implement __hash__ dunder method in subclasses"
    ):
        hash(h)


def test_abstract_freeze() -> None:
    h = THeaders()
    with pytest.raises(
        NotImplementedError, match="Must implement freeze in concrete subclasses"
    ):
        h.freeze()
