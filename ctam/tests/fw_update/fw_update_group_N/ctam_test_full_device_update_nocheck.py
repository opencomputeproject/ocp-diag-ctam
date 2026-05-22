r"""
Copyright (c) AMD
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update No Check
:Test ID:		F5
:Group Name:	fw_update
:Score Weight:	50
:Spec Versions: ">= 1.0"
:Description:	This test case verifies that the firmware staging is successful followed by activate.
                The test can fail with stage failure. No precheck and postcheck is performed in this test case.

:PASS Criteria: The test passes if the staging is successful.

:FAIL Criteria: The test fails if staging is unsuccessful.

:Usage 1:		python ctam.py -w ..\workspace -t F5
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update No Check"

:Dependencies:

    .. code-block:: text 

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
        <dut_info.json>                   : Required - <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
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


class CTAMTestFullDeviceUpdateNoCheck(TestCase):
    """
    Verify that full device update staging is successful followed by activation, no precheck and postcheck is performed in this test case.

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update No Check"
    test_id: str = "F5"
    score_weight: int = 50
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

        step1= self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            status, status_msg, task_id, _ = self.group.fw_update_ifc.ctam_stage_fw()
            failure_reason = status_msg
            if status:
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
            else:
                step1.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : FW Update Staging failed"
                )
                failure_reason = "FW Update Staging failed"
                result = False

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                status, status_msg, _ = self.group.fw_update_ifc.ctam_activate_ac()
                failure_reason = status_msg
                if status:
                    step2.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                    )
                else:
                    step2.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Activation Failed",
                    )
                    failure_reason = "FW Update Activation Failed"
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
