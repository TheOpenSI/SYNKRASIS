from __future__ import annotations

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from pathlib import Path

import fitz

from services.RAG.DocumentProcessor.PymuProcessor import PymuProcessor
from services.RAG.models import Chunk


class DocumentChunker:
    """
    Chunks a PDF document into fixed-size text chunks with citation
    metadata derived from font structure analysis.

    The pipeline is:
        1. Analyse the document with PymuProcessor to build a roles dict
           mapping integer font sizes to structural roles.
        2. Walk the PDF span by span in reading order, tracking the
           current heading context at each level and accumulating body
           and heading text into a buffer.
        3. When the buffer reaches the chunk size, emit a Chunk with the
           heading context active at the start of that chunk, then carry
           the last overlap_chars into the next buffer.

    Spans classified as 'small' are skipped entirely. All other content
    including heading text is included in the buffer so heading text
    appears in the chunk it introduces.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap_chars: int = 200,
        heading_levels: int = 3,
        threshold: int | float = 0.005,
    ) -> None:
        """
        Initialise the DocumentChunker.

        Args:
            chunk_size: Target character count per chunk.
            overlap_chars: Number of characters to carry over from the
                end of one chunk into the start of the next.
            heading_levels: Number of heading levels to detect, passed
                through to FontInspector.classify_sizes().
            threshold: Minimum character count threshold for a font size
                to qualify as a heading level. Float is treated as a
                fraction of body char count; int is absolute.
        """
        self._chunk_size: int = chunk_size
        self._overlap_chars: int = overlap_chars
        self._heading_levels: int = heading_levels
        self._threshold: int | float = threshold
        self._inspector: PymuProcessor = PymuProcessor()


    def chunk(self, filepath: str | Path) -> list[Chunk]:
        """
        Process a PDF into a list of Chunks with citation metadata.

        This is the single public entry point. It runs font analysis,
        then walks the document collecting text into fixed-size chunks
        with overlap. Any remaining text in the buffer after the last
        page is emitted as a final chunk regardless of size.

        Args:
            filepath: Path to the PDF file.

        Returns:
            A list of Chunk objects in document order.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be opened as a PDF.
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"PDF not found: {filepath}")
        
        variants = self._inspector.inspect(filepath)
        roles: dict[int, str] = self._inspector.classify_sizes(
            variants,
            heading_levels=self._heading_levels,
            threshold=self._threshold,
        )

        document_name: str = filepath.name
        document_title: str = self._detect_title(variants, roles, filepath)

        doc: fitz.Document = fitz.open(str(filepath))

        chunks: list[Chunk] = []
        chunk_index: int = 0

        buffer: str = ""
        buffer_page_start: int = 1

        current_heading_1: str = ""
        current_heading_2: str = ""
        current_heading_3: str = ""

        chunk_heading_1: str = ""
        chunk_heading_2: str = ""
        chunk_heading_3: str = ""

        for page in doc:
            page_number: int = page.number + 1
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text: str = span["text"].strip()
                        if not text:
                            continue

                        role: str = self._inspector._get_role_for_size(
                            span["size"], roles
                        )

                        if role in ("small", "ignored", "title"):
                            continue

                        if role == "heading_1":
                            current_heading_1 = text
                            current_heading_2 = ""
                            current_heading_3 = ""

                        elif role == "heading_2":
                            current_heading_2 = text
                            current_heading_3 = ""

                        elif role == "heading_3":
                            current_heading_3 = text

                        if not buffer:
                            buffer_page_start = page_number
                            chunk_heading_1 = current_heading_1
                            chunk_heading_2 = current_heading_2
                            chunk_heading_3 = current_heading_3

                        buffer += text + " "

                        if len(buffer) >= self._chunk_size:
                            chunks.append(
                                Chunk(
                                    text=buffer.strip(),
                                    document_name=document_name,
                                    document_title=document_title,
                                    chunk_index=chunk_index,
                                    chunk_method="fixed",
                                    page_start=buffer_page_start,
                                    page_end=page_number,
                                    heading_1=chunk_heading_1,
                                    heading_2=chunk_heading_2,
                                    heading_3=chunk_heading_3,
                                )
                            )

                            chunk_index += 1
                            overlap_text: str = buffer[-self._overlap_chars:]
                            buffer = overlap_text
                            buffer_page_start = page_number
                            chunk_heading_1 = current_heading_1
                            chunk_heading_2 = current_heading_2
                            chunk_heading_3 = current_heading_3

        if buffer.strip():
            chunks.append(
                Chunk(
                    text=buffer.strip(),
                    document_name=document_name,
                    document_title=document_title,
                    chunk_index=chunk_index,
                    chunk_method="fixed",
                    page_start=buffer_page_start,
                    page_end=page_number,
                    heading_1=chunk_heading_1,
                    heading_2=chunk_heading_2,
                    heading_3=chunk_heading_3,
                )
            )

        doc.close()

        return chunks


    def _detect_title(
        self,
        variants: list,
        roles: dict[int, str],
        filepath: Path,
    ) -> str:
        """
        Extract the document title by finding the first span in the
        document whose font size maps to the 'title' role.

        Falls back to the filename stem if no title span is found.

        Args:
            variants: Font variants from FontInspector.inspect().
            roles: Role dict from FontInspector.classify_sizes().
            filepath: Path to the PDF, used for the fallback title.

        Returns:
            The document title as a string.
        """
        title_candidates: list[str] = []
        doc: fitz.Document = fitz.open(str(filepath))

        for page in doc:
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text: str = span["text"].strip()
                        if not text:
                            continue

                        role: str = self._inspector._get_role_for_size(
                            span["size"], roles
                        )

                        if role == "title":
                            title_candidates.append(text)

        doc.close()
        return " ".join(title_candidates) if title_candidates else filepath.stem


if __name__ == "__main__":
    chunker = DocumentChunker(chunk_size=3000)
    chunks = chunker.chunk("services/RAG/sample/Academic Governance Handbook 2025.pdf")

    for chunk in chunks[:20]:
        print(f"--- chunk {chunk.chunk_index} | pages {chunk.page_start}-{chunk.page_end} ---")
        print(f"h1: {chunk.heading_1}")
        print(f"h2: {chunk.heading_2}")
        print(f"h3: {chunk.heading_3}")
        print(f"title: {chunk.document_title}")
        print(f"name: {chunk.document_name}")
        print()
        print(chunk.text[:200])
        print()