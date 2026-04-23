r"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

r"""
from abc import ABC, abstractmethod
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


class TestGroup(ABC):
    r"""
    This is the super class for Test Groups. The test framework interacts with this superclass
    so it defines the abstract api' that all Test Groups must implement.

    :param ABC: Abstract super class
    :type ABC:
    :raises NotImplementedError: checks for required attributes in the derived test groups
    r"""

    _test_run: Optional[tv.TestRun] = None  # OCP TestRun
    _dut: Optional[CompToolDut]  # dut object

    @staticmethod
    def SetUpAssociations(testrun: tv.TestRun, dut: CompToolDut):
        r"""
        These class attributes are available to all subclasses

        :param testrun: OCP TestRun
        :type testrun: tv.TestRun
        :param dut: Comp Tool Dut interface
        :type dut: CompToolDut
        r"""
        TestGroup._test_run = testrun
        TestGroup._dut = dut

    def __init__(self):
        r"""
        Validates subclass has specified required attributes

        :raises NotImplementedError: missing attributes
        r"""
        self.test_list = []

        required_attrs = [
            "tags",
            "group_id",
            # "exclude_tags",
        ]

        for attr in required_attrs:
            if not hasattr(self, attr):
                raise NotImplementedError(
                    f"Classes derived from TestGroup, {self.__class__.__name__},must define a '{attr}' attribute."
                )

    @staticmethod
    def test_run() -> tv.TestRun:
        r"""
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active test run
        :rtype: tv.TestRun
        r"""
        if TestGroup._test_run:
            return TestGroup._test_run
        else:
            raise NotImplementedError(f"need to call TestGroup.SetUpAssociations")

    @staticmethod
    def dut() -> CompToolDut:
        r"""
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active dut
        :rtype: CompToolDut
        r"""
        if TestGroup._dut:
            return TestGroup._dut
        else:
            raise NotImplementedError(f"need to call TestGroup.SetUpAssociations")

    @abstractmethod
    def setup(self):
        r"""
        Super class setup method that currently only logs point in test runner
        r"""
        step1 = self.test_run().add_step("TestGroup.setup()...")
        with step1.scope():
            pass

    @abstractmethod
    def teardown(self):
        r"""
        Super class setup method that currently only logs point in test runner
        r"""
        step1 = self.test_run().add_step("TestGroup.teardown()...")
        with step1.scope():
            pass
