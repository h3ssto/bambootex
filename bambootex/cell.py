from dataclasses import dataclass


@dataclass
class Cell:
    text: str
    hspan: int = 1
    vspan: int = 1
    align: str = "c"
    font: str | None = None

    def to_latex(self) -> str:
        if not self.text:
            return ""
        content = rf"{self.font}{{{self.text}}}" if self.font else self.text
        if self.hspan == 1 and self.vspan == 1:
            return rf"\SetCell{{{self.align}}}{{{content}}}"
        if self.vspan == 1:
            return rf"\SetCell[c={self.hspan}]{{{self.align}}}{{{content}}}"
        return rf"\SetCell[c={self.hspan}, r={self.vspan}]{{{self.align}}}{{{content}}}"
