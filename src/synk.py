import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import threading
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from services.LLM.LLMBase import LLMBase
from utils.cli.CLICommands import CLICommands
from utils.output_message_format.output_colour import print_info, print_error
from utils.ascii.synkrasis import print_synkrasis_logo


class SynkrasisCLI:
    def __init__(self, model: LLMBase) -> None:
        self.model = model
        self.style = self._get_style()
        self.state = {
            "rag": False,
            "history": []
        }

        # True while the model is working. Read by the toolbar and by the
        # key bindings that lock the input box.
        self.busy = False

        synk_commands = {
            "rag": {
                "desc": "Toggle RAG mode on/off",
                "func": self._update_rag_state
            },
            "c_hist": {
                "desc": "Modify conversation history",
                "func": lambda: None
            }
        }
        self.commands = CLICommands(commands = synk_commands)

        # The normal prompt text.
        self.prompt_text = ">> Query: "

        # The word shown on the prompt line while the model is working, and
        # how long each animation step lasts (in seconds).
        self.busy_word = "thinking"
        self.busy_interval = 0.15


    def _update_rag_state(self) -> bool:
        self.state["rag"] = not self.state["rag"]
        text = "RAG activated" if self.state["rag"] else "RAG deactivated"
        print_info(text)
        print()

        return self.state["rag"]


    def _update_conv_history_state(self) -> None:
        self.state["history"] = self.model.chat_history.conversation_history


    def _show_conv_history(self) -> None:
        pass


    def _get_style(self) -> Style:
        return Style.from_dict(
            {
                # toolbar
                "bottom-toolbar":      "bg:#1e1e1e #aaaaaa",

                # list viewer
                "header":        "bg:#111111 #555555",
                "you.cursor":    "bg:#005f87 #ffffff bold",
                "you.normal":    "bg:#1a1a1a #7ec8e3",
                "you.alt":       "bg:#1f1f1f #7ec8e3",
                "asst.cursor":   "bg:#003f5f #aaaaaa italic",
                "asst.normal":   "bg:#1a1a1a #666666 italic",
                "asst.alt":      "bg:#1f1f1f #666666 italic",
                "hint":          "bg:#111111 #444444",
                "divider":       "bg:#111111 #333333"
            }
        )


    def _busy_text(self) -> str:
        """Return the busy word with an underscore moving along it.

        The position comes from the clock, so no animation thread is needed:
        _hinking, t_inking, th_nking, ... then back to the start.
        """
        word = self.busy_word
        i = int(time.time() / self.busy_interval) % len(word)
        return word[:i] + "_" + word[i + 1:]


    def _get_prompt_message(self) -> str:
        """Text shown at the start of the input line.

        Normally ">> Query: ". While the model is working it becomes the
        animated word. This function is called again on every redraw.
        """
        if self.busy:
            indent = " " * len(self.prompt_text)
            return f"[{self.model.model_name.upper()}] {self._busy_text()}"
        return self.prompt_text


    def _get_toolbar(self) -> HTML:
        rag = "on" if self.state["rag"] else "off"
        n = len(self.state["history"])
        return HTML(
            f'  <b>ENV</b>'
            f'  │  rag = {rag}'
            f'  │  history: <b>{n}</b>'
            f'  |  <i>"/help" to see the list of commands</i>'
        )


    def _set_session(self) -> PromptSession:
        kb = KeyBindings()
        busy = Condition(lambda: self.busy)

        # While the model is working, Enter and the history-search keys
        # (Ctrl+R / Ctrl+S) do nothing.
        @kb.add("enter", filter=busy)
        def _(event):
            pass

        # Tab accepts the grey command suggestion, if one is showing.
        @kb.add("tab")
        def _(event):
            buffer = event.current_buffer
            suggestion = buffer.suggestion
            if suggestion:
                buffer.insert_text(suggestion.text)

        session = PromptSession(
            message=self._get_prompt_message,
            bottom_toolbar=self._get_toolbar,
            auto_suggest=self.commands.auto_suggest,
            style=self.style,
            refresh_interval=self.busy_interval,
            key_bindings=kb,
        )

        # While the model is working, anything typed is wiped straight away.
        def clear_if_busy(buffer) -> None:
            if self.busy and buffer.text:
                buffer.text = ""

        session.default_buffer.on_text_changed += clear_if_busy
        return session


    def _generate(self, query: str) -> None:
        """Runs in a background thread so the prompt and toolbar stay alive."""
        try:
            self.model.generate_response(query, suppress_conversation_history=False)
            self._update_conv_history_state()
        except Exception as e:
            print_error(f"Error occurred while generating response: {e}\n")
        finally:
            self.busy = False


    def run_cli(self) -> None:
        print_synkrasis_logo()
        session = self._set_session()

        # patch_stdout makes every print() appear above the prompt and toolbar.
        # raw=True lets the ANSI colour codes through unchanged.
        with patch_stdout(raw=True):
            while True:
                try:
                    query = session.prompt()
                except (KeyboardInterrupt):
                    print_info("Keyboard interrupt (Ctrl+C) received. Exiting...")
                    self.commands.cmd_exit()
                    break

                query = query.strip()
                if not query:
                    continue

                if query.startswith("\\"):
                    self.commands.execute_command(query)
                    continue

                self.busy = True
                # daemon=True means Ctrl+C can quit without waiting for the model.
                threading.Thread(
                    target=self._generate, args=(query,), daemon=True
                ).start()