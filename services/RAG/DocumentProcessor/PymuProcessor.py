from __future__ import annotations

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

from pathlib import Path
import fitz

from services.RAG.models import FontVariant


class PymuProcessor:
    BOLD_FLAG: int = 1 << 4
    ITALIC_FLAG: int = 1 << 1


    def inspect(self, filepath: str | Path) -> list[FontVariant]:
        """
        Extract all font variants from a PDF, ranked by character count
        in descending order.

        Font sizes are truncated to int for grouping, so 13.0, 13.3, and
        13.6 are all counted under size class 13.

        Args:
            filepath: Path to the PDF file.

        Returns:
            A list of FontVariant objects sorted by char_count descending.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be opened as a PDF.
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"PDF not found: {filepath}")

        doc: fitz.Document = fitz.open(str(filepath))

        if doc.is_encrypted:
            raise ValueError(f"PDF is encrypted and cannot be processed: {filepath}")

        variants: dict[tuple, FontVariant] = {}

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

                        font_name: str = span["font"]
                        font_size: int = int(span["size"])
                        flags: int = span["flags"]
                        is_bold: bool = bool(flags & self.BOLD_FLAG)
                        is_italic: bool = bool(flags & self.ITALIC_FLAG)

                        key: tuple = (font_name, font_size, is_bold, is_italic)

                        if key not in variants:
                            variants[key] = FontVariant(
                                font_name=font_name,
                                font_size=font_size,
                                is_bold=is_bold,
                                is_italic=is_italic,
                            )

                        variants[key].char_count += len(text)

        doc.close()

        return sorted(variants.values(), key=lambda v: v.char_count, reverse=True)


    def classify_sizes(
        self,
        variants: list[FontVariant],
        heading_levels: int = 3,
        threshold: int | float = 0.005) -> dict[int, str]:
        """
        Classify integer-truncated font sizes into structural roles.

        All font sizes are already stored as int after inspect(). Character
        counts are summed across bold and italic variants at the same size.
        The most frequent size is body. Sizes below body are small. Sizes
        above body are filtered by threshold then assigned heading levels
        from largest downward. The single largest qualifying size is
        assigned the role 'title'.

        Args:
            variants: The list returned by inspect().
            heading_levels: Number of heading levels to assign, default 3.
            threshold: Minimum character count for a size to qualify as a
                heading level. Float is treated as a fraction of body char
                count; int is treated as an absolute value.

        Returns:
            A dict mapping integer font size to role string. Possible roles
            are 'title', 'heading_1' through 'heading_N', 'body', 'small',
            and 'ignored'.
        """
        size_char_counts: dict[int, int] = {}

        for variant in variants:
            size: int = int(variant.font_size)
            size_char_counts[size] = size_char_counts.get(size, 0) + variant.char_count

        body_size: int = max(size_char_counts, key=lambda s: size_char_counts[s])
        body_char_count: int = size_char_counts[body_size]

        min_chars: int = (
            int(body_char_count * threshold)
            if isinstance(threshold, float)
            else threshold
        )

        sizes_above_body: list[int] = sorted(
            [size for size in size_char_counts if size > body_size],
            reverse=True,
        )

        roles: dict[int, str] = {}

        for size in size_char_counts:
            if size < body_size:
                roles[size] = "small"
            elif size == body_size:
                roles[size] = "body"
            else:
                roles[size] = "ignored"

        if sizes_above_body:
            title_size: int = sizes_above_body[0]
            roles[title_size] = "title"

            heading_candidates: list[int] = [
                size for size in sizes_above_body[1:]
                if size_char_counts[size] >= min_chars
            ]

            for index, size in enumerate(heading_candidates[:heading_levels]):
                roles[size] = f"heading_{index + 1}"

        return roles


    def _get_role_for_size(
        self, span_size: float, roles: dict[int, str]
    ) -> str:
        """
        Resolve the structural role for a span's actual float font size.

        Uses int() truncation to map the float size to its size class,
        then looks that class up in the roles dict. This ensures that
        13.0, 13.3, and 13.6 all resolve to the same class as 13.

        Args:
            span_size: The raw float font size from PyMuPDF.
            roles: The role dict returned by classify_sizes().

        Returns:
            The role string for this size, or 'ignored' if not found.
        """
        return roles.get(int(span_size), "ignored")


    def collect_text_by_variant(self, filepath: str | Path) -> dict[tuple, list[str]]:
        """
        Collect all text lines from a PDF grouped by font variant key.

        Lines are preserved in document reading order within each group.
        An empty string is inserted between blocks to preserve visual
        separation between paragraphs and headings.

        Args:
            filepath: Path to the PDF file.

        Returns:
            A dict mapping (font_name, font_size, is_bold, is_italic) to
            a list of text lines in reading order.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be opened as a PDF.
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"PDF not found: {filepath}")

        doc: fitz.Document = fitz.open(str(filepath))

        if doc.is_encrypted:
            raise ValueError(f"PDF is encrypted and cannot be processed: {filepath}")

        texts: dict[tuple, list[str]] = {}

        for page in doc:
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    line_parts: dict[tuple, list[str]] = {}

                    for span in line.get("spans", []):
                        text: str = span["text"].strip()
                        if not text:
                            continue

                        font_name: str = span["font"]
                        font_size: int = int(span["size"])
                        flags: int = span["flags"]
                        is_bold: bool = bool(flags & self.BOLD_FLAG)
                        is_italic: bool = bool(flags & self.ITALIC_FLAG)

                        key: tuple = (font_name, font_size, is_bold, is_italic)

                        if key not in line_parts:
                            line_parts[key] = []
                        line_parts[key].append(text)

                    for key, parts in line_parts.items():
                        if key not in texts:
                            texts[key] = []
                        texts[key].append(" ".join(parts))

                for key in texts:
                    if texts[key] and texts[key][-1] != "":
                        texts[key].append("")

        doc.close()

        return texts


    def print_structure(
        self,
        filepath: str | Path,
        heading_levels: int = 3,
        threshold: int | float = 0.005,
    ) -> None:
        """
        Print a structural representation of the document for verification.

        Walks the PDF in reading order and prints each block according to
        its classified role. Title and heading blocks print their actual
        text with indentation reflecting their level. Body blocks print
        the placeholder 'body text' once per heading zone — consecutive
        body blocks under the same heading are suppressed.

        Page numbers are printed as a prefix on every line.

        The output format is:

            1   | Document Title

            4   | Heading 1
            4   |   body text

            5   |   Heading 2
            5   |     body text

        Args:
            filepath: Path to the PDF file.
            heading_levels: Number of heading levels to classify.
            threshold: Minimum char count threshold for heading candidates.
                Float is a fraction of body char count; int is absolute.
        """
        filepath = Path(filepath)
        variants: list[FontVariant] = self.inspect(filepath)
        roles: dict[int, str] = self.classify_sizes(variants, heading_levels, threshold)

        indent_map: dict[str, str] = {
            "title":     "",
            "heading_1": "  ",
            "heading_2": "    ",
            "heading_3": "      ",
            "heading_4": "        ",
            "body":      "  ",
        }

        doc: fitz.Document = fitz.open(str(filepath))

        last_printed_body_after: str | None = None

        for page in doc:
            page_number: int = page.number + 1
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue

                block_lines: list[str] = []
                block_role: str | None = None

                for line in block.get("lines", []):
                    line_text_parts: list[str] = []

                    for span in line.get("spans", []):
                        text: str = span["text"].strip()
                        if not text:
                            continue

                        role: str = self._get_role_for_size(span["size"], roles)

                        if block_role is None:
                            block_role = role

                        line_text_parts.append(text)

                    if line_text_parts:
                        block_lines.append(" ".join(line_text_parts))

                if block_role is None or block_role in ("ignored", "small"):
                    continue

                indent: str = indent_map.get(block_role, "  ")
                prefix: str = f"{page_number:<3} | {indent}"

                if block_role == "body":
                    if last_printed_body_after != "body":
                        print(f"{prefix}body text")
                        last_printed_body_after = "body"
                else:
                    print()
                    for line in block_lines:
                        print(f"{prefix}{line}")
                    last_printed_body_after = block_role

        doc.close()

        
    def dump_spans(
        self,
        filepath: str | Path,
        pages: int | list[int] | None = None) -> None:
        """
        Print raw span metadata for every text span in the specified pages.

        No filtering, classification, or threshold logic is applied — this
        is a pure diagnostic tool to inspect exactly what PyMuPDF sees.

        Args:
            filepath: Path to the PDF file.
            pages: A single page number (1-indexed), a list of page numbers,
                or None to dump all pages.
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"PDF not found: {filepath}")

        doc: fitz.Document = fitz.open(str(filepath))

        if isinstance(pages, int):
            page_indices = [pages - 1]
        elif isinstance(pages, list):
            page_indices = [p - 1 for p in pages]
        else:
            page_indices = list(range(len(doc)))

        for page_index in page_indices:
            page = doc[page_index]
            page_number = page_index + 1
            print(f"\n--- Page {page_number} ---")

            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text: str = span["text"].strip()
                        if not text:
                            continue

                        font_name: str = span["font"]
                        font_size: float = span["size"]
                        flags: int = span["flags"]
                        is_bold: bool = bool(flags & self.BOLD_FLAG)
                        is_italic: bool = bool(flags & self.ITALIC_FLAG)

                        print(
                            f"  size={font_size:.2f}"
                            f"  bold={is_bold}"
                            f"  italic={is_italic}"
                            f"  font='{font_name}'"
                            f"  text='{text}'"
                        )

        doc.close()
        
if __name__ == "__main__":
    pm = PymuProcessor()
    pm.print_structure(
        filepath="services/RAG/sample/Academic Governance Handbook 2025.pdf",
        heading_levels=3,
        threshold=0.005,
    )
    # pm.dump_spans(
    #     filepath="services/RAG/sample/Academic Governance Handbook 2025.pdf",
    #     pages=[1]
    # )
    
    # variants = pm.inspect(filepath="services/RAG/sample/Academic Governance Handbook 2025.pdf")
    # for v in variants:
    #     print(v)