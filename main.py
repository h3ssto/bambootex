import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from os import linesep
from typing import Callable

import pandas as pd


def _as_formatter(fmt: str | Callable) -> Callable:
    if callable(fmt):
        return fmt
    return lambda x: format(x, fmt)


@dataclass
class TextFormatter:
    font: str | None = None
    size: str | None = None

    def __call__(self, value: str) -> str:
        prefix = (self.size or "") + (self.font or "")
        return fr"{prefix}{{{value}}}" if prefix else str(value)


@dataclass
class Cell:
    text: str
    hspan: int = 1
    vspan: int = 1
    align: str = "c"

    def to_latex(self) -> str:
        if not self.text:
            return ""
        if self.hspan == 1 and self.vspan == 1:
            return fr"\thead{{{self.text}}}"
        if self.vspan == 1:
            return fr"\SetCell[c={self.hspan}]{{{self.align}}}{{\thead{{{self.text}}}}}"
        return fr"\SetCell[c={self.hspan}, r={self.vspan}]{{{self.align}}}{{\thead{{{self.text}}}}}"


class Table:

    def __init__(
        self,
        df: pd.DataFrame,
        columns: list[str],
        column_aligns: str | list[str] | None = None,
        column_formatters: dict[str, str | Callable] | None = None,
        headers: list[list[Cell]] | None = None,
        vlines: list[int] | None = None,
        packages: list[str] | None = None,
        number_format: str = ".2f",
    ):
        self.df = df.copy()

        for col in columns:
            if isinstance(col, str) and col not in df:
                raise ValueError(f"Column name {col!r} not in data frame.")

        self.columns = columns
        self.column_aligns = column_aligns
        self.column_formatters = column_formatters
        self.headers = headers
        self.vlines = vlines
        self.packages = packages or []
        self.number_format = number_format
        self._highlights: list[tuple[str, Callable, str]] = []

    def highlight(self, column: str, fn: Callable, color: str) -> "Table":
        self._highlights.append((column, fn, color))
        return self

    def _build_colspec(self) -> str:
        if self.column_aligns == "auto":
            alignments = [
                "l" if pd.api.types.is_string_dtype(self.df[col]) else "r"
                for col in self.columns
            ]
        elif self.column_aligns:
            alignments = list(self.column_aligns)
        else:
            alignments = ["l"] * len(self.columns)

        if self.vlines:
            inc = 0
            for v in sorted(self.vlines):
                if v < 0:
                    alignments.append("|")
                else:
                    alignments.insert(v + inc, "|")
                    inc += 1

        return "".join(alignments)

    def _build_preamble(self, colspec: str) -> str:
        pkgs = r"\usepackage{makecell}\usepackage{xcolor}\usepackage{tabularray}"
        for pkg in self.packages:
            pkgs += fr"\usepackage{{{pkg}}}"
        return fr"\documentclass{{standalone}}{pkgs}\begin{{document}}\begin{{tblr}}{{colspec = {{{colspec}}}}}\hline"

    def _build_headers(self) -> list[str]:
        if not self.headers:
            return []

        lines = []
        for header in self.headers:
            cells = [cell.to_latex() for cell in header]
            lines.append(f"&{linesep}".join(cells) + r"\\")

        lines[-1] += r"\hline"
        return lines

    def _compute_highlights(self, df: pd.DataFrame) -> dict[tuple[int, str], str]:
        highlights: dict[tuple[int, str], str] = {}
        for col, fn, color in self._highlights:
            result = fn(df[col])
            mask = result if isinstance(result, pd.Series) else df[col] == result
            for idx in df.index[mask]:
                highlights[(idx, col)] = color
        return highlights

    def _build_content(self, df: pd.DataFrame, highlights: dict[tuple[int, str], str]) -> list[str]:
        rows = []
        for idx, row in df.iterrows():
            cells = [
                fr"\SetCell{{bg={highlights[(idx, col)]}}} {row[col]}"
                if (idx, col) in highlights else str(row[col])
                for col in self.columns
            ]
            rows.append("&".join(cells) + r"\\")
        return rows

    def to_tex(self, output_path: str):
        df = self.df.copy()
        highlights = self._compute_highlights(df)
        formatters = {
            col: _as_formatter(self.number_format)
            for col in self.columns
            if pd.api.types.is_float_dtype(df[col])
        }
        if self.column_formatters:
            formatters.update({col: _as_formatter(fmt) for col, fmt in self.column_formatters.items()})
        for col, fmt in formatters.items():
            df[col] = df[col].apply(fmt)

        colspec = self._build_colspec()
        pre = self._build_preamble(colspec)
        post = r"\end{tblr}\end{document}"
        lines = [pre, *self._build_headers(), *self._build_content(df, highlights), post]

        with open(output_path, "w+") as fp:
            fp.writelines(line + linesep for line in lines)

    def to_pdf(self, output_path: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "table.tex")
            self.to_tex(tex_path)
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"pdflatex failed:\n{result.stdout}")
            shutil.copy(os.path.join(tmpdir, "table.pdf"), output_path)


def main():
    df = pd.read_csv("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv")

    tbl = Table(
        df,
        columns=["species", "sepal_length", "sepal_width"],
        column_aligns="auto",
        column_formatters=dict(species=TextFormatter(font=r"\textsf", size=r"\small")),
        headers=[
            [Cell("Species", vspan=2), Cell("Sepal", hspan=2)],
            [Cell(""), Cell("Length"), Cell("Width")],
        ],
        vlines=[0, 1, -1],
        packages=["libertine"],
    )

    tbl.highlight("sepal_length", lambda x: x > 4.5, "red!25")
    tbl.to_pdf("output.pdf")


if __name__ == "__main__":
    main()
