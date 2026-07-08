r"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update Activation With Failed Component
:Test ID:		F56
:Group Name:	fw_update
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description: This test verifies the robustness of the firmware update stack when one component fails to stage. 
              The vendor must provide a firmware package where one component image is corrupted, while all other 
              component images are valid(If it not provided in package info testcase can generate). 
              The test performs the following steps:
              1. Retrieves the component to be corrupted.
              2. Performs a firmware update pre-check.
              3. Stages the firmware update with the corrupted component.
              4. Activates the firmware update.
              5. Verifies the firmware update.

              PASS Criteria: The test passes if the firmware activation is handled correctly despite one component failing to stage.
              FAIL Criteria: The test fails if the firmware activation is not handled correctly when one component fails to stage.

:Usage 1:		python ctam.py -w ..\workspace -t F56
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update Activation With Failed Component"

:Dependencies:

    .. code-block:: text 

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <Single>ShotPowerCycle>, <SingleShotPowerCycleCommand>, <SingleShotPowerCycleTimeOut>

        <package_info.json>               : Required - <Path>, <Package>, <JSON>, <CorruptComponentIdentifier>
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


class CTAMTestFullDeviceUpdateActivationWithFailedComponent(TestCase):
    """
    Verify If one component copying (staging) fails, activation is handled correctly.

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update Activation With Failed Component"
    test_id: str = "F56"
    score_weight: int = 10
    tags: List[str] = ["L3"]
    compliance_level: str = "L3"
    spec_versions: Union[str, List[str]] = ">= 1.0"

    def __init__(self, group: FWUpdateTestGroupN):
        """
        _summary_
        """
        super().__init__()
        self.group = group
        self.corrupted_component_id = None

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
        
        step0 = self.test_run().add_step(f"{self.__class__.__name__} run(), step0")  # type: ignore
        with step0.scope():
            self.corrupted_component_id = self.group.fw_update_ifc.ctam_get_component_to_be_corrupted(VendorProvidedBundle=False)
            if self.corrupted_component_id is None:
                step0.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : Corrupt Component Id Retrieval Failed"
                )
                result = False
                failure_reason = "Corrupt Component Id Retrieval Failed"
            else:
                step0.add_log(LogSeverity.INFO, f"{self.test_id} : Corrupt Component Id Retrieved")

        if result:
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
                status, msg, task_id, _ = self.group.fw_update_ifc.ctam_stage_fw(image_type="corrupt_component", 
                    corrupted_component_id=self.corrupted_component_id
                    )
                failure_reason = msg
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
                status, status_msg, _ = self.group.fw_update_ifc.ctam_activate_ac()
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
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify(image_type="corrupt_component", 
                                                                  corrupted_component_id=self.corrupted_component_id
                                                                  )
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
