r"""
Copyright (c) AMD
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update Precheck Only
:Test ID:		F3
:Group Name:	fw_update
:Score Weight:	0
:Description:	This test case verifies the precheck flow and expects SoftwareInventory to match against
                the new firmware

:PASS Criteria: The test passes if the SoftwareInventory matches against new firmware

:FAIL Criteria: The test fails if the SoftwareInventory does not match against the new firmware

:Usage 1:		python ctam.py -w ..\workspace -t F3
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update Precheck Only"

:Dependencies:

    .. code-block:: text 

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>

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


class CTAMTestFullDeviceUpdatePrecheckOnly(TestCase):
    """
    Verify that full device SoftwareInventory matches against new firmware

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update Precheck Only"
    test_id: str = "F3"
    score_weight: int = 0
    tags: List[str] = ["L3"]
    compliance_level: str = "L3"

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

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck()
            failure_reason = status_msg
            if status:
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Software Inventory matches against new firmware")
            else:
                step1.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : Software Inventory does not match against the new firmware"
                    )
                failure_reason += " " + "Precheck verification failed"
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
