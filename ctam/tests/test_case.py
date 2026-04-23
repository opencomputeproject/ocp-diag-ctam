r"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

r"""
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
    r"""
    This is the super class for Test Cases. The test framework interacts with this superclass
    so it defines the abstract api' that all Test Cases must implement.

    :param ABC: Abstract super class
    :type ABC:
    :raises NotImplementedError: checks for required attributes in the derived test cases
    r"""

    # use class attributes so they are available to all subclassed TestCase objects
    _test_run: Optional[tv.TestRun] = None  # OCP TestRun
    _dut: Optional[CompToolDut]  # dut object
    total_compliance_score = 0  # accumulative
    max_compliance_score = 0
    total_execution_time = 0 # seconds
    test_ids_set = set()
    test_results_summary = {}
    @staticmethod
    def SetUpAssociations(testrun: tv.TestRun, dut: CompToolDut):
        r"""
        These class attributes are available to all subclasses

        :param testrun: OCP TestRun
        :type testrun: tv.TestRun
        :param dut: Comp Tool Dut interface
        :type dut: CompToolDut
        r"""
        TestCase._test_run = testrun
        TestCase._dut = dut
        TestCase.total_compliance_score = 0
        TestCase.max_compliance_score = 0
        TestCase.total_execution_time = 0

    def __init__(self):
        r"""
        Validates subclass has specified required attributes

        :raises NotImplementedError: missing attributes
        r"""
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
        r"""
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active test run
        :rtype: tv.TestRun
        r"""
        if TestCase._test_run:
            return TestCase._test_run
        else:
            raise NotImplementedError(f"need to call TestCase.SetUpAssociations")

    @staticmethod
    def dut() -> CompToolDut:
        r"""
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active dut
        :rtype: CompToolDut
        r"""
        if TestCase._dut:
            return TestCase._dut
        else:
            raise NotImplementedError(f"need to call TestCase.SetUpAssociations")

    @abstractmethod
    def setup(self):
        r"""
        Super class setup method that currently only logs point in test runner
        r"""
        step1 = self.test_run().add_step("TestCase.setup()...")
        with step1.scope():
            pass

    @abstractmethod
    def run(self) -> TestResult:
        r"""
        Actual test case run

        :return: Pass/Fail and test case score
        :rtype: Tuple[Status, int]
        r"""
        pass

    @abstractmethod
    def teardown(self):
        r"""
        Super class setup method that currently only logs point in test runner
        r"""
        step1 = self.test_run().add_step("TestCase.teardown()...")
        with step1.scope():
            if self.test_id not in self.test_ids_set:
                TestCase.max_compliance_score += self.score_weight
                self.test_ids_set.add(self.test_id)

            if self.test_id not in self.test_results_summary:
                self.test_results_summary[self.test_id] = set()
                
             # Add current score to the set (avoids duplicates)
            self.test_results_summary[self.test_id].add(self.score)

            # Recalculate total_compliance_score using the minimum score from each test_id set
            TestCase.total_compliance_score = sum(
                min(scores) for scores in self.test_results_summary.values()
            )