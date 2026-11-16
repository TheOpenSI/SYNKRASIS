from __future__ import annotations

import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import math
import re
from pathlib import Path
from typing import Any

from utils.output_message_format.output_colour import print_warning


class OptometryExtractor:

    # temp_count = 0

    def __init__(self) -> None:
        self.source = ""
        self.cases_with_warnings = set()
        self.null_tokens = {"none", "n/a", "na", "nil", "-"}
        self.snellen_ou = re.compile(r"\bOU\b\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)")
        self.not_testable = re.compile(
            r"not testable|unable|cannot|nil|absent|not assessed|not measured|not obtained", re.IGNORECASE
        )
        self.filename_id = re.compile(r"^(?:Case_)?(\d+)_")
        self.text_id = re.compile(r"\A\s*Case\s+(\d+)\b")


    # def extract_folder(self, folder: str | Path) -> list[dict[str, Any]]:
    def extract_folder(self, folder: str | Path) -> dict[str, dict[str, Any]]:
        files = sorted(Path(folder).glob("*Optom*_Report.txt"))
        if not files:
            raise ValueError(f"No optometry report .txt files in {folder}")
        
        # patch to match ot extarct
        extract_list = [self.extract(path) for path in files]
        records = {}

        for item in extract_list:
            case_id = item.get("case_id")
            del item["case_id"]
            records[case_id] = item

        return records


    def extract(self, path: str | Path) -> dict[str, Any]:
        path = Path(path)
        self.source = path.name
        text = path.read_text(encoding="utf-8-sig").replace(" ", " ")
        best_va = self.best_corrected_acuity(text)
        habitual_va = self.habitual_acuity(text)
        best_logmar = self.logmar(best_va)
        habitual_logmar = self.logmar(habitual_va)
        stereo_testable = self.stereo_testable(text)
        return {
            "case_id": self.case_id(text),
            "age": self.age(text),
            "gender": self.gender(text),
            "care_setting": self.care_setting(text),
            "primary_phenotype": self.primary_phenotype(text),
            "secondary_phenotype": self.secondary_phenotype(text),
            "primary_diagnosis": self.primary_diagnosis(text),
            "modifiers": self.modifiers(text),
            "best_corrected_va_ou": best_va,
            "best_corrected_logmar_ou": best_logmar,
            "habitual_va_ou": habitual_va,
            "habitual_logmar_ou": habitual_logmar,
            "correction_gap_logmar": self.correction_gap(habitual_logmar, best_logmar),
            "stereo_testable": stereo_testable,
            "stereo_arcsec": self.stereo_arcsec(text, stereo_testable),
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


    def age(self, text: str) -> int | None:
        value = self._value(text, "Age")
        if value is None:
            return None
        match = re.search(r"\d+", value)
        if match is None:
            return self._fail(f"no number in age '{value}'")
        return int(match.group())


    def gender(self, text: str) -> str | None:
        return self._value(text, "Gender")


    def care_setting(self, text: str) -> str | None:
        return self._value(text, "Care setting")


    def primary_phenotype(self, text: str) -> str | None:
        return self._value(text, "Primary phenotype")


    def secondary_phenotype(self, text: str) -> str | None:
        value = self._value(text, "Secondary phenotype")
        return None if value is None or value.lower() in self.null_tokens else value


    def primary_diagnosis(self, text: str) -> str | None:
        return self._value(text, "Primary diagnosis")


    def modifiers(self, text: str) -> list[str] | None:
        value = self._value(text, "Modifiers")
        if value is None:
            return None
        if value.lower() in self.null_tokens:
            return []
        return [modifier.strip() for modifier in value.split(";") if modifier.strip()]


    def best_corrected_acuity(self, text: str) -> str | None:
        return self._acuity(text, "best corrected")


    def habitual_acuity(self, text: str) -> str | None:
        return self._acuity(text, "presenting, habitual")


    def logmar(self, snellen: str | None) -> float | None:
        if snellen is None:
            return None
        numerator, denominator = (float(part) for part in snellen.split("/"))
        if numerator <= 0 or denominator <= 0:
            return self._fail(f"cannot convert '{snellen}' to logMAR")
        return round(math.log10(denominator / numerator), 3)


    def correction_gap(
        self, habitual_logmar: float | None, best_logmar: float | None
    ) -> float | None:
        if habitual_logmar is None or best_logmar is None:
            return None
        return round(habitual_logmar - best_logmar, 3)


    def stereo_testable(self, text: str) -> bool | None:
        value = self._stereo_value(text)
        if value is None:
            return None
        if self.not_testable.search(value):
            return False
        if re.search(r"\d+", value) is None:
            return self._fail(f"stereo result not recognised: '{value}'")
        return True


    def stereo_arcsec(self, text: str, testable: bool | None) -> int | None:
        if not testable:
            # print(f"{testable = }")
            # self.temp_count += 1
            return None
        value = int(re.search(r"\d+", self._stereo_value(text)).group())
        # print(f"{self.temp_count = }, {value = }")
        # self.temp_count += 1
        return value


    def _stereo_value(self, text: str) -> str | None:
        return self._line_value(text, r"Stereo[ \t]*\([^)]*\)", "Stereo (...)")


    def _acuity(self, text: str, qualifier: str, required: bool = True) -> str | None:
        pattern = rf"Distance VA[ \t]*\({re.escape(qualifier)}[^)]*\)"
        description = f"Distance VA ({qualifier}...)"
        line = self._line_value(text, pattern, description, required)
        if line is None:
            return None
        match = self.snellen_ou.search(line)
        if match is None:
            return self._fail(f"no binocular (OU) Snellen value in '{description}: {line}'")
        return f"{match.group(1)}/{match.group(2)}"


    def _value(self, text: str, label: str) -> str | None:
        return self._line_value(text, re.escape(label), label)


    def _line_value(
        self, text: str, label_pattern: str, description: str, required: bool = True
    ) -> str | None:
        pattern = rf"^[ \t]*{label_pattern}[ \t]*:[ \t]*(\S.*?)[ \t]*$"
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not matches:
            return self._fail(f"no value found for '{description}'") if required else None
        if len(matches) > 1:
            return self._fail(f"{len(matches)} lines match '{description}': {matches}")
        return matches[0]


    def _fail(self, message: str) -> None:
        self.cases_with_warnings.add(self.source)
        print_warning(f"{self.source}: {message}")


if __name__ == "__main__":
    output = "Agents/data/metadata/90_Optometry_Inputs_metadata.json"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    extractor = OptometryExtractor()
    records = extractor.extract_folder("Agents/data/90_Optometry_Inputs_txt")
    Path(output).write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{len(records)} cases written to {output}")
    print(f"{len(extractor.cases_with_warnings)} cases with warnings")