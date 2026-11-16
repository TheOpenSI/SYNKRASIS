from __future__ import annotations

import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import re
from pathlib import Path

from utils.output_message_format.output_colour import print_warning, print_info
from services.LLM.Ollama.OllamaClient import OllamaClient


class LLMExtractor:

    def __init__(
        self,
        reports_folder: str | Path,
        responses_folder: str | Path,
        prompt_path: str | Path,
    ) -> None:
        self.reports_folder = Path(reports_folder)
        self.responses_folder = Path(responses_folder)
        self.system_prompt = Path(prompt_path).read_text(encoding="utf-8")
        self.source = ""
        self.cases_with_warnings = set()
        self.questions = [
            "contrast_abnormal",
            "field_defect",
            "motility_or_diplopia",
            "colour_abnormal",
            "pupil_abnormal",
            "fall_confirmed",
            "falls_recurrent",
            "near_fall",
            "lives_alone",
            "refer_gp",
            "refer_specialist",
            "refer_ot",
            "refer_other",
        ]
        self.filename_id = re.compile(r"^(?:Case_)?(\d+)_")
        self.text_id = re.compile(r"\A\s*Case\s+(\d+)\b")
        self.json_block = re.compile(r"```json\s*(.*?)```", re.DOTALL)



    def run(self, models: list[OllamaClient], overwrite: bool = False) -> None:
        reports = self._reports()
        for model in models:
            folder = self.responses_folder / model.model_name
            folder.mkdir(parents=True, exist_ok=True)
            model.set_system_prompt(self.system_prompt)
            
            for case_id, path in reports.items():
                target = folder / f"{case_id}.txt"
                if target.exists() and not overwrite:
                    continue
                self.source = f"{model.model_name} {case_id}"
                try:
                    response = model.generate_response(self._read(path))
                except Exception as error:
                    self._fail(f"model call failed: {error}")
                    continue
                if not response:
                    self._fail("empty response")
                    continue
                target.write_text(response, encoding="utf-8")
            saved = len(list(folder.glob("*.txt")))
            print_info(f"{model.model_name}: {saved} of {len(reports)} responses saved")


    def analyse(self, output: str | Path) -> dict[str, dict[str, bool | None]]:
        models = sorted(p.name for p in self.responses_folder.iterdir() if p.is_dir())
        if not models:
            raise ValueError(f"No model folders in {self.responses_folder}")
        metadata, votes = {}, {}
        for case_id in self._reports():
            case_votes = {question: {} for question in self.questions}
            for model in models:
                answers = self._model_answers(model, case_id)
                for question in self.questions:
                    case_votes[question][model] = answers.get(question)
            votes[case_id] = case_votes
            metadata[case_id] = {
                question: self._majority(list(case_votes[question].values()))
                for question in self.questions
            }
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        votes_path = output.with_name(f"{output.stem}_votes.json")
        votes_path.write_text(json.dumps(votes, indent=2, ensure_ascii=False), encoding="utf-8")
        self._print_summary(metadata, votes, models, output)
        return metadata


    def _model_answers(self, model: str, case_id: str) -> dict[str, str]:
        self.source = f"{model} {case_id}"
        path = self.responses_folder / model / f"{case_id}.txt"
        if not path.exists():
            self._fail("no saved response")
            return {}
        blocks = self.json_block.findall(path.read_text(encoding="utf-8"))
        if not blocks:
            self._fail("no json block in response")
            return {}
        try:
            data = json.loads(blocks[-1])
        except json.JSONDecodeError as error:
            self._fail(f"invalid JSON: {error}")
            return {}
        if not isinstance(data, dict):
            self._fail("json block is not an object")
            return {}
        for key in set(data) - set(self.questions):
            self._fail(f"unexpected key '{key}'")
        answers = {}
        for question in self.questions:
            answer = self._valid_answer(question, data.get(question))
            if answer is not None:
                answers[question] = answer
        return answers


    def _valid_answer(self, question: str, value: object) -> str | None:
        answer = str(value).strip().lower()
        if answer not in ("yes", "no"):
            return self._fail(f"{question}: answer is not yes or no: {value!r}")
        return answer


    def _majority(self, values: list[str | None]) -> bool | None:
        valid = [value for value in values if value is not None]
        if valid.count("yes") == valid.count("no"):
            return None
        return valid.count("yes") > valid.count("no")


    def _print_summary(
        self, metadata: dict, votes: dict, models: list[str], output: Path
    ) -> None:
        print_info(f"{len(metadata)} cases, {len(models)} models: {models}")
        print_info(f"metadata written to {output}")
        for question in self.questions:
            split = sum(
                1 for case_votes in votes.values()
                if len({v for v in case_votes[question].values() if v is not None}) > 1
            )
            print_info(f"  {question}: {split} split votes")


    def _reports(self) -> dict[str, Path]:
        reports = {}
        for path in sorted(self.reports_folder.glob("*Optom*_Report.txt")):
            case_id = self._case_id(path, self._read(path))
            if case_id is None:
                continue
            if case_id in reports:
                self._fail(f"duplicate of {case_id}, skipped")
                continue
            reports[case_id] = path
        if not reports:
            raise ValueError(f"No optometry report .txt files in {self.reports_folder}")
        return reports


    def _case_id(self, path: Path, text: str) -> str | None:
        self.source = path.name
        from_name = self.filename_id.match(path.name)
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


    def _read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8-sig").replace(" ", " ")


    def _fail(self, message: str) -> None:
        self.cases_with_warnings.add(self.source)
        print_warning(f"{self.source}: {message}")


if __name__ == "__main__":
    extractor = LLMExtractor(
        reports_folder="Agents/data/90_Optometry_Inputs_txt",
        responses_folder="Agents/data/metadata/llm_responses",
        prompt_path="Agents/prompts/metadata.txt",
    )
    extractor.run(
        models=[
            OllamaClient(model_name = "qwen2.5:72b"),
            OllamaClient(model_name = "mixtral:8x22b"),
            OllamaClient(model_name = "llama3.3:70b"),
        ],
        overwrite=False,
    )

    extractor.analyse("Agents/data/metadata/90_Optometry_llm_metadata.json")