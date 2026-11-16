from __future__ import annotations

import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from utils.output_message_format.output_colour import print_warning


class OTExtractor:

    def __init__(self) -> None:
        self.source = ""
        self.cases_with_warnings = set()
        self.filename_id = re.compile(r"^(?:Case_)?(\d+)_")
        self.text_id = re.compile(r"\A\s*Case\s+(\d+)\b")
        self.falls_heading = re.compile(
            r"^[ \t]*(?:\d+\.[ \t]*)?Falls Risk Level[ \t]*:?[ \t]*$",
            re.IGNORECASE | re.MULTILINE,
        )
        self.risk_level = re.compile(r"(very high|high|moderate|low)\b", re.IGNORECASE)
        self.followup_heading = re.compile(
            r"^[ \t]*Clinical Follow-*\s*up", re.IGNORECASE | re.MULTILINE
        )


    def extract_folder(self, folder: str | Path) -> dict[str, dict[str, Any]]:
        files = sorted(Path(folder).glob("*OT_*Summar*.txt"))
        if not files:
            raise ValueError(f"No OT summary .txt files in {folder}")
        records = {}
        for path in files:
            record = self.extract(path)
            key = record.pop("case_id") or path.name
            if key in records:
                self._fail(f"duplicate of {key}, skipped")
                continue
            records[key] = record
        return records


    def extract(self, path: str | Path) -> dict[str, Any]:
        path = Path(path)
        self.source = path.name
        text = path.read_text(encoding="utf-8-sig").replace(" ", " ")
        return {
            "case_id": self.case_id(text),
            "falls_risk_level": self.falls_risk_level(text),
            "has_clinical_followup_section": self.has_clinical_followup_section(text),
        }


    def case_id(self, text: str) -> str | None:
        from_name = self.filename_id.match(self.source)
        from_text = self.text_id.match(text)
        if from_name is None or from_text is None:
            return self._fail(
                f"case ID not found (in filename: {from_name is not None}, "
                f"on line 1: {from_text is not None})"
            )
        name_number, text_number = int(from_name.group(1)), int(from_text.group(1))
        if name_number != text_number:
            return self._fail(
                f"filename says case {name_number} but line 1 says case {text_number}"
            )
        return f"Case_{name_number:03d}"


    def falls_risk_level(self, text: str) -> str | None:
        heading = self.falls_heading.search(text)
        if heading is None:
            outline = [line.strip() for line in text.splitlines() if 0 < len(line.strip()) < 45]
            return self._fail(f"no 'Falls Risk Level' heading (short lines in file: {outline[:15]})")
        lead = next((line for line in text[heading.end():].splitlines() if line.strip()), "")
        match = self.risk_level.match(re.sub(r"^[\s•\-*]+", "", lead))
        if match is None:
            return self._fail(f"falls risk line does not start with a risk level: '{lead.strip()}'")
        return match.group(1).capitalize()


    def has_clinical_followup_section(self, text: str) -> bool:
        return bool(self.followup_heading.search(text))


    def _fail(self, message: str) -> None:
        self.cases_with_warnings.add(self.source)
        print_warning(f"{self.source}: {message}")


if __name__ == "__main__":
    output = "Agents/data/metadata/90_OT_Reference_Summaries_metadata.json"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    extractor = OTExtractor()
    records = extractor.extract_folder("Agents/data/90_OT_Reference_Summaries_txt")
    Path(output).write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{len(records)} cases written to {output}")
    print(f"{len(extractor.cases_with_warnings)} cases with warnings")
    for field in next(iter(records.values())):
        missing = sum(record[field] is None for record in records.values())
        print(f"  {field}: missing in {missing} of {len(records)}")
    print(f"  falls risk counts: {dict(Counter(r['falls_risk_level'] for r in records.values()))}")