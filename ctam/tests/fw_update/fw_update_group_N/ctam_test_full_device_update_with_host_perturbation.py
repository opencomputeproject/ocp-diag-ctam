r"""
Copyright (c) Google LLC
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update With Host Perturbation During Staging
:Test ID:		F91
:Group Name:	fw_update
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description:
    Firmware update denial of service check: the host OS must not be able to disrupt an out-of-band
    firmware update. While a full device firmware update is staging, this test perturbs the host OS
    in-band with the commands in HostPerturbations (e.g. in-band device queries, device resets,
    driver reloads, host reboots). It then activates the update with an AC power cycle and verifies
    the firmware versions. See "Host Connection" in the README for the configuration.

:PASS Criteria:
    - Staging completes successfully despite the host perturbations.
    - At least one host perturbation takes effect while staging is in progress.
    - The host OS comes back within HostBootWaitTime after a host reboot.
    - The update activates and the firmware inventory matches the bundle.

:FAIL Criteria:
    - The host connection or HostPerturbations is not configured, or the host OS is not reachable.
    - Staging fails, or no host perturbation takes effect while staging is in progress.
    - The host OS does not come back, activation fails, or the firmware inventory does not match the bundle.

:Usage 1:		python ctam.py -w ..\workspace -t F91
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update With Host Perturbation During Staging"

:Dependencies:

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>

        <dut_info.json>                   : Required - <HostIPAddress> or <HostCommandPrefix>, <HostPerturbations>, <FwActivationTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <HostPort>, <HostSSHKeyFile>, <HostBootWaitTime>, <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>, <SingleShotPowerCycleTimeOut>

        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <HasSignature>, <SignatureStructBytes>

        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
"""

import time
from typing import List, Union
from tests.test_case import TestCase
from ocptv.output import (
    LogSeverity,
    TestResult,
)
from tests.fw_update.fw_update_group_N._fw_update_group_N import (
    FWUpdateTestGroupN,
)
from utils.host_perturbation import HostPerturbationRunner, parse_host_perturbations


