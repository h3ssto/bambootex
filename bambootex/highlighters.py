from typing import Any, Protocol

import pandas as pd


class Highlighter(Protocol):
    def __call__(self, series: pd.Series) -> dict[Any, str]: ...


from dataclasses import dataclass


@dataclass
class SimpleHighlighter:
    color: str

    def __call__(self, series: pd.Series) -> dict[Any, str]:
        return {idx: self.color for idx in series.index}


@dataclass
class GradientHighlighter:
    color_min: str
    color_max: str

    def __call__(self, series: pd.Series) -> dict[Any, str]:
        mn, mx = series.min(), series.max()

        def pct(v):
            return 50 if mx == mn else int(round((v - mn) / (mx - mn) * 100))

        return {
            idx: f"{self.color_max}!{pct(v)}!{self.color_min}"
            for idx, v in series.items()
        }
