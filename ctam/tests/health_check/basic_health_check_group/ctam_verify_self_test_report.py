"""
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Verify Self-Test Report
:Test ID:		H50
:Group Name:	health_check
:Score Weight:	10

:Description:	This test case verifies if self-test reports any failures.
:Usage 1:		python ctam.py -w ..\workspace -T H50
:Usage 2:		python ctam.py -w ..\workspace -T "CTAM Test Verify Self-Test Report"

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
from tests.health_check.basic_health_check_group.basic_health_check_test_group import (
    BasicHealthCheckTestGroup,
)


class CTAMVerifySelfTestReport(TestCase):
    """
    Verify if self-test reports any failures

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Verify Self-Test Report"
    test_id: str = "H50"
    score_weight: int = 10
    tags: List[str] = ["HCheck"]

    def __init__(self, group: BasicHealthCheckTestGroup):
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
            if self.group.health_check_ifc.trigger_self_test_dump_collection():
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Self test dump collection is triggered")
            else:
                step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Self Test Dump Collection Failed")
                result = False

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} step2")  # type: ignore
            with step2.scope():
                if self.group.health_check_ifc.download_self_test_dump():
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : Self Test Dump Download")
                else:
                    step2.add_log(LogSeverity.ERROR, f"{self.test_id} : Self Test Dump Download Failed")
                    result = False
                    
        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                if self.group.health_check_ifc.check_self_test_report():
                    step3.add_log(LogSeverity.INFO, f"{self.test_id} : Self Test Report Failure Check")
                else:
                    step3.add_log(LogSeverity.ERROR, f"{self.test_id} : Self Test Report Failure Check Failed")
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
