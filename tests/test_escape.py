import tempfile
import pandas as pd
import pytest
from bambootex import Table, Cell


def tex_content(df, columns, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".tex", mode="r", delete=False) as f:
        path = f.name
    t = Table(df, columns, **kwargs)
    t.to_tex(path)
    with open(path) as f:
        return f.read()


def test_underscore_escaped_in_string_column():
    df = pd.DataFrame({"name": ["test_test"]})
    content = tex_content(df, ["name"])
    assert r"test\_test" in content
    assert "test_test" not in content.replace(r"test\_test", "")


def test_underscore_escaped_with_text_formatter():
    from bambootex import TextFormatter
    df = pd.DataFrame({"name": ["test_test"]})
    content = tex_content(df, ["name"], column_formatters={"name": TextFormatter(font=r"\textsf")})
    assert r"test\_test" in content
    assert "test_test" not in content.replace(r"test\_test", "")
