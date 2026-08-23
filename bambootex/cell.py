from dataclasses import dataclass


@dataclass
class Cell:
    text: str
    hspan: int = 1
    vspan: int = 1
    align: str = "c"
    font: str | None = None
    valign: str | None = None
    bg: str | None = None

    def to_latex(self) -> str:
        if not self.text:
            return ""
        content = rf"{self.font}{{{self.text}}}" if self.font else self.text
        align_parts = [self.align]
        if self.valign:
            align_parts.append(self.valign)
        if self.bg:
            align_parts.append(f"bg={self.bg}")
        align = ",".join(align_parts)
        if self.hspan == 1 and self.vspan == 1:
            return rf"\SetCell{{{align}}}{{{content}}}"
        if self.vspan == 1:
            return rf"\SetCell[c={self.hspan}]{{{align}}}{{{content}}}"
        return rf"\SetCell[c={self.hspan}, r={self.vspan}]{{{align}}}{{{content}}}"
