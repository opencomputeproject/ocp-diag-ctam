"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update Activation Time
:Test ID:		F64
:Group Name:	fw_update
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description:	This test case verifies that the firmware activation operation does not exceed the maximum time specified 
                in the requirements. The test stages the firmware update, activates it, and verifies the update within the 
                specified time. The activation time is checked to ensure it does not exceed the maximum allowed time 
                (FwActivationTimeMax) as defined in the device configuration.

:PASS Criteria: The test passes if the firmware activation completes within the maximum allowed time (FwActivationTimeMax) 
                and the GPU is reachable and enabled after activation.

:FAIL Criteria: The test fails if the firmware activation exceeds the maximum allowed time (FwActivationTimeMax), the GPU 
                is not reachable or not enabled after activation, or the verification fails.

:Usage 1:		python ctam.py -w ..\workspace -t F64
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update Activation Time"

:Dependencies:

    .. code-block:: text 

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>

        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <HasSignature>, <SignatureStructBytes>
                            
        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
"""

import os
import json
import time
from typing import Optional, List, Union
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


class CTAMTestFullDeviceUpdateActivationTime(TestCase):
    """
    Verify that firmware activation operation does not exceed the max time specified in the requirements

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update Activation Time"
    test_id: str = "F64"
    score_weight: int = 10
    tags: List[str] = ["L1"]
    compliance_level: str = "L1"
    spec_versions: Union[str, List[str]] = ">= 1.0"

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
        result = True
        failure_reason = ""
        activation_time = None
        fwupd_hyst_wait = True
        skip_to_step_6 = False

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            # check if F1 ran
            if self.measurements.get("F1", {}).get("activation_time", 0.0) != 0.0: 
                # check if F1 passed
                if self.measurements.get("F1", {}).get("test_status", False) is False:
                    result = False
                    failure_reason = "F1 test failed"
                    step1.add_log(
                        LogSeverity.ERROR, f"{self.test_id} : {failure_reason}, skipping all steps"
                    )
                else:    
                    activation_time = self.measurements["F1"].get("activation_time")
                    fwupd_hyst_wait = False
                    step1.add_log(LogSeverity.INFO, f"{self.test_id} : Time took for activation : {activation_time:.3f} secs")
                    step1.add_log(LogSeverity.INFO, f"{self.test_id} : Skipping to step 6")
                    skip_to_step_6 = True 
            else:
                step1.add_log(
                        LogSeverity.INFO, f"{self.test_id} : Activation time not found, going to step 2"
                    )
        if result and not skip_to_step_6:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck()
                failure_reason = status_msg
                if not status:
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                else:
                    step2.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                    )

            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                status, status_msg, _, _ = self.group.fw_update_ifc.ctam_stage_fw()
                failure_reason = status_msg
                if status:
                    step3.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
                else:
                    step3.add_log(
                        LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                    )
                    failure_reason = "FW Update Stage Failed"
                    result = False

            if result:
                step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")  # type: ignore
                with step4.scope():
                    status, status_msg, activation_time = self.group.fw_update_ifc.ctam_activate_ac()
                    failure_reason = status_msg
                    if status:
                        step4.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                        )
                    else:
                        step4.add_log(
                            LogSeverity.ERROR,
                            f"{self.test_id} : FW Update Activation Failed",
                        )
                        failure_reason = "FW Update Activation Failed"
                        result = False
                    
            if result:
                step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5")
                with step5.scope():
                    status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify()
                    failure_reason = status_msg
                    if status:
                        step5.add_log(
                            LogSeverity.INFO,
                            f"{self.test_id} : Update Verification Completed",
                        )
                    else:
                        step5.add_log(
                            LogSeverity.INFO, f"{self.test_id} : Update Verification Failed"
                        )
                        failure_reason = "Update Verification Failed"
                        result = False
        if result:
            step6 = self.test_run().add_step(f"{self.__class__.__name__} run(), step6")
            with step6.scope():
                if activation_time:
                    status, status_msg = self.group.fw_update_ifc.ctam_activate_time_check(activation_time, fwupd_hyst_wait=fwupd_hyst_wait)  # ctam_activate_time_check
                    if status:
                        failure_reason = f"Measured activation time: {activation_time:.3f} secs"
                        step6.add_log(
                            LogSeverity.INFO,
                            f"{self.test_id} : FW Update Activate Time under threshold",
                        )
                    else:
                        step6.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update activation time too long"
                        )
                        failure_reason = status_msg
                        result = False      
                else:
                    step6.add_log(
                            LogSeverity.INFO, f"{self.test_id} : Unable to get FW Update activation time "
                        )
                    failure_reason = "Unable to get FW Update activation time"
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
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
