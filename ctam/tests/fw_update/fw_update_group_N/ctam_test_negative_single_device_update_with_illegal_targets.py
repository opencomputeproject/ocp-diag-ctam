"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Single Device Update with illegal targets
:Test ID:		F32
:Group Name:	fw_update
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description:	This test case focuses on the scenario where a GPU baseboard has multiple targets, some of which are updatable
				and others which are not. The goal of this test case is to identify the list of firmware inventory targets
				that are **"not"** in the AllowableValues of the URI pointed by ``@Redfish.ActionInfo``. On attempting an
				update, we expect the firmware version to be retained.

				PASS Criteria:
				- The firmware version is retained when attempting to update targets that are not updatable.
				
				FAIL Criteria:
				- The firmware version changes when attempting to update targets that are not updatable.

:Usage 1:		python ctam.py -w ..\workspace -t F32
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Negative Single Device Update with illegal targets"

:Dependencies:

    .. code-block:: text 

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <MultiPartFormData>, <IsMultiPart>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>, <SingleShotPowerCycleTimeOut>
                            
        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <HasSignature>, <SignatureStructBytes>
                                                      
        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
"""
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

class CTAMTestNegativeSingleDeviceUpdateWithIllegalTargets(TestCase):
    """
    Test case to attempt update of targets which are not updateable. 

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Single Device Update with illegal targets"
    test_id: str = "F32"
    score_weight: int = 10
    tags: List[str] = ["Negative", "L3", "Single_Device"]
    compliance_level: str = "L3"
    spec_versions: Union[str, List[str]] = ">= 1.0"

    def __init__(self, group: FWUpdateTestGroupN):
        """
        _summary_
        """
        super().__init__()
        self.group = group
        self.exclude_targets = []

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

        component_list = self.group.fw_update_ifc.ctam_get_updateable_devices_in_bundle(illegal=1)
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if self.group.fw_update_ifc.ctam_selectpartiallist(
                count=1, 
                illegal=1, 
                specific_targets=component_list,
                excluded_targets=self.exclude_targets
            ):
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
            else:
                step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                failure_reason += "Single Device Selection Failed"
                result = False
            
        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck()
                failure_reason = status_msg
                if not status:
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                else:
                    step2.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Not Required, going ahead nevertheless"
                    )

        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                status, status_msg, task_id, _ = self.group.fw_update_ifc.ctam_stage_fw(
                    partial=1, specific_targets=component_list)
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
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify(image_type="negate")
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
