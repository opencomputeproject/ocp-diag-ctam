"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Large Image Update
:Test ID:		F25
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case focuses on the scenario where we are trying from large image transfer is initiated for
				a firmware update. The expectation is for staging to fail when this is attempted. The image is provided by the vendor
				and it has a section in package_info.json

:Usage 1:		python ctam.py -w ..\workspace -t F25
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Negative Large Image Update"

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

class CTAMTestNegativeLargeImageUpdate(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Large Image Update"
    test_id: str = "F25"
    score_weight: int = 10
    tags: List[str] = ["Negative"]

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
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if self.group.fw_update_ifc.ctam_stage_fw(partial=1, image_type="large"):
                step1.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : FW Update Stage Initiation Failed as Expected",
                )
            else:
                step1.add_log(
                    LogSeverity.ERROR,
                    f"{self.test_id} : FW Update Staging Initiated - Unexpected",
                )
                result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

        # call super last to log result and score
        super().run()
        return self.result

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
