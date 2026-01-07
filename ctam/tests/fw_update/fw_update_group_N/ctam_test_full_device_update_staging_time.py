"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update Staging Time
:Test ID:		F63
:Group Name:	fw_update
:Score Weight:	10
:Spec Versions: ">= 1.0"

Description:	
    This test verifies that the firmware copy operation (staging) does not exceed the maximum time specified in the requirements(FwStagingTimeMax). 
    The test involves performing a pre-check to ensure the device is capable of firmware updates, followed by staging the firmware update and verifying the operation's success.

:PASS Criteria:	
    - The firmware updation process should not exceed the maximum time specified in the requirements(FwStagingTimeMax).

:FAIL Criteria:	
    - The firmware staging operation fails or does not complete within the specified time(FwStagingTimeMax).
    
:Usage 1:		python ctam.py -w ..\workspace -t F63
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update Staging Time"

:Dependencies: 

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>
                            
        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <CorruptComponentIdentifier>, <HasSignature>, <SignatureStructBytes>
                                                      
        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
"""
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
from tests.fw_update.fw_update_group_N._fw_update_group_N import (
    FWUpdateTestGroupN,
)


class CTAMTestFullDeviceUpdateStagingTime(TestCase):
    """
    Verfy that firmware copy operation (staging) does not exceed the max time specified in the requirements

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update Staging Time"
    test_id: str = "F63"
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
        staging_time = None
        skip_to_step_6 = False

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            # check if F0 ran
            if self.measurements.get("F0", {}).get("staging_time", 0.0) != 0.0:
                if self.measurements.get("F0", {}).get("test_status", False) is False:
                    result = False
                    failure_reason = "F0 test failed"
                    step1.add_log(
                        LogSeverity.ERROR, f"{self.test_id} : {failure_reason}, skipping all steps"
                    )
                else:
                    staging_time = self.measurements["F0"].get("staging_time")
                    print(f"Time took to stage: {staging_time:.3f} secs")
                    step1.add_log(
                            LogSeverity.INFO, f"{self.test_id} : Skipping to step 6"
                        )
                    skip_to_step_6 = True    
            else:
                step1.add_log(
                        LogSeverity.INFO, f"{self.test_id} : Staging time not found, going to step 2"
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
                status, status_msg, _, staging_time = self.group.fw_update_ifc.ctam_stage_fw()
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
                    status, status_msg, _ = self.group.fw_update_ifc.ctam_activate_ac()
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
                if staging_time:
                    status, status_msg = self.group.fw_update_ifc.ctam_stage_time_check(staging_time)
                    if status:
                        failure_reason = f"Measured Staging Time: {staging_time:.3f} secs"
                        step6.add_log(
                            LogSeverity.INFO,
                            f"{self.test_id} : FW Update Staging Time under Threshold",
                        )
                    else:
                        step6.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update staging time too long"
                        )
                        failure_reason = status_msg
                        result = False      
                else:
                    step6.add_log(
                            LogSeverity.INFO, f"{self.test_id} : Unable to get FW Update staging time "
                        )
                    failure_reason = "Unable to get FW Update staging time"
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
