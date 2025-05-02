"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update In Loop
:Test ID:		F8
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case performs a full firmware update in a loop to ensure stability and verify that ongoing rollbacks are not affected by subsequent updates.
                The test stages the firmware update, activates it, and verifies the update in a loop.

                PASS Criteria: The test passes if N-1 & N firmware updates complete successfully without errors in the loop.
                FAIL Criteria: The test fails if any firmware update encounters an error in the loop.

:Usage 1:		python ctam.py -w ..\workspace -t F8
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update In Loop"

:Dependencies: 

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>

        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <CorruptComponentIdentifier>, <HasSignature>, <SignatureStructBytes>, <MetadataSizeBytes>
                                                        
        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
"""
from typing import Optional, List
from tests.test_case import TestCase
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.fw_update.fw_update_group_N._fw_update_group_N import (
    FWUpdateTestGroupN,
)

class CTAMTestFullDeviceUpdateInLoop(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update In Loop"
    test_id: str = "F8"
    score_weight: int = 10
    tags: List[str] = ["L1"]
    compliance_level: str = "L1"

    def __init__(self, group: FWUpdateTestGroupN):
        """
        _summary_
        """
        super().__init__()
        self.group = group

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
        failure_reason = ""
        result = True

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck(
                image_type="backup"
            )
            failure_reason += status_msg
            if not status:
                step1.add_log(LogSeverity.INFO, f"[{self.test_id}] : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )

        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
        with step2.scope():

            status, status_msg, task_id =self.group.fw_update_ifc.ctam_stage_fw(
                wait_for_stage_completion=False
            )
            failure_reason += " " + status_msg
            if status:
                step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
            else:
                step2.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                )
                failure_reason += " " + "FW Update Stage Failed"
                result = False
        
        unexpected_error = False
        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                keep_disturbing = True
                disturb_count = 1
                while keep_disturbing:
                    status, msg, _ = self.group.fw_update_ifc.ctam_stage_fw(image_type="backup")
                    failure_reason += " " + msg
                    if status:
                        keep_disturbing = False
                        step3.add_log(
                            LogSeverity.INFO,
                            f"{self.test_id} : FW Update restarted, Disturb Count = {disturb_count}",
                        )
                    elif msg.lower() == "ExpectedMessage".lower():
                        step3.add_log(
                            LogSeverity.ERROR,
                            f"{self.test_id} : FW Update Disturb Failed as expected",
                        )
                        disturb_count = disturb_count + 1
                    else:
                        step3.add_log(
                            LogSeverity.ERROR,
                            f"{self.test_id} : FW Update Disturb Failed, but with incorrect message.",
                        )
                        failure_reason += " " + "FW Update Disturb Failed, but with incorrect message."
                        keep_disturbing = False
                        unexpected_error = True

                if disturb_count == 1 and not unexpected_error:
                    result = False
                    step3.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Disturb was successful in first shot - Not Expected",
                    )
                    failure_reason += " " + f"{self.test_id} : FW Update Disturb was successful in first shot - Not Expected"
                if unexpected_error and task_id:
                    step3.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Failed with Unexpected error - Waiting for pervious FW staging to be completed",
                    )
                    failure_reason += " " + f"{self.test_id} : FW Update Failed with Unexpected error - Waiting for pervious FW staging to be completed"
                    status, json_data = self.group.fw_update_ifc.ctam_monitor_task(TaskID=task_id)
                

        if result or unexpected_error:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")  # type: ignore
            with step4.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_activate_ac()
                failure_reason += " " + status_msg
                if status:
                    step4.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                    )
                else:
                    step4.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Activation Failed",
                    )
                    failure_reason += " " + "FW Update Activation Failed"
                    result = False

        if result or unexpected_error:
            step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5")
            with step5.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify(image_type="backup")
                failure_reason += " " + status_msg
                if status:
                    step5.add_log(
                        LogSeverity.INFO,
                        f"{self.test_id} : Update Verification Completed",
                    )
                else:
                    step5.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : Update Verification Failed",
                    )
                    failure_reason += " " + "Update Verification Failed"
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result and not unexpected_error else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

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
            pass

        # call super teardown last
        super().teardown()
