# bambootex

Convert pandas DataFrames into LaTeX/PDF tables using [tabularray](https://ctan.org/pkg/tabularray).

## Requirements

- Python >= 3.11
- A TeX distribution with `pdflatex` (e.g. [TeX Live](https://tug.org/texlive/))
- The following LaTeX packages: `tabularray`, `siunitx`, `xcolor`, `babel`, `lmodern`

## Installation

```bash
pip install bambootex
```

## Quick start

```python
import pandas as pd
from bambootex import Table, Cell, Font, Size, TextFormatter, GradientHighlighter, SimpleHighlighter

df = pd.read_csv("iris.csv")

tbl = Table(
    df,
    columns=["species", "sepal_length", "sepal_width"],
    column_formatters={
        "species": TextFormatter(font=Font.sf, size=Size.small),
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
    df,                      # pd.DataFrame
    columns,                 # columns to include, in order
    column_formatters=None,  # dict of column -> format string, NumberFormatter, or TextFormatter
    headers=None,            # list of header rows, each a list of Cell
    packages=None,           # extra LaTeX packages to load
    number_format=".2f",     # default format for float columns (str or NumberFormatter)
    vlines=None,             # list of column indices to draw a vertical line after
    hlines=None,             # list of row indices to draw a horizontal line after
    default_size=None,       # document-wide font size (str or Size)
)
```

#### `.sort_by(key, reverse=False)`

Sort rows before rendering. `key` can be a column name, list of column names, or a row-wise callable.

#### `.highlight(column, highlighter, *fns)`

Highlight cells in one or more columns.

- **Single column** (`column: str`): filter functions receive the full column series.
- **Multiple columns** (`column: list[str]`): a single predicate `(value, row_subset) -> bool` selects which cells to highlight per row.

```python
# Gradient across all rows
tbl.highlight("score", GradientHighlighter("white", "red"))

# Highlight minimum per row across columns
tbl.highlight(
    ["time_a", "time_b", "time_c"],
    SimpleHighlighter("green!25"),
    lambda v, row: v == row.min(),
)
```

#### `.to_tex(output_path)` / `.to_pdf(output_path)`

Render to a `.tex` file or compile directly to PDF (requires `pdflatex` on `$PATH`).

---

### `Cell`

Defines a header cell.

```python
Cell(
    text,        # cell content
    hspan=1,     # columns to span
    vspan=1,     # rows to span
    align="c",   # tabularray halign: "l", "c", or "r"
    font=None,   # LaTeX font command, e.g. Font.tt or r"\texttt"
)
```

---

### `TextFormatter`

Applies LaTeX styling to a column's string values. When `align` is set, it also controls the column's alignment in the colspec.

```python
TextFormatter(
    font=Font.sf,       # font command or list of font commands
    size=Size.small,    # size command
    align="c",          # column alignment ("l", "c", "r")
    prefix="(",         # prepended to each value
    suffix=")",         # appended to each value
)
```

---

### `NumberFormatter`

Controls formatting of numeric columns.

```python
NumberFormatter(
    decimal_places=2,   # decimal places
    unit=None,          # unit string appended after value
    nan=None,           # string to substitute for NaN values (e.g. "--")
)
```

---

### `Font`

```python
Font.rm   # \textrm
Font.sf   # \textsf
Font.tt   # \texttt
Font.bf   # \textbf
Font.it   # \textit
```

---

### `Size`

```python
Size.tiny / Size.scriptsize / Size.footnotesize / Size.small / Size.normalsize
Size.large / Size.Large / Size.LARGE / Size.huge / Size.Huge
```

---

### Highlighters

| Class | Args | Effect |
|---|---|---|
| `SimpleHighlighter` | `color` | Fills matching cells with a flat xcolor color |
| `GradientHighlighter` | `color_min`, `color_max` | Interpolates between two colors based on relative value |

Any callable matching `(series: pd.Series) -> dict[index, color_str]` also works as a highlighter.
