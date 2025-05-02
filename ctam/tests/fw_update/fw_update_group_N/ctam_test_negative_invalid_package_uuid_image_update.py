"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Invalid Package UUID Image Update
:Test ID:		F27
:Group Name:	fw_update
:Score Weight:	10

:Description:	
    This test case is a negative test. It makes a copy of the default FW image provided in package_info.json 
    and corrupts the UUID of the PLDM bundle. Then it attempts a firmware update with the fwpkg containing the corrupted UUID. 

:PASS Criteria:	
    - The firmware staging operation fails as expected due to the corrupted UUID.

:FAIL Criteria:	
    - The firmware staging operation succeeds unexpectedly with the corrupted UUID.

:Usage 1:		python ctam.py -w ..\workspace -t F27
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Negative Invalid Package UUID Image Update"

:Dependencies: 

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <MultiPartFormData>, <IsMultiPart>
                            
        <dut_info.json>                   : Required - <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>
                            
        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <HasSignature>, <SignatureStructBytes>
                                                      
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


class CTAMTestNegativeInvalidPackageUUIDImageUpdate(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Invalid Package UUID Image Update"
    test_id: str = "F27"
    score_weight: int = 10
    tags: List[str] = ["Negative", "L2"]
    compliance_level: str = "L2"

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
            status, failure_reason = self.group.fw_update_ifc.ctam_fw_update_precheck()
            if not status:
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )

        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
        with step2.scope():
            status, status_msg, task_id = self.group.fw_update_ifc.ctam_stage_fw(partial=1, 
                                                                                 image_type="invalid_pkg_uuid")
            failure_reason += " " + status_msg
            if status:
                step2.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : FW Update Stage Initiation Failed as Expected",
                )
            else:
                step2.add_log(
                    LogSeverity.ERROR,
                    f"{self.test_id} : FW Update Staging Initiated - Unexpected",
                )
                failure_reason += " " + "FW Update Staging Initiated - Unexpected"
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
            if self.group.fw_update_ifc.ctam_activate_ac(gpu_check=False, fwupd_hyst_wait=False):
                msg = f"{self.test_id} : Teardown : AC Cycle Passed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)  
            else:
                msg = f"{self.test_id} : Teardown : AC Cycle Failed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)

        # call super teardown last
        super().teardown()
