"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the 
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Telemetry MR Read
:Test ID:		T4
:Group Name:	telemetry
:Score Weight:	10

:Description:	Basic test case to discover list of all metric reports and  
:Usage 1:		python ctam.py -w ..\workspace -t T4
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Telemetry MR Read"

"""
from typing import Optional, List
from tests.test_case import TestCase
from prettytable import PrettyTable
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.telemetry.basic_telemetry_group.basic_telemetry_group import (
    BasicTelemetryTestGroup
)

class CTAMTestTelemetryMRRead(TestCase):
    
    test_name: str = "CTAM Test Telemetry MR Read"
    test_id: str = "T4"
    score_weight: int = 10
    tags: List[str] = []

    def __init__(self, group: BasicTelemetryTestGroup):
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
        step1 = self.test_run().add_step((f"{self.__class__.__name__} run(), step1"))  # type: ignore
        with step1.scope():
            self.test_run().add_log(LogSeverity.INFO, 'The test id is {}'.format(self.test_id))
            res = self.group.telemetry_ifc.ctam_get_all_metric_reports()

        step2 = self.test_run().add_step((f"{self.__class__.__name__} run(), step2"))  # type: ignore
        with step2.scope():
            if res != "":
                msg = '"Extraction Complete", extra={"additional_detail": {"Matric Values": res}}'
                self.test_run().add_log(LogSeverity.INFO, msg)
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Could not extract the Metric Reports. Proceed with manual debug")
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