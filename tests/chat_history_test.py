# did not test __repr__

import unittest
import warnings
import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")
from modules.ChatHistory import ChatHistory

class TestChatHistory(unittest.TestCase):
    def setUp(self):
        self.chat = ChatHistory("What's the weather like?")

    def test_initialization(self):
        self.assertEqual(self.chat.original_question, "What's the weather like?")
        self.assertEqual(self.chat.history_length, 0)
        self.assertEqual(self.chat.conversation_history, [])

    def test_add_interaction(self):
        self.chat.add_interaction("Will it rain?", "There's a 30% chance of rain.")
        self.assertEqual(self.chat.history_length, 1)
        self.assertEqual(self.chat.conversation_history, [("Will it rain?", "There's a 30% chance of rain.")])

    def test_max_history(self):
        chat = ChatHistory("Initial question", max_history=2)
        chat.add_interaction("Q1", "A1")
        chat.add_interaction("Q2", "A2")
        chat.add_interaction("Q3", "A3")
        self.assertEqual(chat.history_length, 2)
        self.assertEqual(chat.conversation_history, [("Q2", "A2"), ("Q3", "A3")])

    def test_clear_history(self):
        self.chat.add_interaction("Q1", "A1")
        self.chat.clear_history()
        self.assertIsNone(self.chat.original_question)
        self.assertEqual(self.chat.history_length, 0)
        self.assertEqual(self.chat.conversation_history, [])

    def test_to_dict(self):
        self.chat.add_interaction("Q1", "A1")
        expected_dict = {
            "original_question": "What's the weather like?",
            "conversation_history": [("Q1", "A1")]
        }
        self.assertEqual(self.chat.to_dict(), expected_dict)

    def test_str_representation(self):
        expected_str = "ChatHistory(original_question='What's the weather like?', history_length=0)"
        self.assertEqual(str(self.chat), expected_str)

    def test_original_question_setter(self):
        self.chat._original_question = "New question" # changing the attribute directly
        self.assertEqual(self.chat._original_question, "New question")

    # def test_original_question_setter_validation(self):
    #     with self.assertRaises(ValueError):
    #         self.chat._original_question = ""  # Empty string
    #     with self.assertRaises(ValueError):
    #         self.chat._original_question = "   "  # Whitespace only

    # def test_add_interaction_validation(self):
    #     with self.assertRaises(ValueError):
    #         self.chat.add_interaction("", "Valid answer")  # Empty question
    #     with self.assertRaises(ValueError):
    #         self.chat.add_interaction("Valid question", "")  # Empty answer

    # def test_warning_on_unset_original_question(self):
    #     chat = ChatHistory(None, 3)  # Initialize without original question
    #     with warnings.catch_warnings(record=True) as w:
    #         warnings.simplefilter("always")
    #         _ = chat.original_question
    #         self.assertEqual(len(w), 1)
    #         self.assertTrue(issubclass(w[-1].category, UserWarning))
    #         self.assertIn("Original question has not been set yet", str(w[-1].message))

if __name__ == '__main__':
    unittest.main()