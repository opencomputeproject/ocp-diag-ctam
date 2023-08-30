"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update with Self-test Verification
:Test ID:		F67
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case does a full firmware update first, and then verifies if self-test reports any failures.
:Usage 1:		python ctam.py -w ..\workspace -T F67
:Usage 2:		python ctam.py -w ..\workspace -T "CTAM Test Full Device Update with Self-test Verification"

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
from tests.fw_update.fw_update_group_N_1.ctam_test_full_device_update import (
    CTAMTestFullDeviceUpdate,
)
from tests.health_check.basic_health_check_group.ctam_verify_self_test_report import (
    CTAMVerifySelfTestReport,
)
from interfaces.health_check_ifc import (
    HealthCheckIfc
)


class CTAMTestFullDeviceUpdateWithSelfTest(TestCase):
    """
    Verify if self-test reports any failure after a full firmware update

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update with Self-test Verification"
    test_id: str = "F67"
    score_weight: int = 10
    tags: List[str] = []

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
        fw_update_score_percentage = 0
        self_test_score_percentage = 0
        
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            FwUpdateTest = CTAMTestFullDeviceUpdate(self.group)
            if FwUpdateTest.run() == TestResult.PASS:
                fw_update_score_percentage = float(FwUpdateTest.score / FwUpdateTest.score_weight)
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update")
            else:
                step1.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : FW Update Failed"
                )
                result = False

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                self.group.health_check_ifc = HealthCheckIfc.get_instance()
                SelfTest = CTAMVerifySelfTestReport(self.group)
                if SelfTest.run() == TestResult.PASS:
                    self_test_score_percentage = float(SelfTest.score / SelfTest.score_weight)
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : Post FW Update Self-test")
                else:
                    step2.add_log(
                        LogSeverity.ERROR, f"{self.test_id} : Post FW Update Self-test Failed"
                    )
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = (fw_update_score_percentage * 0.5 + self_test_score_percentage * 0.5) * self.score_weight

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
