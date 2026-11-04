"""
Copyright (c) Google LLC

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Description: Perturbs the host OS of the system under test (e.g. device resets, driver reloads,
              reboots) while a long operation, such as firmware staging, is in progress.
"""

import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from ocptv.output import LogSeverity

from utils.host_connection import HostCommandResult, HostConnection

# Keys of a HostPerturbations entry in dut_info.json.
_CONFIG_KEYS = frozenset(
    {
        "Name",
        "Command",
        "StartCommand",
        "StopCommand",
        "IntervalSeconds",
        "MaxCount",
        "ExpectDisconnect",
        "TimeoutSeconds",
    }
)


@dataclass
class HostPerturbation:
    """
    One entry of HostPerturbations in dut_info.json.

    :param name: Name used in logs
    :param command: Command run on the host while the operation is in progress
    :param start_command: Command run once before the operation, e.g. to start a background load,
                          and again after the host comes back from a reboot
    :param stop_command: Command run once after the operation, e.g. to stop the background load
    :param interval_seconds: Minimum seconds between two runs of command
    :param max_count: Maximum runs of command, 0 for no limit
    :param expect_disconnect: command takes the host down, e.g. a reboot
    :param timeout_seconds: Timeout of each command, and how long an expect_disconnect command
                            has to take the host down
    """

    name: str
    command: str = ""
    start_command: str = ""
    stop_command: str = ""
    interval_seconds: int = 0
    max_count: int = 0
    expect_disconnect: bool = False
    timeout_seconds: int = 120

    @classmethod
    def from_config(cls, entry: dict) -> "HostPerturbation":
        """
        :param entry: HostPerturbations entry from dut_info.json
        :return: The perturbation
        :raises ValueError: The entry is malformed
        """
        if not isinstance(entry, dict):
            raise ValueError(f"entry must be an object: {entry!r}")
        unknown = sorted(set(entry) - _CONFIG_KEYS)
        if unknown:
            raise ValueError(f"unknown keys {unknown} in {entry!r}")

        def text(key):
            value = entry.get(key, "")
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string in {entry!r}")
            return value.strip()

        def count(key, default):
            try:
                value = int(entry.get(key, default))
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be an integer in {entry!r}") from None
            if value < 0:
                raise ValueError(f"{key} must not be negative in {entry!r}")
            return value

        expect_disconnect = entry.get("ExpectDisconnect", False)
        if not isinstance(expect_disconnect, bool):
            raise ValueError(f"ExpectDisconnect must be true or false in {entry!r}")
        perturbation = cls(
            name=text("Name"),
            command=text("Command"),
            start_command=text("StartCommand"),
            stop_command=text("StopCommand"),
            interval_seconds=count("IntervalSeconds", 0),
            max_count=count("MaxCount", 0),
            expect_disconnect=expect_disconnect,
            timeout_seconds=count("TimeoutSeconds", 120),
        )
        if not perturbation.name:
            raise ValueError(f"Name is required in {entry!r}")
        if not (perturbation.command or perturbation.start_command):
            raise ValueError(f"{perturbation.name}: Command or StartCommand is required")
        if perturbation.expect_disconnect and not perturbation.command:
            raise ValueError(f"{perturbation.name}: ExpectDisconnect needs a Command")
        if not perturbation.timeout_seconds:
            raise ValueError(f"{perturbation.name}: TimeoutSeconds must be positive")
        return perturbation


def parse_host_perturbations(entries) -> List[HostPerturbation]:
    """
    :param entries: Value of HostPerturbations in dut_info.json
    :return: The perturbations, in order
    :raises ValueError: The value is malformed
    """
    if not entries:
        return []
    if not isinstance(entries, list):
        raise ValueError(f"HostPerturbations must be a list: {entries!r}")
    perturbations = [HostPerturbation.from_config(entry) for entry in entries]
    names = [perturbation.name for perturbation in perturbations]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate names {duplicates}")
    return perturbations


@dataclass
class PerturbationEvent:
    """
    A host command run by HostPerturbationRunner.

    :param name: Name of the perturbation
    :param action: "start", "restart", "run" or "stop"
    :param elapsed: Seconds since HostPerturbationRunner.start()
    :param result: Outcome of the command
    :param effective: The command took effect (see HostPerturbationRunner)
    :param percent_complete: PercentComplete of the task when the command ran, if known
    :param note: Extra detail for the log
    """

    name: str
    action: str
    elapsed: float
    result: HostCommandResult
    effective: bool
    percent_complete: Optional[int] = None
    note: str = ""

    def __str__(self) -> str:
        text = f"[+{self.elapsed:.0f} s] {self.name} {self.action}: rc={self.result.rc}"
        if self.percent_complete is not None:
            text += f", task {self.percent_complete}% complete"
        if self.note:
            text += f", {self.note}"
        if self.result.error:
            text += f", error: {self.result.error}"
        elif not self.result.ok and self.result.stderr.strip():
            text += f", stderr: {self.result.stderr.strip()[-300:]}"
        return text


