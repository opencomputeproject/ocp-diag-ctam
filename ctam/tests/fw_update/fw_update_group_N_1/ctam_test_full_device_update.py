r"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update
:Test ID:		F1
:Group Name:	fw_update
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description:	Basic test case of full firmware update. This test case verifies the successful execution of a full firmware update process.

                PASS Criteria:
				- The firmware update process completes successfully and the firmware is updated to the new version.
				
				FAIL Criteria:
				- The firmware update process fails or the firmware is not updated to the new version.
    
:Usage 1:		python ctam.py -w ..\workspace -t F1
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update"

:Dependencies: 

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>, <SingleShotPowerCycleTimeOut>

        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <HasSignature>, <SignatureStructBytes>
                                                        
        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
r"""
import os
import json
from typing import Optional, List, Union
from tests.test_case import TestCase
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.fw_update.fw_update_group_N_1._fw_update_group_N_1 import (
    FWUpdateTestGroupNMinus1,
)


class CTAMTestFullDeviceUpdate(TestCase):
    r"""
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    r"""

    test_name: str = "CTAM Test Full Device Update"
    test_id: str = "F1"
    score_weight: int = 10
    tags: List[str] = ["Compliance", "L0"]
    compliance_level: str = "L0"
    spec_versions: Union[str, List[str]] = ">= 1.0"

    def __init__(self, group: FWUpdateTestGroupNMinus1):
        r"""
        _summary_
        r"""
        super().__init__()
        self.group = group

    def setup(self):
        r"""
        set environment state for this test only
        r"""
        # call super first
        super().setup()

        # add custom setup here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  setup()...")
        with step1.scope():
            pass

    def run(self) -> TestResult:
        r"""
        actual test verification
        r"""
        result = True
        failure_reason = ""
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck()
            failure_reason = status_msg
            if not status:
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )

        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
        with step2.scope():
            status, status_msg, task_id, _ = self.group.fw_update_ifc.ctam_stage_fw(is_force_update=False)
            failure_reason = status_msg
            if status:
                step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
            else:
                step2.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                )
                failure_reason = "FW Update Stage Failed"
                result = False
        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                status, status_msg, activation_time = self.group.fw_update_ifc.ctam_activate_ac()
                self.activation_time = round(activation_time, 2)
                self.activation_status = status
                self.activation_failure_reason = status_msg
                failure_reason = status_msg
                if status:
                    step3.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                    )
                else:
                    step3.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Activation Failed",
                    )
                    failure_reason = "FW Update Activation Failed"
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")
            with step4.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify()
                failure_reason = status_msg
                if status:
                    step4.add_log(
                        LogSeverity.INFO,
                        f"{self.test_id} : Update Verification Completed",
                    )
                else:
                    step4.add_log(
                        LogSeverity.INFO, f"{self.test_id} : Update Verification Failed"
                    )
                    failure_reason = "Update Verification Failed"
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight
        self.test_status = result
        # call super last to log result and score
        super().run()
        return self.result, failure_reason

    def teardown(self):
        r"""
        undo environment state change from setup() above, this function is called even if run() fails or raises exception
        r"""
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            pass

        # call super teardown last
        super().teardown()
