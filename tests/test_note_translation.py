import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from src.routes.note import note_bp
import translator


class NoteTranslationRouteTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(note_bp, url_prefix="/api")
        self.client = app.test_client()

    def test_rejects_missing_target_language(self):
        response = self.client.post(
            "/api/notes/translate",
            json={"title": "Hello", "content": "World"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("target language", response.get_json()["error"])

    @patch("src.routes.note.translate_note_with_openrouter")
    def test_returns_translated_title_and_content(self, translate_note):
        translate_note.return_value = {"title": "Hola", "content": "Mundo"}

        response = self.client.post(
            "/api/notes/translate",
            json={"title": "Hello", "content": "World", "target_language": "Spanish"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"title": "Hola", "content": "Mundo"})
        translate_note.assert_called_once_with("Hello", "World", "Spanish")

    @patch("src.routes.note.translate_note_with_openrouter")
    def test_hides_configuration_error_details(self, translate_note):
        translate_note.side_effect = RuntimeError("secret provider detail")

        response = self.client.post(
            "/api/notes/translate",
            json={"title": "Hello", "content": "World", "target_language": "Spanish"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret provider detail", response.get_data(as_text=True))

    @patch("src.routes.note.translate_note_with_openrouter")
    def test_rejects_invalid_model_output_safely(self, translate_note):
        translate_note.side_effect = ValueError("raw malformed response")

        response = self.client.post(
            "/api/notes/translate",
            json={"title": "Hello", "content": "World", "target_language": "Spanish"},
        )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("raw malformed response", response.get_data(as_text=True))


class TranslatorTests(unittest.TestCase):
    def test_parses_structured_translation_json(self):
        message = SimpleNamespace(content='{"title":"Hola","content":"Mundo"}')
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        completions = SimpleNamespace(create=unittest.mock.Mock(return_value=response))
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

        with patch("translator._openrouter_client", return_value=client):
            translated = translator.translate_note("Hello", "World", "Spanish")

        self.assertEqual(translated, {"title": "Hola", "content": "Mundo"})
        self.assertEqual(completions.create.call_args.kwargs["response_format"], {"type": "json_object"})

    def test_rejects_invalid_translation_json(self):
        message = SimpleNamespace(content="not json")
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response))
        )

        with patch("translator._openrouter_client", return_value=client):
            with self.assertRaises(ValueError):
                translator.translate_note("Hello", "World", "Spanish")


if __name__ == "__main__":
    unittest.main()