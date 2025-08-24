"""Tests importing python_sri with various installed optional packages"""

import sys
import types
from typing import Generator, Optional, Sequence, cast

import pytest


# From https://stackoverflow.com/questions/51044068/test-for-import-of-optional-
# dependencies-in-init-py-with-pytest-python-3-5/51048604?r=Saves_UserSavesList#51048604
class PackageDiscarder:
    """Pretends that a list of packages aren't actually installed, by raising an
    exception part way through the import process
    """

    def __init__(self) -> None:
        self.pkgnames: list[str] = []

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,  # pylint: disable=unused-argument
        target: types.ModuleType | None = None,  # pylint: disable=unused-argument
    ) -> None:
        if fullname in self.pkgnames:
            raise ImportError()

    def __repr__(self) -> str:
        return f"PackageDiscarder({self.pkgnames})"


available_installed = {"django.http", "flask", "fastapi.staticfiles"}
discarders: list[PackageDiscarder] = []
popped: dict[str, Optional[types.ModuleType]] = {}


def simulate_installed(installed: list[str]) -> None:
    """Simulates having installed only a given set of modules from what is actually
        installed
    Args:
    installed: A list of modules that will appear installed. All others froom the
        available_installed set will appear uninstalled
    """
    if len(popped.keys()) > 0:
        for module in installed:
            if module in popped and popped[module] is not None:
                sys.modules[module] = cast(types.ModuleType, popped[module])
    for discarder in discarders:
        try:
            sys.meta_path.remove(discarder)
        except ValueError:
            pass
    d = PackageDiscarder()
    to_remove = available_installed - set(installed)
    for module in to_remove:
        popped[module] = sys.modules.pop(module, None)
        d.pkgnames.append(module)
    sys.meta_path.insert(0, d)
    discarders.append(d)


@pytest.fixture
def no_django() -> Generator[None]:
    simulate_installed(["fastapi.staticfiles", "flask"])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.fixture
def no_flask() -> Generator[None]:
    simulate_installed(["django.http", "fastapi.staticfiles"])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.fixture
def no_fastapi() -> Generator[None]:
    simulate_installed(["flask", "django.http"])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.fixture
def no_flask_no_fastapi() -> Generator[None]:
    simulate_installed(["django.http"])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.fixture
def no_flask_no_django() -> Generator[None]:
    simulate_installed(["fastapi.staticfiles"])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.fixture
def no_django_no_fastapi() -> Generator[None]:
    simulate_installed(["flask"])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.fixture
def none_installed() -> Generator[None]:
    simulate_installed([])
    yield
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


def test_all_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "DjangoSRI")
        and hasattr(python_sri, "FlaskSRI")
        and hasattr(python_sri, "FastAPISRI")
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )
    del python_sri
    if "python_sri" in sys.modules:
        del sys.modules["python_sri"]


@pytest.mark.usefixtures("no_django")
def test_django_not_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        not hasattr(python_sri, "DjangoSRI")
        and hasattr(python_sri, "FlaskSRI")
        and hasattr(python_sri, "FastAPISRI")
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )


@pytest.mark.usefixtures("no_flask")
def test_flask_not_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "DjangoSRI")
        and not hasattr(python_sri, "FlaskSRI")
        and hasattr(python_sri, "FastAPISRI")
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )


@pytest.mark.usefixtures("no_fastapi")
def test_fastapi_not_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "DjangoSRI")
        and hasattr(python_sri, "FlaskSRI")
        and not hasattr(python_sri, "FastAPISRI")
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )


@pytest.mark.usefixtures("no_flask_no_fastapi")
def test_django_only_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "SRI")
        and hasattr(python_sri, "DjangoSRI")
        and not hasattr(python_sri, "FlaskSRI")
        and not hasattr(python_sri, "FastAPISRI")
        and python_sri.SRI == python_sri.DjangoSRI
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )


@pytest.mark.usefixtures("no_django_no_fastapi")
def test_flask_only_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "SRI")
        and not hasattr(python_sri, "DjangoSRI")
        and hasattr(python_sri, "FlaskSRI")
        and not hasattr(python_sri, "FastAPISRI")
        and python_sri.SRI == python_sri.FlaskSRI
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )


@pytest.mark.usefixtures("no_flask_no_django")
def test_fastapi_only_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "SRI")
        and not hasattr(python_sri, "DjangoSRI")
        and not hasattr(python_sri, "FlaskSRI")
        and hasattr(python_sri, "FastAPISRI")
        and python_sri.SRI == python_sri.FastAPISRI
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
    )


@pytest.mark.usefixtures("none_installed")
def test_none_installed() -> None:
    import python_sri  # pylint: disable=import-outside-toplevel

    assert (
        hasattr(python_sri, "SRI")
        and not hasattr(python_sri, "DjangoSRI")
        and not hasattr(python_sri, "FlaskSRI")
        and not hasattr(python_sri, "FastAPISRI")
        and hasattr(python_sri, "GenericSRI")
        and hasattr(python_sri, "Headers")
        and python_sri.SRI == python_sri.GenericSRI
    )
