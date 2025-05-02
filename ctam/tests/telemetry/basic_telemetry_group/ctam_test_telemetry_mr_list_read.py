"""
Copyright (c) Microsoft Corporation
This source code is licensed under the 
MIT license found in the LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Telemetry MR List Read
:Test ID:		T2
:Group Name:	Telemetry
:Score Weight:	10

:Description:	This test case discovers and prints the list of all Metric Report Definitions (MRDs)
                available on the Device Under Test (DUT). It ensures that the telemetry interface
                can retrieve the list of MRDs correctly.

:PASS Criteria: The test will pass if the telemetry interface successfully retrieves and prints
                the list of all MRDs.

:FAIL Criteria: The test will fail if the telemetry interface returns an empty list or encounters
                any errors while retrieving the MRDs.

:Usage 1:		python ctam.py -w ..\workspace -t T2
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Telemetry MR List Read"


:Dependencies: None

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
from tests.telemetry.basic_telemetry_group.basic_telemetry_group import (
    BasicTelemetryTestGroup
)

class CTAMTestTelemetryMRListRead(TestCase):
    
    test_name: str = "CTAM Test Telemetry MR List Read"
    test_id: str = "T2"
    score_weight: int = 10
    tags: List[str] = ["L3"]
    compliance_level: str = "L3"

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
        failure_reason = ""
        result = True
        step1 = self.test_run().add_step((f"{self.__class__.__name__} run(), step1"))  # type: ignore
        with step1.scope():
            if self.group.telemetry_ifc.ctam_get_all_metric_reports_uri() == []:
                step1.add_log(LogSeverity.FATAL, f"{self.test_id} : All metric reports URI empty")
                failure_reason += "All metric reports URI empty"
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
