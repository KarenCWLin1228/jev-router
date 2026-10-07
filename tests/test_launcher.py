import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jev_router.launcher import collect_antigravity, launch_antigravity
from jev_router.worker import run_job

CANDIDATES = {"fast": {"model": "gemini-test"}}


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        executable = self.home / "AppData/Local/agy/bin/agy.exe"
        executable.parent.mkdir(parents=True)
        executable.touch()
        for patcher in (patch("jev_router.launcher.Path.home", return_value=self.home),
                        patch("jev_router.launcher.shutil.which", return_value="orca.exe")):
            patcher.start()
            self.addCleanup(patcher.stop)

    @patch("jev_router.launcher.subprocess.run")
    def test_confirmation_and_allowlist_before_process(self, process):
        for model, confirmed in (("gemini-test", False), ("unknown", True)):
            with self.assertRaises(ValueError):
                launch_antigravity(model, "問題", "", CANDIDATES, confirmed=confirmed)
        process.assert_not_called()

    @patch("jev_router.launcher.subprocess.run")
    def test_dry_run_starts_nothing(self, process):
        result = launch_antigravity("gemini-test", "私人問題", "", CANDIDATES, dry_run=True)
        self.assertEqual(result["target"], "orca")
        self.assertNotIn("私人問題", json.dumps(result, ensure_ascii=False))
        process.assert_not_called()

    @patch("jev_router.launcher.orca_call")
    @patch("jev_router.launcher.subprocess.run")
    def test_launch_keeps_user_text_out_of_shell(self, process, orca):
        process.return_value = subprocess.CompletedProcess([], 0, "gemini-test Test", "")
        orca.return_value = {"terminal": {"handle": "term_owned"}}
        job = self.home / "job"
        job.mkdir()
        question = '`whoami` $(danger) "private"'
        with patch("jev_router.launcher.tempfile.mkdtemp", return_value=str(job)):
            result = launch_antigravity("gemini-test", question, "", CANDIDATES, confirmed=True)
        self.assertEqual(result["terminal_handle"], "term_owned")
        self.assertNotIn(question, " ".join(orca.call_args.args[1]))
        create_arguments = orca.call_args_list[0].args[1]
        self.assertNotIn("--focus", create_arguments)
        self.assertNotIn("exit", create_arguments[-1])
        self.assertEqual(json.loads((job/"request.json").read_text(encoding="utf-8"))["question"], question)

    @patch("jev_router.launcher.orca_call")
    def test_pending_never_closes_success_closes_owned_terminal_and_cleans(self, orca):
        with tempfile.TemporaryDirectory(prefix="jev-antigravity-") as folder:
            job = Path(folder)
            (job/"request.json").write_text(json.dumps({"orca": "orca.exe"}), encoding="utf-8")
            (job/"terminal.json").write_text(json.dumps({"handle": "term_owned"}), encoding="utf-8")
            self.assertEqual(collect_antigravity(job)["status"], "pending")
            orca.assert_not_called()
            (job/"result.json").write_text(json.dumps({"status": "completed", "response": "回答"}), encoding="utf-8")
            orca.return_value = {"close": {"ptyKilled": True}}
            result = collect_antigravity(job)
            self.assertFalse(result["terminal_closed"])
            orca.assert_not_called()
            self.assertTrue(job.exists())
            with self.assertRaises(ValueError):
                collect_antigravity(job, close=True)
            orca.assert_not_called()
            result = collect_antigravity(job, close=True, confirmed=True)
            self.assertNotIn("response", result)
            self.assertNotIn("回答", json.dumps(result, ensure_ascii=False))
            self.assertTrue(result["terminal_closed"])
            self.assertEqual(orca.call_args.args[1], ["terminal", "close", "--terminal", "term_owned"])
            self.assertFalse(job.exists())

    @patch("jev_router.worker.subprocess.Popen")
    @patch("jev_router.worker.Path.home")
    def test_worker_inherits_terminal_and_records_no_answer(self, home, process):
        home.return_value = self.home
        request = dict(executable="agy.exe", model="gemini-test", question="問題", context="", mode="plan")
        (self.home/"request.json").write_text(json.dumps(request), encoding="utf-8")
        for expected in (0, 1):
            def finish():
                started = json.loads((self.home/"result.json").read_text(encoding="utf-8"))
                self.assertEqual(started["status"], "interactive_started")
                self.assertFalse(started["answer_verified"])
                self.assertFalse(started["answer_displayed"])
                return expected
            process.return_value = Mock(pid=123)
            process.return_value.wait.side_effect = finish
            self.assertEqual(run_job(self.home), expected)
            recorded = (self.home/"result.json").read_text(encoding="utf-8")
            self.assertNotIn("response", json.loads(recorded))
            self.assertEqual(json.loads(recorded)["status"], "exited" if expected == 0 else "error")
            command = process.call_args.args[0]
            self.assertTrue(command[3].startswith("--prompt-interactive="))
            self.assertEqual(set(process.call_args.kwargs), {"cwd"})
            self.assertEqual(command[-2:], ["--mode", "plan"])
            self.assertEqual(process.call_count, 1 if expected == 0 else 2)

    @patch("jev_router.launcher.orca_call", return_value={"close": {"ptyKilled": True}})
    def test_confirmed_close_does_not_wait_for_interactive_answer(self, orca):
        with tempfile.TemporaryDirectory(prefix="jev-antigravity-") as folder:
            job = Path(folder)
            (job/"request.json").write_text(json.dumps({"orca": "orca.exe"}), encoding="utf-8")
            (job/"terminal.json").write_text(json.dumps({"handle": "term_owned"}), encoding="utf-8")
            result = collect_antigravity(job, close=True, confirmed=True)
            self.assertEqual(result["status"], "closed")
            self.assertTrue(result["terminal_closed"])
            self.assertFalse(job.exists())
