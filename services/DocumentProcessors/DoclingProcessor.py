## TEST ONLY, DO NOT USE ##

from __future__ import annotations

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

from pathlib import Path

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel

from services.DocumentProcessors.doc_data_models import ExtractedItem


class DocumentProcessor:
    """
    Converts a document file into a flat list of extracted items using
    Docling, preserving full citation metadata on each item.

    This is the first stage of the RAG pipeline. It does not chunk,
    merge, or split content — it produces one ExtractedItem per logical
    document element exactly as Docling identifies them. Chunking is
    applied separately in a later stage.

    Docling handles structure detection, reading order, header/footer
    removal, and heading hierarchy. This class maps that output onto the
    ExtractedItem model and tracks the current section heading as the
    document is traversed.
    """

    _HEADING_LABELS: frozenset[str] = frozenset({
        str(DocItemLabel.SECTION_HEADER),
        str(DocItemLabel.TITLE),
    })

    _HEADING_LEVEL_MAP: dict[str, int] = {
        str(DocItemLabel.TITLE): 1,
        str(DocItemLabel.SECTION_HEADER): 2,
    }


    def __init__(self) -> None:
        """
        Initialise the DocumentProcessor.

        The Docling DocumentConverter is instantiated once and reused
        across calls to process(), so model weights are loaded only on
        the first conversion.
        """
        self._converter = DocumentConverter()


    def process(self, filepath: str | Path) -> list[ExtractedItem]:
        """
        Convert a document into a list of ExtractedItems with citation
        metadata.

        This is the single public entry point. It loads the document via
        Docling, extracts the document title from metadata, then walks
        every content item in reading order. Section headings are tracked
        as the document is traversed and attached to each subsequent item
        until the next heading is encountered.

        Args:
            filepath: Path to the document file. Docling supports PDF,
                DOCX, PPTX, HTML, Markdown, and several other formats.

        Returns:
            A list of ExtractedItem objects in document reading order.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Document not found: {filepath}")

        result = self._converter.convert(str(filepath))
        doc = result.document

        document_name: str = filepath.name
        document_title: str = self._extract_title(doc)

        items: list[ExtractedItem] = []
        current_heading: str = ""
        current_heading_level: int | None = None

        for item, _level in doc.iterate_items():
            label: str = str(item.label)

            if label in self._HEADING_LABELS:
                current_heading = item.text.strip() if hasattr(item, "text") else ""
                current_heading_level = self._HEADING_LEVEL_MAP.get(label)
                continue

            text: str = item.text.strip() if hasattr(item, "text") else ""
            page_start, page_end, char_span = self._extract_provenance(item)

            items.append(
                ExtractedItem(
                    text=text,
                    document_name=document_name,
                    document_title=document_title,
                    item_label=label,
                    section_heading=current_heading,
                    heading_level=current_heading_level,
                    page_start=page_start,
                    page_end=page_end,
                    char_span=char_span,
                )
            )

        return items


    def _extract_title(self, doc: object) -> str:
        """
        Extract the document title from Docling metadata.

        Docling exposes metadata via doc.name and doc.origin. The origin
        object carries the original filename; the name field is the
        document identifier set during conversion. Neither is a true
        semantic title, so we look for the first TITLE-labelled item in
        the document body as the primary source, falling back to doc.name.

        Args:
            doc: The DoclingDocument returned by the converter.

        Returns:
            The document title as a string, or an empty string if not
            found.
        """
        for item, _level in doc.iterate_items():
            if str(item.label) == str(DocItemLabel.TITLE):
                return item.text.strip() if hasattr(item, "text") else ""

        return getattr(doc, "name", "") or ""


    def _extract_provenance(
        self, item: object
    ) -> tuple[int | None, int | None, tuple[int, int] | None]:
        """
        Extract page numbers and character span from a Docling item's
        provenance list.

        Docling stores provenance as a list to handle elements that span
        page boundaries. page_start comes from the first provenance entry
        and page_end from the last.

        Args:
            item: Any item returned by doc.iterate_items().

        Returns:
            A tuple of (page_start, page_end, char_span), where any
            value may be None if provenance is absent.
        """
        prov_list = getattr(item, "prov", [])

        if not prov_list:
            return None, None, None

        first = prov_list[0]
        last = prov_list[-1]

        page_start: int = first.page_no
        page_end: int = last.page_no

        raw_charspan = getattr(first, "charspan", None)
        char_span: tuple[int, int] | None = (
            (raw_charspan[0], raw_charspan[1]) if raw_charspan is not None else None
        )

        return page_start, page_end, char_span
    
    
if __name__ == "__main__":
    dp = DocumentProcessor()
    items = dp.process("services/RAG/sample/Academic Governance Handbook 2025.pdf")
    for item in items:
        print(f"{item.document_name=}")
        print(f"{item.document_title=}")
        print(f"{item.item_label=}")
        print(f"{item.section_heading=}")
        print(f"{item.heading_level=}")
        print("\n")