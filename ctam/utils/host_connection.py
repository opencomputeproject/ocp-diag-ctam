"""
Copyright (c) Google LLC

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Description: Runs commands on the host OS of the system under test.
"""

import logging
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

# A no-op accepted by POSIX shells, cmd.exe and PowerShell.
_NO_OP_COMMAND = "exit 0"

# Log channel of the built-in SSH client. paramiko logs failed connections, e.g. while the host reboots,
# with tracebacks from its own thread. They are already returned in HostCommandResult.error, so the
# NullHandler keeps them off the console unless logging is configured to show them.
_SSH_LOG_CHANNEL = "paramiko.transport.host_connection"
logging.getLogger(_SSH_LOG_CHANNEL).addHandler(logging.NullHandler())


def _text(output) -> str:
    """Returns captured output as text; TimeoutExpired holds bytes even in text mode."""
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode(errors="replace")
    return output


@dataclass
class HostCommandResult:
    """
    Outcome of a command run on the host OS.

    :param command: Command run on the host
    :param rc: Exit status, or None if the command could not be run or did not finish in time
    :param stdout: Standard output
    :param stderr: Standard error
    :param error: Why the command could not be run or did not finish, if so
    """

    command: str
    rc: Optional[int]
    stdout: str = ""
    stderr: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.rc == 0


class HostConnection:
    """
    Connection to the host OS of the system under test: the OS running on the host CPU, as opposed
    to the management controllers that CTAM talks to over Redfish. Tests use it to act in-band,
    e.g. to perturb the host while a firmware update is in progress.

    Commands go through one of two transports:

    * If HostCommandPrefix is set, the command is appended to it as a single argument and run
      locally, e.g. with "ssh -o BatchMode=yes root@myhost". Use it for jump hosts, SSH
      certificates, sshpass or any other wrapper.
    * Otherwise the built-in SSH client (paramiko) connects to HostIPAddress:HostPort, with the
      .netrc credentials for HostIPAddress and/or HostSSHKeyFile.

    Nothing connects until the first command, so runs that do not use the host are unaffected.
    """

    def __init__(self, dut_config: dict, net_rc=None):
        """
        :param dut_config: "properties" of dut_info.json
        :param net_rc: Parsed .netrc holding the host credentials, if any
        """

        def value(key, default):
            setting = dut_config.get(key, {}).get("value", default)
            return default if setting in (None, "") else setting

        def integer(key, default):
            # A bad optional setting must not keep tests that do not use the host from running.
            setting = value(key, default)
            try:
                return int(setting)
            except (TypeError, ValueError):
                self._config_errors.append(f"{key} must be an integer, not {setting!r}")
                return default

        self._config_errors = []
        self.ip_address = value("HostIPAddress", "")
        self.port = integer("HostPort", 22)
        self.ssh_key_file = value("HostSSHKeyFile", None)
        self.command_prefix = value("HostCommandPrefix", "")
        self.boot_wait_time = integer("HostBootWaitTime", 900)
        self._net_rc = net_rc
        self._client = None

    @property
    def is_configured(self) -> bool:
        """True if dut_info.json says how to reach the host."""
        return bool(self.command_prefix or self.ip_address)

    def run(self, command: str, timeout: int = 60) -> HostCommandResult:
        """
        Runs a command on the host. Never raises: if the command cannot be run or does not finish
        within the timeout, the result has rc None and says why in error.

        :param command: Command line for the host's shell
        :param timeout: Seconds to wait for the command
        :return: Outcome of the command
        :rtype: HostCommandResult
        """
        if not self.is_configured:
            return HostCommandResult(
                command, None, error="host connection is not configured (HostIPAddress or HostCommandPrefix)"
            )
        if self._config_errors:
            return HostCommandResult(command, None, error="; ".join(self._config_errors))
        if self.command_prefix:
            return self._run_with_prefix(command, timeout)
        return self._run_with_ssh(command, timeout)

    def probe(self, timeout: int = 15) -> HostCommandResult:
        """
        Runs a no-op command, to check that the host answers.

        :param timeout: Seconds to wait for the host to answer
        :return: Outcome of the no-op command
        :rtype: HostCommandResult
        """
        return self.run(_NO_OP_COMMAND, timeout=timeout)

    def is_reachable(self, timeout: int = 15) -> bool:
        """
        :param timeout: Seconds to wait for the host to answer
        :return: True if the host runs a no-op command within the timeout
        """
        return self.probe(timeout).ok

    def wait_until_reachable(self, timeout: float, interval: int = 15) -> bool:
        """
        Waits for the host to answer, e.g. after a reboot.

        :param timeout: Maximum seconds to wait
        :param interval: Seconds between two checks
        :return: True if the host answered within the timeout
        """
        deadline = time.monotonic() + timeout
        while not self.is_reachable():
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval)
        return True

    def wait_until_unreachable(self, timeout: float, interval: int = 5) -> bool:
        """
        Waits for the host to stop answering, e.g. after a reboot command. The host counts as down
        after two failed checks in a row, so that one slow answer is not mistaken for a reboot.

        :param timeout: Maximum seconds to wait
        :param interval: Seconds between two checks
        :return: True if the host stopped answering within the timeout
        """
        deadline = time.monotonic() + timeout
        failed_checks = 0
        while True:
            failed_checks = 0 if self.is_reachable() else failed_checks + 1
            if failed_checks >= 2:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval)

    def close(self) -> None:
        """Closes the built-in SSH client, if connected."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _run_with_prefix(self, command: str, timeout: int) -> HostCommandResult:
        argv = shlex.split(self.command_prefix) + [command]
        try:
            completed = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            return HostCommandResult(
                command, None, _text(e.stdout), _text(e.stderr), f"did not finish within {timeout} s"
            )
        except OSError as e:
            return HostCommandResult(command, None, error=f"cannot run {argv[0]}: {e}")
        return HostCommandResult(command, completed.returncode, completed.stdout, completed.stderr)

    def _run_with_ssh(self, command: str, timeout: int) -> HostCommandResult:
        try:
            client = self._ssh_client(timeout)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            stdin.close()
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            rc = stdout.channel.recv_exit_status()
        except Exception as e:  # paramiko, socket and timeout errors
            # Reconnect on the next command, e.g. once a rebooted host is back.
            self.close()
            return HostCommandResult(command, None, error=f"{type(e).__name__}: {e}")
        if rc == -1:
            # The channel closed without an exit status, e.g. because the host went down.
            self.close()
            return HostCommandResult(command, None, out, err, "connection closed without an exit status")
        return HostCommandResult(command, rc, out, err)

    def _ssh_client(self, timeout: int):
        transport = self._client.get_transport() if self._client else None
        if transport is not None and transport.is_active():
            return self._client
        self.close()
        import paramiko  # Only the built-in SSH transport needs paramiko.

        username = password = None
        credentials = self._net_rc.authenticators(self.ip_address) if self._net_rc else None
        if credentials:
            username, _, password = credentials
        client = paramiko.SSHClient()
        client.set_log_channel(_SSH_LOG_CHANNEL)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.ip_address,
            port=self.port,
            username=username,
            password=password or None,
            key_filename=self.ssh_key_file,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
        )
        self._client = client
        return client
