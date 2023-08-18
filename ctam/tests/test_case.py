"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, List
import ocptv.output as tv
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from interfaces.comptool_dut import CompToolDut


class TestCase(ABC):
    """
    This is the super class for Test Cases. The test framework interacts with this superclass
    so it defines the abstract api' that all Test Cases must implement.

    :param ABC: Abstract super class
    :type ABC:
    :raises NotImplementedError: checks for required attributes in the derived test cases
    """

    # use class attributes so they are available to all subclassed TestCase objects
    _test_run: Optional[tv.TestRun] = None  # OCP TestRun
    _dut: Optional[CompToolDut]  # dut object
    total_compliance_score = 0  # accumulative
    max_compliance_score = 0

    @staticmethod
    def SetUpAssociations(testrun: tv.TestRun, dut: CompToolDut):
        """
        These class attributes are available to all subclasses

        :param testrun: OCP TestRun
        :type testrun: tv.TestRun
        :param dut: Comp Tool Dut interface
        :type dut: CompToolDut
        """
        TestCase._test_run = testrun
        TestCase._dut = dut
        TestCase.total_compliance_score = 0
        TestCase.max_compliance_score = 0

    def __init__(self):
        """
        Validates subclass has specified required attributes

        :raises NotImplementedError: missing attributes
        """
        required_attrs = [
            "test_id",
            "test_name",
            "score_weight",
            "tags",
            # "exclude_tags",
        ]

        self.result = TestResult.FAIL
        self.score = 0

        for attr in required_attrs:
            if not hasattr(self, attr):
                raise NotImplementedError(
                    f"Classes derived from TestCase, {self.__class__.__name__},must define a '{attr}' attribute."
                )

    @staticmethod
    def test_run() -> tv.TestRun:
        """
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active test run
        :rtype: tv.TestRun
        """
        if TestCase._test_run:
            return TestCase._test_run
        else:
            raise NotImplementedError(f"need to call TestCase.SetUpAssociations")

    @staticmethod
    def dut() -> CompToolDut:
        """
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active dut
        :rtype: CompToolDut
        """
        if TestCase._dut:
            return TestCase._dut
        else:
            raise NotImplementedError(f"need to call TestCase.SetUpAssociations")

    @abstractmethod
    def setup(self):
        """
        Super class setup method that currently only logs point in test runner
        """
        step1 = self.test_run().add_step("TestCase.setup()...")
        with step1.scope():
            pass

    @abstractmethod
    def run(self) -> TestResult:
        """
        Actual test case run

        :return: Pass/Fail and test case score
        :rtype: Tuple[Status, int]
        """
        pass

    @abstractmethod
    def teardown(self):
        """
        Super class setup method that currently only logs point in test runner
        """
        step1 = self.test_run().add_step("TestCase.teardown()...")
        with step1.scope():
            if self.result == TestResult.PASS:
                TestCase.total_compliance_score += self.score
            TestCase.max_compliance_score += self.score_weight
