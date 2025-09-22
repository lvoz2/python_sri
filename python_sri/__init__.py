"""Entry point to python_sri"""

import sys
from typing import TYPE_CHECKING, Literal, Optional, cast, overload

from .generic_sri import GenericSRI
from .headers import FrozenHeaders, Headers, MutableHeaders

if TYPE_CHECKING:
    from .django_sri import DjangoSRI
    from .fastapi_sri import FastAPISRI
    from .flask_sri import FlaskSRI

__all__ = ["GenericSRI", "FrozenHeaders", "Headers", "MutableHeaders"]
# This cascading try/except is to detect what framework is being used and change the SRI
# class exported to match the desired framework
# Try/except/else: Else block executes if no exceptions are thrown in the try block
try:
    from django.http import HttpResponse
except ImportError:
    pass

try:
    from flask import Flask
except ImportError:
    pass

try:
    from fastapi.staticfiles import StaticFiles
except ImportError:
    pass


mods = set(sys.modules)
_django_inst: Literal[True, False] = "django.http" in mods
_flask_inst: Literal[True, False] = "flask" in mods
_fastapi_inst: Literal[True, False] = "fastapi.staticfiles" in mods

if all((_django_inst, _flask_inst, _fastapi_inst)):
    from .django_sri import DjangoSRI
    from .fastapi_sri import FastAPISRI
    from .flask_sri import FlaskSRI

    __all__ += ["DjangoSRI", "FlaskSRI", "FastAPISRI"]
elif _django_inst and _flask_inst:
    from .django_sri import DjangoSRI
    from .flask_sri import FlaskSRI

    __all__ += ["DjangoSRI", "FlaskSRI"]
elif _flask_inst and _fastapi_inst:
    from .fastapi_sri import FastAPISRI
    from .flask_sri import FlaskSRI

    __all__ += ["FlaskSRI", "FastAPISRI"]
elif _django_inst and _fastapi_inst:
    from .django_sri import DjangoSRI
    from .fastapi_sri import FastAPISRI

    __all__ += ["DjangoSRI", "FastAPISRI"]
elif _django_inst:
    from .django_sri import DjangoSRI

    __all__ += ["DjangoSRI"]
elif _flask_inst:
    from .flask_sri import FlaskSRI

    __all__ += ["FlaskSRI"]
elif _fastapi_inst:
    from .fastapi_sri import FastAPISRI

    __all__ += ["FastAPISRI"]


@overload
def get_sri(
    django_inst: Literal[True], flask_inst: Literal[True], fastapi_inst: Literal[True]
) -> None:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[True], flask_inst: Literal[True], fastapi_inst: Literal[False]
) -> None:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[True], flask_inst: Literal[False], fastapi_inst: Literal[True]
) -> None:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[True], flask_inst: Literal[False], fastapi_inst: Literal[False]
) -> type["DjangoSRI"]:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[False], flask_inst: Literal[True], fastapi_inst: Literal[True]
) -> None:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[False], flask_inst: Literal[True], fastapi_inst: Literal[False]
) -> type["FlaskSRI"]:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[False], flask_inst: Literal[False], fastapi_inst: Literal[True]
) -> type["FastAPISRI"]:
    pass  # pragma: no cover


@overload
def get_sri(
    django_inst: Literal[False],
    flask_inst: Literal[False],
    fastapi_inst: Literal[False],
) -> type["GenericSRI"]:
    pass  # pragma: no cover


def get_sri(
    django_inst: Literal[True, False],
    flask_inst: Literal[True, False],
    fastapi_inst: Literal[True, False],
) -> Optional[
    type["DjangoSRI"] | type["FlaskSRI"] | type["FastAPISRI"] | type["GenericSRI"]
]:
    """Get whatever class SRI will point to if possible, else None

    Required so Mypy knows which one is being used for correct type hinting. See 8
        overloads above for details
    """
    total = int(django_inst) + int(flask_inst) + int(fastapi_inst)
    if total > 1:
        # More than one optional dependency installed
        return None
    if _django_inst:
        return DjangoSRI  # pylint: disable=possibly-used-before-assignment
    if _flask_inst:
        return FlaskSRI  # pylint: disable=possibly-used-before-assignment
    if _fastapi_inst:
        return FastAPISRI  # pylint: disable=possibly-used-before-assignment
    return GenericSRI


sri = get_sri(_django_inst, _flask_inst, _fastapi_inst)
if sri is not None:
    SRI = sri

    __all__ += ["SRI"]
