from __future__ import annotations

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

from dataclasses import dataclass

@dataclass
class FontVariant:
    """
    A unique combination of font properties observed in the document.

    Each distinct (font_name, font_size, is_bold, is_italic) combination
    gets its own FontVariant. Character count is accumulated across all
    spans that share the same combination.

    Attributes:
        font_name: The font family name as reported by PyMuPDF.
        font_size: Font size in points, rounded to one decimal place.
        is_bold: True if the bold flag is set on the font.
        is_italic: True if the italic flag is set on the font.
        char_count: Total number of characters seen with this combination
            across the entire document.
        sample_text: A short excerpt of text seen with this combination,
            useful for visually confirming what role this variant plays.
    """

    font_name: str
    font_size: float
    is_bold: bool
    is_italic: bool
    char_count: int = 0
    # sample_text: str = ""


@dataclass
class ExtractedItem:
    """
    A single content element extracted from a document, with full citation
    metadata.

    This is the primary output of the DocumentProcessor. Each item maps
    to one logical element in the source document — a paragraph, heading,
    table, image caption, list item, footnote, or similar — as identified
    by Docling's layout analysis.

    Attributes:
        text: The text content of the element. For tables this is the
            Markdown representation. Empty string if not applicable.
        document_name: The filename of the source document.
        document_title: The title extracted from document metadata, or an
            empty string if not available.
        item_label: Docling's label for the element type, e.g. 'text',
            'section_header', 'table', 'picture', 'list_item', 'footnote',
            'caption', 'code'.
        section_heading: The text of the nearest preceding section heading
            at any level. Empty string if no heading has been seen yet.
        heading_level: The hierarchical level of the nearest preceding
            heading (1, 2, or 3). None if no heading has been seen yet.
        page_start: Page number where this element begins (1-indexed).
            None if provenance is unavailable.
        page_end: Page number where this element ends (1-indexed). Equals
            page_start for single-page elements. None if unavailable.
        char_span: Character offset span [start, end] within the page
            text stream, as reported by Docling. None if unavailable.
    """

    text: str
    document_name: str
    document_title: str
    item_label: str
    section_heading: str
    heading_level: int | None
    page_start: int | None
    page_end: int | None
    char_span: tuple[int, int] | None
    
    
@dataclass
class Chunk:
    """
    A chunk of document text with full citation metadata.

    Produced by the DocumentChunker after walking the PDF in reading
    order. Each chunk carries the heading context that was active when
    the chunk was collected, along with page range and document identity
    information for downstream citation.

    Attributes:
        text: The chunk text, may include heading text and body text.
        document_name: The filename of the source PDF.
        document_title: The title detected from the largest font size in
            the document, may differ from document_name.
        chunk_index: Zero-based position of this chunk in document order.
        chunk_method: The chunking strategy used, e.g. 'fixed'.
        page_start: Page number where this chunk begins (1-indexed).
        page_end: Page number where this chunk ends (1-indexed).
        heading_1: Text of the first heading_1 encountered in this chunk.
            Empty string if no heading_1 context exists.
        heading_2: Text of the first heading_2 encountered in this chunk.
            Empty string if no heading_2 context exists.
        heading_3: Text of the first heading_3 encountered in this chunk.
            Empty string if no heading_3 context exists.
    """

    text: str
    document_name: str
    document_title: str
    chunk_index: int
    chunk_method: str
    page_start: int
    page_end: int
    heading_1: str
    heading_2: str
    heading_3: str