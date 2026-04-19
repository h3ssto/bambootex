# bambootex

Convert pandas DataFrames into publication-quality LaTeX/PDF tables using [tabularray](https://ctan.org/pkg/tabularray).

## Requirements

- Python >= 3.10
- A TeX distribution with `pdflatex` (e.g. [TeX Live](https://tug.org/texlive/))
- The following LaTeX packages: `tabularray`, `siunitx`, `xcolor`, `babel`

## Installation

```bash
pip install bambootex
```

## Quick start

```python
import pandas as pd
from bambootex import Table, Cell, TextFormatter, GradientHighlighter, SimpleHighlighter

df = pd.read_csv("iris.csv")

tbl = Table(
    df,
    columns=["species", "sepal_length", "sepal_width"],
    column_formatters={
        "species": TextFormatter(font=r"\textsf", size=r"\small"),
    },
    headers=[
        [Cell("Species", vspan=2), Cell("Sepal", hspan=2)],
        [Cell(""), Cell("Length"), Cell("Width")],
    ],
    packages=["libertine"],
)

tbl.sort_by("sepal_length")
tbl.highlight("sepal_length", GradientHighlighter("white", "red"))
tbl.to_pdf("output.pdf")
```

## API

### `Table`

```python
Table(
    df,                     # pd.DataFrame
    columns,                # columns to include, in order
    column_formatters=None, # dict of column -> format string or callable
    headers=None,           # list of header rows, each a list of Cell
    packages=None,          # extra LaTeX packages to load
    number_format=".2f",    # default format for float columns
)
```

#### `.sort_by(key, reverse=False)`

Sort rows before rendering. `key` can be:
- a column name: `tbl.sort_by("value")`
- a list of column names: `tbl.sort_by(["group", "value"])`
- a callable applied row-wise: `tbl.sort_by(lambda r: r["a"] - r["b"])`

#### `.highlight(column, highlighter, *fns)`

Highlight cells in `column` using `highlighter`. Optional filter functions `fns` are ANDed together to select which rows to highlight — omit them to highlight all rows.

```python
# All rows, gradient from white to red
tbl.highlight("score", GradientHighlighter("white", "red"))

# Rows matching a condition
tbl.highlight("score", SimpleHighlighter("yellow"), lambda x: x > 90)

# Multiple conditions (ANDed)
tbl.highlight("score", SimpleHighlighter("green"), lambda x: x > 50, lambda x: x < 80)
```

#### `.to_tex(output_path)` / `.to_pdf(output_path)`

Render to a `.tex` file or compile directly to PDF (requires `pdflatex` on `$PATH`).

---

### `Cell`

Defines a header cell, optionally spanning multiple columns or rows.

```python
Cell(
    text,        # cell content
    hspan=1,     # columns to span
    vspan=1,     # rows to span
    align="c",   # tabularray halign: "l", "c", or "r"
)
```

---

### `TextFormatter`

Applies LaTeX font commands to a column's values.

```python
TextFormatter(font=r"\textsf", size=r"\small")
# renders each value as: \small\textsf{value}
```

---

### Highlighters

| Class | Args | Effect |
|---|---|---|
| `SimpleHighlighter` | `color` | Fills matching cells with a flat xcolor color |
| `GradientHighlighter` | `color_min`, `color_max` | Interpolates between two colors based on the cell's relative value |

Colors are plain [xcolor](https://ctan.org/pkg/xcolor) named colors (`"red"`, `"white"`, `"blue!30"`, etc.).  
`GradientHighlighter` colors must be base named colors without `!` mixing, as they are used inside the gradient formula internally.

#### Custom highlighters

Any callable matching `(series: pd.Series) -> dict[index, color_str]` works as a highlighter:

```python
def my_highlighter(series):
    return {idx: "green" if v > 0 else "red" for idx, v in series.items()}

tbl.highlight("delta", my_highlighter)
```
