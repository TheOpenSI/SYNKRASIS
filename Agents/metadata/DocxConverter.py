from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph


class DocxConverter:
    def __init__(self) -> None:
        self.bullet = "• "
        self.inline = {
            qn("w:t"): lambda node: node.text or "",
            qn("w:tab"): lambda node: "\t",
            qn("w:br"): lambda node: "\n",
        }


    def convert_folders(self, source_folders: list[str]) -> list[Path]:
        written = []
        for folder in source_folders:
            output = self._create_output_folder(folder)
            for path in sorted(Path(folder).iterdir()):
                if path.suffix.lower() != ".docx" or path.name.startswith("~$"):
                    continue
                target = output / f"{path.stem}.txt"
                if target in written:
                    raise ValueError(f"Two documents would write to {target.name}")
                target.write_text(self.convert(path), encoding="utf-8")
                written.append(target)
        if not written:
            raise ValueError(f"No .docx files found in {source_folders}")
        return written

    
    def _create_output_folder(self, folder: str) -> Path:
        output_folder = folder + "_txt"
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        return Path(output_folder)


    def convert(self, path: str | Path) -> str:
        document = Document(str(path))
        lines = [self._line(p, document) for p in document.element.body.iter(qn("w:p"))]
        text = "\n".join(lines)
        if not text.strip():
            raise ValueError(f"{Path(path).name}: no text extracted")
        return text + "\n"


    def _line(self, paragraph: CT_P, document: DocxDocument) -> str:
        text = "".join(self.inline[node.tag](node) for node in paragraph.iter(*self.inline))
        return self.bullet + text if self._is_bullet(paragraph, document) else text


    def _is_bullet(self, paragraph: CT_P, document: DocxDocument) -> bool:
        if "bullet" in Paragraph(paragraph, document._body).style.name.lower():
            return True
        num_pr = paragraph.pPr.numPr if paragraph.pPr is not None else None
        if num_pr is None or num_pr.numId is None:
            return False
        level = num_pr.ilvl.val if num_pr.ilvl is not None else 0
        return self._number_format(document, num_pr.numId.val, level) == "bullet"


    def _number_format(self, document: DocxDocument, num_id: int, level: int) -> str:
        numbering = document.part.numbering_part.element
        abstract_ids = numbering.xpath(f"w:num[@w:numId='{num_id}']/w:abstractNumId/@w:val")
        formats = numbering.xpath(
            f"w:abstractNum[@w:abstractNumId='{abstract_ids[0]}']"
            f"/w:lvl[@w:ilvl='{level}']/w:numFmt/@w:val"
        )
        return formats[0]

if __name__ == "__main__":
    files = DocxConverter().convert_folders(["Agents/data/90_Optometry_Inputs"])