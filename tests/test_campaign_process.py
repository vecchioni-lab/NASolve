import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import unittest
from itertools import count
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nasolve.campaign_process import (
    CampaignProcessError,
    _boot_id,
    _group_alive,
    _stop_owned_group,
    current_process_identity,
    exclusive_lock,
    process_alive,
    run_job,
)


@unittest.skipUnless(os.name == "posix", "Campaign worker execution requires POSIX")
class CampaignProcessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.job = self.root / "job.json"
        self.job.write_text("{}\n")
        self.identities = []

    def worker(self, script):
        """Exercise real sessions/process groups without a scientific runtime."""
        original = subprocess.Popen

        def launch(command, *args, **kwargs):
            if command[:3] == [sys.executable, "-m", "nasolve.campaign_worker"]:
                self.assertEqual(command[3], str(self.job))
                self.assertTrue(kwargs["start_new_session"])
                self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
                command = [sys.executable, "-c", script]
            return original(command, *args, **kwargs)

        return patch("nasolve.campaign_process.subprocess.Popen", side_effect=launch)

    def test_exit_code_output_and_identity_are_preserved(self):
        with self.worker("import time; print('worker evidence', flush=True); time.sleep(.15); raise SystemExit(7)"):
            heartbeats = []
            result = run_job(self.job, on_process=self.identities.append,
                             on_heartbeat=heartbeats.append, poll_interval=.02)
        self.assertEqual(result, 7)
        self.assertEqual((self.root / "worker.log").read_text(), "worker evidence\n")
        self.assertEqual(len(self.identities), 1)
        identity = self.identities[0]
        self.assertEqual(identity["pid"], identity["pgid"])
        self.assertEqual(identity["host"], platform.node())
        self.assertIn("start_marker", identity)
        self.assertTrue(heartbeats)
        self.assertGreaterEqual(heartbeats[-1]["heartbeat_utc"], identity["started_utc"])
        self.assertFalse(process_alive(identity))

    def test_existing_worker_log_is_never_overwritten(self):
        logfile = self.root / "worker.log"
        logfile.write_text("earlier attempt\n")
        with patch("nasolve.campaign_process.subprocess.Popen") as launch:
            with self.assertRaisesRegex(CampaignProcessError, "immutable campaign worker log") as caught:
                run_job(self.job)
        launch.assert_not_called()
        self.assertFalse(caught.exception.stopped_verified)
        self.assertEqual(logfile.read_text(), "earlier attempt\n")

    def test_launch_os_error_proves_no_child_was_started(self):
        with patch("nasolve.campaign_process.subprocess.Popen", side_effect=OSError("Cannot exec")):
            with self.assertRaisesRegex(CampaignProcessError, "Cannot launch campaign worker") as caught:
                run_job(self.job, on_process=self.identities.append)
        self.assertTrue(caught.exception.stopped_verified)
        self.assertEqual(self.identities, [])

    def test_missing_job_proves_no_child_was_started(self):
        self.job.unlink()
        with patch("nasolve.campaign_process.subprocess.Popen") as launch:
            with self.assertRaisesRegex(CampaignProcessError, "Cannot access campaign job") as caught:
                run_job(self.job)
        launch.assert_not_called()
        self.assertTrue(caught.exception.stopped_verified)

    def test_uncertain_completed_group_does_not_claim_stopped(self):
        with self.worker("raise SystemExit(0)"), \
                patch("nasolve.campaign_process._group_alive", return_value=None):
            with self.assertRaisesRegex(CampaignProcessError, "unidentifiable descendants") as caught:
                run_job(self.job, poll_interval=.02)
        self.assertFalse(caught.exception.stopped_verified)

    def test_lock_contends_across_processes_and_survives_release(self):
        lock = self.root / "dataset.lock"
        script = (
            "from pathlib import Path\n"
            "from nasolve.campaign_process import exclusive_lock, CampaignProcessError\n"
            "import sys\n"
            "try:\n"
            "    with exclusive_lock(Path(sys.argv[1])): pass\n"
            "except CampaignProcessError as exc:\n"
            "    print(str(exc)); raise SystemExit(9)\n"
        )
        with exclusive_lock(lock):
            inode = lock.stat().st_ino
            attempted = subprocess.run([sys.executable, "-c", script, str(lock)],
                                       capture_output=True, text=True, timeout=5)
        self.assertEqual(attempted.returncode, 9)
        self.assertIn("lock busy", attempted.stdout)
        with exclusive_lock(lock):
            self.assertEqual(lock.stat().st_ino, inode)
        self.assertTrue(lock.is_file())

    def test_lock_refuses_symlink_and_preserves_target(self):
        target = self.root / "untouched"
        target.write_text("unchanged")
        lock = self.root / "dataset.lock"
        lock.symlink_to(target)
        with self.assertRaisesRegex(CampaignProcessError, "Cannot open campaign lock"):
            with exclusive_lock(lock):
                self.fail("Symlink lock must not be acquired")
        self.assertEqual(target.read_text(), "unchanged")

    def test_interrupt_terminates_worker_and_term_ignoring_descendant(self):
        self.require_process_listing()
        child_ready = self.root / "child.ready"
        child = (
            "import signal, time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            f"Path({str(child_ready)!r}).write_text('ready'); time.sleep(60)"
        )
        script = (
            "import subprocess, sys, signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(60)"
        )

        def interrupted(identity):
            if child_ready.exists():
                self.assertTrue(process_alive(identity))
                raise KeyboardInterrupt

        with self.worker(script):
            with self.assertRaises(KeyboardInterrupt):
                run_job(self.job, on_process=self.identities.append,
                        on_heartbeat=interrupted, poll_interval=.02)
        self.assertFalse(process_alive(self.identities[0]))

    def test_sigterm_is_cleaned_up_and_original_handler_restored(self):
        previous = signal.getsignal(signal.SIGTERM)

        def interrupted(identity):
            os.kill(os.getpid(), signal.SIGTERM)

        with self.worker("import time; time.sleep(60)"):
            with self.assertRaises(KeyboardInterrupt):
                run_job(self.job, on_process=self.identities.append,
                        on_heartbeat=interrupted, poll_interval=.02)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)
        self.assertFalse(process_alive(self.identities[0]))

    def test_callback_failure_stops_owned_worker_before_propagating(self):
        def failed(identity):
            self.identities.append(identity)
            raise RuntimeError("Cannot persist process identity")

        with self.worker("import time; time.sleep(60)"):
            with self.assertRaisesRegex(RuntimeError, "Cannot persist") as caught:
                run_job(self.job, on_process=failed, poll_interval=.02)
        self.assertTrue(caught.exception.stopped_verified)
        self.assertFalse(process_alive(self.identities[0]))

    def test_interrupt_during_spawn_is_deferred_until_child_ownership(self):
        original = subprocess.Popen
        children = []

        def launch(command, *args, **kwargs):
            if command[:3] == [sys.executable, "-m", "nasolve.campaign_worker"]:
                child = original([sys.executable, "-c", "import time; time.sleep(60)"],
                                 *args, **kwargs)
                children.append(child)
                os.kill(os.getpid(), signal.SIGINT)
                return child
            return original(command, *args, **kwargs)

        previous = signal.getsignal(signal.SIGINT)
        with patch("nasolve.campaign_process.subprocess.Popen", side_effect=launch):
            with self.assertRaises(KeyboardInterrupt) as caught:
                run_job(self.job, poll_interval=.02)
        self.assertTrue(caught.exception.stopped_verified)
        self.assertEqual(signal.getsignal(signal.SIGINT), previous)
        self.assertIsNotNone(children[0].returncode)
        self.assertFalse(_group_alive(children[0].pid))

    def test_surviving_descendant_prevents_accepting_completed_worker(self):
        self.require_process_listing()
        script = (
            "import subprocess, sys; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])"
        )
        try:
            with self.worker(script):
                with self.assertRaisesRegex(CampaignProcessError, "surviving or unidentifiable descendants"):
                    run_job(self.job, on_process=self.identities.append, poll_interval=.02)
            self.assertTrue(process_alive(self.identities[0]))
        finally:
            # This test created this private group and retains its live identity.
            if self.identities and process_alive(self.identities[0]) is True:
                os.killpg(self.identities[0]["pgid"], signal.SIGKILL)

    def require_process_listing(self):
        if sys.platform.startswith("linux"):
            proc_pid = int(Path("/proc/self/stat").read_text().split(" ", 1)[0])
            if proc_pid != os.getpid():
                self.skipTest("Runtime process IDs do not match its proc namespace")
        listing = subprocess.run(["/bin/ps", "-axo", "pgid=,stat="],
                                 capture_output=True, text=True, timeout=2)
        if listing.returncode != 0:
            self.skipTest("Runtime does not expose its process namespace to ps")

    def test_group_listing_distinguishes_live_zombie_and_unknown(self):
        for output, result in (("100 S\n100 Z\n", True),
                               ("100 Z\n", False), ("101 S\n", None)):
            with self.subTest(output=output), \
                    patch("nasolve.campaign_process.os.killpg") as probe, \
                    patch("nasolve.campaign_process.subprocess.run", return_value=SimpleNamespace(
                        returncode=0, stdout=output,
                    )):
                self.assertIs(_group_alive(100), result)
                self.assertTrue(all(call.args == (100, 0) for call in probe.call_args_list))
        with patch("nasolve.campaign_process.os.killpg"), \
                patch("nasolve.campaign_process.subprocess.run", return_value=SimpleNamespace(
                    returncode=1, stdout="",
                )):
            self.assertIsNone(_group_alive(100))

    def test_permission_denied_probe_still_distinguishes_zombies_from_live_or_unknown(self):
        # Darwin killpg(..., 0) can return EPERM for an existing group whose
        # members are all zombies. Permission alone cannot classify liveness.
        cases = ((0, "100 Z\n", False), (0, "100 Z+\n100 Z\n", False),
                 (0, "100 Z\n100 S\n", True), (0, "101 S\n", None),
                 (1, "100 Z\n", None), (0, "100 Z\n100\n", None))
        for code, output, expected in cases:
            with self.subTest(code=code, output=output), \
                    patch("nasolve.campaign_process.os.killpg", side_effect=PermissionError(1, "Operation not permitted")) as probe, \
                    patch("nasolve.campaign_process.subprocess.run", return_value=SimpleNamespace(
                        returncode=code, stdout=output,
                    )):
                self.assertIs(_group_alive(100), expected)
                self.assertTrue(all(call.args == (100, 0) for call in probe.call_args_list))

    def test_darwin_zombie_after_term_is_reaped_without_unnecessary_kill(self):
        process = SimpleNamespace(pid=100, returncode=None)
        terminated = False
        signals = []

        def signal_group(pid, sig):
            nonlocal terminated
            self.assertEqual(pid, process.pid)
            if terminated:
                raise PermissionError(1, "Operation not permitted")
            if sig:
                signals.append(sig)
                terminated = True

        def listing(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout="100 Z\n" if terminated else "100 S\n")

        def reap(timeout):
            self.assertTrue(terminated)
            process.returncode = -signal.SIGTERM

        process.wait = reap
        with patch("nasolve.campaign_process.os.killpg", side_effect=signal_group), \
                patch("nasolve.campaign_process.subprocess.run", side_effect=listing), \
                patch("nasolve.campaign_process.time.monotonic", side_effect=count()), \
                patch("nasolve.campaign_process.time.sleep"):
            _stop_owned_group(process)
        self.assertEqual(signals, [signal.SIGTERM])
        self.assertEqual(process.returncode, -signal.SIGTERM)

    def test_permission_denied_signal_succeeds_only_after_verified_group_exit(self):
        for activity in (False, True, None):
            with self.subTest(activity=activity):
                process = SimpleNamespace(pid=100, returncode=None)
                reaped = []
                process.wait = lambda timeout: reaped.append(True)
                with patch("nasolve.campaign_process.os.killpg", side_effect=PermissionError(1, "Operation not permitted")) as send, \
                        patch("nasolve.campaign_process._group_alive", return_value=activity):
                    if activity is False:
                        _stop_owned_group(process)
                        self.assertEqual(reaped, [True])
                    else:
                        with self.assertRaisesRegex(CampaignProcessError, "Cannot stop owned") as caught:
                            _stop_owned_group(process)
                        self.assertFalse(caught.exception.stopped_verified)
                        self.assertEqual(reaped, [])
                send.assert_called_once_with(100, signal.SIGTERM)

    def test_saved_identity_never_authorizes_signalling(self):
        identity = {"pid": 92341, "pgid": 92341, "host": platform.node(),
                    "boot_id": "same-boot", "start_marker": "old-marker"}
        with patch("nasolve.campaign_process._boot_id", return_value="same-boot"), \
                patch("nasolve.campaign_process._group_alive", return_value=True) as check, \
                patch("nasolve.campaign_process.os.killpg") as signal_group:
            self.assertTrue(process_alive(identity))
        check.assert_called_once_with(92341)
        signal_group.assert_not_called()
        with patch("nasolve.campaign_process._boot_id", return_value="new-boot"), \
                patch("nasolve.campaign_process._group_alive") as check:
            self.assertFalse(process_alive(identity))
        check.assert_not_called()
        identity["host"] = "different-computer"
        self.assertIsNone(process_alive(identity))

    def test_escalation_reserves_owned_pid_until_all_signals_are_sent(self):
        process = SimpleNamespace(pid=12345, returncode=None)
        sent = []

        def reap(timeout):
            self.assertEqual(sent, [signal.SIGTERM, signal.SIGKILL])
            process.returncode = -signal.SIGKILL

        process.wait = reap
        with patch("nasolve.campaign_process.os.killpg", side_effect=lambda pid, sig: sent.append(sig)), \
                patch("nasolve.campaign_process._group_alive", side_effect=lambda pid: (
                    False if signal.SIGKILL in sent else True
                )), \
                patch("nasolve.campaign_process.time.monotonic", side_effect=count()), \
                patch("nasolve.campaign_process.time.sleep"):
            _stop_owned_group(process)
        self.assertEqual(process.returncode, -signal.SIGKILL)

    def test_uncertain_descendants_after_escalation_remain_an_error(self):
        process = SimpleNamespace(pid=12345, returncode=None)
        process.wait = lambda timeout: setattr(process, "returncode", -signal.SIGKILL)
        with patch("nasolve.campaign_process.os.killpg"), \
                patch("nasolve.campaign_process._group_alive", return_value=None), \
                patch("nasolve.campaign_process.time.monotonic", side_effect=count()), \
                patch("nasolve.campaign_process.time.sleep"):
            with self.assertRaisesRegex(CampaignProcessError, "did not stop verifiably"):
                _stop_owned_group(process)

    def test_unknown_or_malformed_identity_is_not_reported_inactive(self):
        for identity in (None, {}, {"host": platform.node(), "pid": 1, "pgid": 1},
                         {"host": platform.node(), "pid": 2, "pgid": True},
                         {"host": platform.node(), "pid": 10, "pgid": 11}):
            with self.subTest(identity=identity):
                self.assertIsNone(process_alive(identity))
        identity = current_process_identity()
        self.assertEqual(identity["pid"], os.getpid())
        self.assertEqual(identity["pgid"], os.getpgrp())
        self.assertIn("heartbeat_utc", identity)
        json.dumps(identity)

    def test_macos_boot_identity_does_not_depend_on_timezone_rendering(self):
        for suffix in ("Thu Sep 10 09:00:00 2026", "Thu Sep 10 11:00:00 2026"):
            with self.subTest(suffix=suffix), \
                    patch("nasolve.campaign_process.sys.platform", "darwin"), \
                    patch("nasolve.campaign_process.subprocess.run", return_value=SimpleNamespace(
                        returncode=0, stdout="{ sec = 1789023600, usec = 17 } " + suffix,
                    )):
                self.assertEqual(_boot_id(), "darwin-boot:1789023600:17")

    def test_non_posix_platform_has_clear_execution_error(self):
        with patch("nasolve.campaign_process.os.name", "nt"):
            with self.assertRaisesRegex(CampaignProcessError, "requires POSIX"):
                run_job(self.job)
            with self.assertRaisesRegex(CampaignProcessError, "requires POSIX"):
                with exclusive_lock(self.root / "lock"):
                    pass
