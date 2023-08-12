"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

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


class VerifyExampleTest(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_id: List[str] = ["H410", "mine"]
    score_weight: int = 10
    tags: List[str] = ["HealthCheck", 'NotCheck']
    # exclude_tags: List[str] = ["NotCheck"]

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
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")
        with step1.scope():
            pass

        step2 = self.test_run().add_step(f"{self.__class__.__name__} step2")
        with step2.scope():
            msg = f"Example Debug message in {self.__class__.__name__}"
            self.test_run().add_log(severity=LogSeverity.DEBUG, message=msg)

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS
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