class HostPerturbationRunner:
    """
    Perturbs the host OS while an operation is in progress. Call start() right before the
    operation, poll() each time the operation is found still in progress (e.g. as the on_poll
    callback of ctam_monitor_task), and stop() once it is over.

    * start() runs every StartCommand, e.g. to start background loads. They run again when the
      host comes back from a reboot. stop() runs every StopCommand.
    * Each poll() runs the Command of the next due perturbation, round robin in list order, so the
      perturbations are spread over the operation. A perturbation is due once IntervalSeconds have
      passed since it last ran, until it has run MaxCount times.
    * While the host is down after an ExpectDisconnect perturbation (e.g. a reboot), poll() only
      checks whether it is back. stop() waits for it for up to HostBootWaitTime.

    A command takes effect if it exits 0 or, for ExpectDisconnect, if the host goes down. Commands
    that fail (e.g. a device reset refused because the device is busy) are logged, not raised: the
    caller judges the operation under perturbation, not the perturbations.
    """

    def __init__(
        self,
        perturbations: List[HostPerturbation],
        host: HostConnection,
        run_command: Callable[[str, int], HostCommandResult],
        log: Callable[[LogSeverity, str], None],
    ):
        """
        :param perturbations: Perturbations to run
        :param host: Connection used to check whether the host is up
        :param run_command: Runs and logs a host command, e.g. CompToolDut.run_host_command
        :param log: Logs a message, e.g. TestRun.add_log
        """
        self.perturbations = perturbations
        self.host = host
        self.events: List[PerturbationEvent] = []
        # The host did not come back from a reboot within HostBootWaitTime.
        self.host_lost = False
        self._run_command = run_command
        self._log = log
        self._start_time = None
        self._last_run = {}  # name -> time.monotonic() of the last run of its command
        self._runs = {}  # name -> runs of its command
        self._next = 0  # round-robin position among the perturbations with a command
        self._host_down_since = None
        self._loads_running = False
        self._stopped = False

    @property
    def effective_count(self) -> int:
        """Number of host commands that took effect."""
        return sum(1 for event in self.events if event.effective)

    def start(self) -> None:
        """Runs every StartCommand."""
        self._start_time = time.monotonic()
        self._start_loads("start")

    def poll(self, task: Optional[dict] = None) -> None:
        """
        Runs the next due perturbation, or checks whether the host is back from a reboot.

        :param task: Latest JSON of the task in progress, for the log
        """
        if self._stopped or self.host_lost:
            return
        if self._host_down_since is not None:
            self._check_host_back()
            return
        perturbation = self._next_due()
        if perturbation is None:
            return
        percent = (task or {}).get("PercentComplete")
        self._last_run[perturbation.name] = time.monotonic()
        self._runs[perturbation.name] = self._runs.get(perturbation.name, 0) + 1
        result = self._run_command(perturbation.command, perturbation.timeout_seconds)
        if not perturbation.expect_disconnect:
            self._record(perturbation, "run", result, result.ok, percent)
            return
        went_down = self.host.wait_until_unreachable(timeout=perturbation.timeout_seconds)
        if went_down:
            self._host_down_since = time.monotonic()
            self._loads_running = False  # The reboot killed them.
            note = "host went down"
        else:
            note = f"host still up {perturbation.timeout_seconds} s later"
        self._record(perturbation, "run", result, went_down, percent, note)

    def stop(self) -> None:
        """Waits for the host if it is down, then runs every StopCommand. Safe to call twice."""
        if self._stopped:
            return
        self._stopped = True
        if self._host_down_since is not None and not self.host_lost:
            remaining = max(0.0, self.host.boot_wait_time - (time.monotonic() - self._host_down_since))
            self._log(LogSeverity.INFO, f"Waiting up to {remaining:.0f} s for the host to come back")
            if self.host.wait_until_reachable(timeout=remaining):
                down_for = time.monotonic() - self._host_down_since
                self._host_down_since = None
                self._log(LogSeverity.INFO, f"Host is back after {down_for:.0f} s")
            else:
                self._lose_host()
        if self._loads_running and not self.host_lost:
            for perturbation in self.perturbations:
                if perturbation.stop_command:
                    result = self._run_command(perturbation.stop_command, perturbation.timeout_seconds)
                    self._record(perturbation, "stop", result, False)
            self._loads_running = False

    def summary(self) -> str:
        """
        :return: For each perturbation, how many of its commands took effect
        """
        parts = []
        for perturbation in self.perturbations:
            events = [event for event in self.events if event.name == perturbation.name and event.action != "stop"]
            effective = sum(1 for event in events if event.effective)
            parts.append(f"{perturbation.name}: {effective}/{len(events)} took effect")
        return ", ".join(parts)

    def _start_loads(self, action: str) -> None:
        for perturbation in self.perturbations:
            if perturbation.start_command:
                result = self._run_command(perturbation.start_command, perturbation.timeout_seconds)
                self._record(perturbation, action, result, result.ok)
                self._loads_running = True

    def _next_due(self) -> Optional[HostPerturbation]:
        candidates = [perturbation for perturbation in self.perturbations if perturbation.command]
        now = time.monotonic()
        for offset in range(len(candidates)):
            index = (self._next + offset) % len(candidates)
            perturbation = candidates[index]
            if perturbation.max_count and self._runs.get(perturbation.name, 0) >= perturbation.max_count:
                continue
            last_run = self._last_run.get(perturbation.name)
            if last_run is not None and now - last_run < perturbation.interval_seconds:
                continue
            self._next = index + 1
            return perturbation
        return None

    def _check_host_back(self) -> None:
        down_for = time.monotonic() - self._host_down_since
        if self.host.is_reachable():
            self._host_down_since = None
            self._log(LogSeverity.INFO, f"Host is back after {down_for:.0f} s")
            self._start_loads("restart")
        elif down_for > self.host.boot_wait_time:
            self._lose_host()

    def _lose_host(self) -> None:
        self.host_lost = True
        self._log(LogSeverity.ERROR, f"Host did not come back within {self.host.boot_wait_time} s")

    def _record(self, perturbation, action, result, effective, percent=None, note="") -> None:
        elapsed = time.monotonic() - self._start_time if self._start_time is not None else 0.0
        event = PerturbationEvent(perturbation.name, action, elapsed, result, effective, percent, note)
        self.events.append(event)
        succeeded = result.ok if action == "stop" else effective
        self._log(LogSeverity.INFO if succeeded else LogSeverity.WARNING, f"Host perturbation {event}")
