from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


_LATEX_ESCAPE = str.maketrans({
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
})


def _latex_escape(s: str) -> str:
    return s.translate(_LATEX_ESCAPE)


@dataclass
class NumberFormatter:
    decimal_places: int = 2
    unit: str | None = None
    nan: str | None = None

    def __call__(self, value: float) -> str:
        if self.nan is not None and pd.isna(value):
            return self.nan
        formatted = format(value, f".{self.decimal_places}f")
        return f"{formatted} {self.unit}" if self.unit else formatted


def _as_formatter(fmt: str | Callable) -> Callable:
    if callable(fmt):
        return fmt
    return lambda x: format(x, fmt)


@dataclass
class TextFormatter:
    font: str | list[str] | None = None
    size: str | None = None
    align: str | None = None
    prefix: str = ""
    suffix: str = ""

    def __call__(self, value: str) -> str:
        fonts = self.font if isinstance(self.font, list) else ([self.font] if self.font else [])
        content = f"{self.prefix}{value}{self.suffix}"
        for f in reversed(fonts):
            content = rf"{f}{{{content}}}"
        if self.size:
            content = rf"{self.size}{{{content}}}"
        return content
