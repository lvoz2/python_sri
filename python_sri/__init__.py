"""Entry point to python_sri"""

import sys
from typing import cast

from .generic_sri import GenericSRI
from .sri import Headers

__all__ = ["GenericSRI", "Headers"]
# This cascading try/except is to detect what framework is being used and change the SRI
# class exported to match the desired framework
# Try/except/else: Else block executes if no exceptions are thrown in the try block
try:
    from django import http
except ImportError:
    pass

try:
    from flask import Flask
except ImportError:
    pass

try:
    from fastapi import staticfiles
except ImportError:
    pass

mods = set(sys.modules)
_django_inst = "django.http" in mods
_flask_inst = "flask" in mods
_fastapi_inst = "fastapi.staticfiles" in mods

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

    SRI: DjangoSRI = DjangoSRI  # type: ignore[assignment]
    __all__ += ["SRI", "DjangoSRI"]
elif _flask_inst:
    from .flask_sri import FlaskSRI

    SRI: FlaskSRI = FlaskSRI  # type: ignore[no-redef]
    __all__ += ["SRI", "FlaskSRI"]
elif _fastapi_inst:
    from .fastapi_sri import FastAPISRI

    SRI: FastAPISRI = FastAPISRI  # type: ignore[no-redef]
    __all__ += ["SRI", "FastAPISRI"]
else:
    SRI: GenericSRI = GenericSRI  # type: ignore[no-redef]

    __all__ += ["SRI"]
