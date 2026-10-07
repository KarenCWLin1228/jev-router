import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import httpx

from jev_router.cli import main
from jev_router.client import post_request
from jev_router.config import load_settings


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.models = {
            "codex": {"fast": {"model": "codex-test", "description": "簡單問題"}},
            "claude": {"fast": {"model": "claude-test", "description": "簡單問題"}},
            "antigravity": {"fast": {"model": "gemini-test", "description": "生活日常"}},
        }
        (self.folder / "models.json").write_text(json.dumps(self.models), encoding="utf-8")
        (self.folder / ".env").write_text('TYPESAFE_API_KEY="fake-secret"\n', encoding="utf-8")
        self.env = patch.dict(os.environ, {"JEV_ROUTER_CONFIG_DIR": str(self.folder)})
        self.env.start()
        os.environ.pop("TYPESAFE_API_KEY", None)
        os.environ.pop("TYPESAFE_MODEL", None)
        self.addCleanup(self.env.stop)

    def invoke(self, *extra, client="codex"):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(["recommend", "--client", client, "--config-dir", str(self.folder), *extra])
        self.assertNotIn("fake-secret", output.getvalue() + errors.getvalue())
        return code, output.getvalue(), errors.getvalue()

    @patch("jev_router.cli.post_request")
    def test_clients_use_separate_lists_and_only_one_jev_call(self, request):
        request.return_value = {"model": "jev-test", "answers": {"route": {
            "choice": "fast", "probabilities": {"fast": 1}, "confidence": 0.9,
        }}}
        for client in ("codex", "claude", "antigravity"):
            request.reset_mock()
            code, output, _ = self.invoke("--question", "問題", "--json", client=client)
            self.assertEqual(code, 0)
            expected = "gemini-test" if client == "antigravity" else client + "-test"
            self.assertEqual(json.loads(output)["recommended_model"], expected)
            self.assertFalse(json.loads(output)["selected_model_called"])
            request.assert_called_once()
            self.assertEqual(request.call_args.args[1], "fake-secret")
            self.assertNotIn("fake-secret", json.dumps(request.call_args.args[0]))

    @patch("jev_router.cli.post_request", side_effect=AssertionError("Offline tests cannot call API"))
    def test_dry_run_needs_no_secret_and_never_calls_api(self, request):
        (self.folder / ".env").unlink()
        code, output, _ = self.invoke("--question", "問題", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "dry_run")
        request.assert_not_called()

    @patch("jev_router.cli.post_request", side_effect=AssertionError("Fixed route cannot call API"))
    def test_fixed_route_needs_no_secret_and_never_calls_api(self, request):
        (self.folder / ".env").unlink()
        code, output, _ = self.invoke("--question", "問題", "--route", "fast", "--json", client="claude")
        self.assertEqual(code, 0)
        result = json.loads(output)
        self.assertEqual(result["recommended_model"], "claude-test")
        self.assertEqual(result["source"], "fixed")
        self.assertTrue(result["auto_send"])
        self.assertEqual(self.invoke("--question", "問題", "--route", "deep", "--json")[0], 1)
        request.assert_not_called()

    @patch("jev_router.cli.post_request")
    def test_bad_inputs_and_missing_key_never_call_api(self, request):
        for client, question in (("codex", " "), ("unknown", "問題")):
            self.assertEqual(self.invoke("--question", question, "--json", client=client)[0], 1)
        (self.folder / ".env").unlink()
        self.assertEqual(self.invoke("--question", "問題", "--json")[0], 1)
        request.assert_not_called()

    @patch("jev_router.cli.post_request", return_value={"answers": {}})
    def test_invalid_response_is_failure_without_recommendation(self, request):
        code, output, _ = self.invoke("--question", "問題", "--json")
        self.assertEqual(code, 1)
        self.assertNotIn("recommended_model", json.loads(output))

    def test_environment_overrides_file(self):
        os.environ["TYPESAFE_API_KEY"] = "environment-secret"
        self.assertEqual(load_settings(self.folder)["TYPESAFE_API_KEY"], "environment-secret")

    @patch("jev_router.client.httpx.Client")
    def test_http_error_does_not_leak_provider_body_or_key(self, client):
        response = httpx.Response(401, text="fake-secret")
        client.return_value.__enter__.return_value.post.return_value = response
        with self.assertRaisesRegex(RuntimeError, "HTTP 401") as caught:
            post_request({}, "fake-secret")
        self.assertNotIn("fake-secret", str(caught.exception))

    @patch("jev_router.cli.post_request")
    def test_utf8_file_and_context_reach_jev(self, request):
        question = self.folder / "question.txt"
        question.write_text("問題", encoding="utf-8-sig")
        request.return_value = {}
        self.invoke("--question-file", str(question), "--context", "前一題", "--json")
        self.assertEqual(request.call_args.args[0]["state"], {"question": "問題", "recent_context": "前一題"})

    @patch("jev_router.cli.collect_antigravity")
    @patch("jev_router.cli.post_request")
    def test_collect_only_closes_with_explicit_flags(self, request, collector):
        collector.return_value = {"status": "completed", "terminal_closed": False}
        for flags, expected in (([], False), (["--close", "--confirmed"], True)):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["collect", "--job-dir", str(self.folder), "--json", *flags]), 0)
            self.assertEqual(collector.call_args.kwargs, {"close": expected, "confirmed": expected})
        request.assert_not_called()

    @patch("jev_router.cli.launch_antigravity", return_value={"status": "launch_preview"})
    @patch("jev_router.cli.post_request")
    def test_launch_passes_confirmation_and_mode_without_jev_request(self, request, launcher):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([
                "launch", "--model", "gemini-test", "--question", "生活問題", "--mode", "plan",
                "--config-dir", str(self.folder), "--dry-run", "--json",
            ])
        self.assertEqual(code, 0)
        request.assert_not_called()
        self.assertFalse(launcher.call_args.kwargs["confirmed"])
        self.assertTrue(launcher.call_args.kwargs["dry_run"])
        self.assertEqual(launcher.call_args.kwargs["mode"], "plan")