class CTAMTestFullDeviceUpdateWithHostPerturbation(TestCase):
    """
    Verify that perturbing the host OS while a full device firmware update is staging does not keep
    the update from completing

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update With Host Perturbation During Staging"
    test_id: str = "F91"
    score_weight: int = 10
    tags: List[str] = ["Host", "L3"]
    compliance_level: str = "L3"
    spec_versions: Union[str, List[str]] = ">= 1.0"

    def __init__(self, group: FWUpdateTestGroupN):
        """
        _summary_
        """
        super().__init__()
        self.group = group
        self.perturbation_runner = None

    def setup(self):
        """
        set environment state for this test only
        """
        # call super first
        super().setup()

        # add custom setup here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  setup()...")
        with step1.scope():
            pass

    def run(self) -> TestResult:
        """
        actual test verification
        """
        result = True
        failure_reason = ""
        host = self.dut().host
        perturbations = []
        task_id = None

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            try:
                perturbations = parse_host_perturbations(
                    self.dut().dut_config.get("HostPerturbations", {}).get("value", [])
                )
            except ValueError as e:
                failure_reason = f"Invalid HostPerturbations in dut_info.json: {e}"
            else:
                if not perturbations:
                    failure_reason = "HostPerturbations is empty in dut_info.json"
                elif not host.is_configured:
                    failure_reason = (
                        "Host connection is not configured (HostIPAddress or HostCommandPrefix in dut_info.json)"
                    )
                else:
                    probe = host.probe()
                    if not probe.ok:
                        detail = probe.error or probe.stderr.strip() or f"rc={probe.rc}"
                        failure_reason = f"Host OS is not reachable: {detail}"
            if failure_reason:
                step1.add_log(LogSeverity.ERROR, f"{self.test_id} : {failure_reason}")
                result = False
            else:
                step1.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : Host OS reachable, perturbations: "
                    + ", ".join(perturbation.name for perturbation in perturbations),
                )

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck()
                if not status:
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                else:
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Not Required")

        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                # Logs at run level: the runner keeps logging while step4 monitors staging.
                self.perturbation_runner = HostPerturbationRunner(
                    perturbations, host, self.dut().run_host_command, self.test_run().add_log
                )
                self.perturbation_runner.start()
                status, status_msg, task_id, _ = self.group.fw_update_ifc.ctam_stage_fw(wait_for_stage_completion=False)
                if status and task_id:
                    step3.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staging Started, task {task_id}")
                else:
                    failure_reason = status_msg or "FW Update Staging did not start"
                    step3.add_log(LogSeverity.ERROR, f"{self.test_id} : {failure_reason}")
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")  # type: ignore
            with step4.scope():
                staging_start_time = time.time()
                try:
                    staged, task = self.group.fw_update_ifc.ctam_monitor_task(
                        task_id, on_poll=self.perturbation_runner.poll
                    )
                finally:
                    self.staging_time = round(time.time() - staging_start_time, 2)
                    self.perturbation_runner.stop()
                self.staging_status = staged
                step4.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : Staging took {self.staging_time} s under host perturbation"
                    f" ({self.perturbation_runner.summary()})",
                )
                baseline = self.measurements.get("F0", {}) if getattr(self, "measurements", None) else {}
                if baseline.get("test_status") and baseline.get("staging_time"):
                    step4.add_log(
                        LogSeverity.INFO,
                        f"{self.test_id} : Staging took {baseline['staging_time']} s without host perturbation (F0)",
                    )
                if not staged:
                    if task.get("TaskState") in (None, "Running"):
                        # ctam_monitor_task gave up after consecutive failed polls.
                        failure_reason = "FW Update Staging task stopped answering under host perturbation (last PercentComplete: {})".format(
                            task.get("PercentComplete")
                        )
                    else:
                        failure_reason = (
                            "FW Update Staging failed under host perturbation: TaskState={}, TaskStatus={}".format(
                                task.get("TaskState"), task.get("TaskStatus")
                            )
                        )
                elif not self.perturbation_runner.effective_count:
                    failure_reason = "No host perturbation took effect while staging was in progress"
                elif self.perturbation_runner.host_lost:
                    failure_reason = f"Host OS did not come back within {host.boot_wait_time} s"
                if failure_reason:
                    self.staging_failure_reason = failure_reason
                    step4.add_log(LogSeverity.ERROR, f"{self.test_id} : {failure_reason}")
                    result = False
                else:
                    step4.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")

        if result:
            step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5")  # type: ignore
            with step5.scope():
                status, status_msg, activation_time = self.group.fw_update_ifc.ctam_activate_ac()
                self.activation_time = round(activation_time, 2)
                self.activation_status = status
                self.activation_failure_reason = status_msg
                if status:
                    step5.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Activate")
                else:
                    failure_reason = status_msg or "FW Update Activation Failed"
                    step5.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Activation Failed : {failure_reason}")
                    result = False

        if result:
            step6 = self.test_run().add_step(f"{self.__class__.__name__} run(), step6")  # type: ignore
            with step6.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify()
                if status:
                    step6.add_log(LogSeverity.INFO, f"{self.test_id} : Update Verification Completed")
                else:
                    failure_reason = f"Update Verification Failed : {status_msg}"
                    step6.add_log(LogSeverity.ERROR, f"{self.test_id} : {failure_reason}")
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight
            failure_reason = ""
        self.test_status = result

        # call super last to log result and score
        super().run()
        return self.result, failure_reason

    def teardown(self):
        """
        undo environment state change from setup() above, this function is called even if run() fails or raises exception
        """
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            if self.perturbation_runner:
                # Stops background loads and waits for the host, even if run() raised.
                self.perturbation_runner.stop()

        # call super teardown last
        super().teardown()
