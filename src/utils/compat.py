"""
Compatibility shim: provides a minimal pydantic-like BaseModel
when pydantic is not installed.
"""
from __future__ import annotations
import copy
from typing import Any


def _to_jsonable(obj: Any) -> Any:
    """Recursively convert BaseModel instances / lists / dicts to plain types."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


try:
    from pydantic import BaseModel
except ImportError:

    class BaseModel:  # type: ignore[no-redef]
        """Minimal pydantic-compatible BaseModel (keyword-init + recursive model_dump)."""

        def __init__(self, **kwargs: Any) -> None:
            for cls in reversed(type(self).__mro__):
                for attr, val in vars(cls).items():
                    if attr.startswith("_") or callable(val):
                        continue
                    if isinstance(val, (classmethod, staticmethod, property)):
                        continue
                    object.__setattr__(self, attr, copy.deepcopy(val))
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

        def model_dump(self) -> dict:
            result = {}
            for k, v in self.__dict__.items():
                if k.startswith("_"):
                    continue
                result[k] = _to_jsonable(v)
            return result

        def dict(self) -> dict:
            return self.model_dump()
