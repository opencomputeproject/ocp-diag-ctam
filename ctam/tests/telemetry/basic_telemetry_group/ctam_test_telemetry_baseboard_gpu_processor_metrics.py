"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the 
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Telemetry Baseboard GPU Processor Metrics
:Test ID:		T11
:Group Name:	telemetry
:Score Weight:	10

:Description:	Basic telemetry test case to discover & print the list of Baseboard GPU Processor Metrics

:Usage 1:		python ctam.py -w ..\workspace -t T11
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Telemetry Baseboard GPU Processor Metrics"

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
import json
class CTAMTestTelemetryBaseboardGPUProcessorMetrics(TestCase):
    
    test_name: str = "CTAM Test Telemetry Baseboard GPU Processor Metrics"
    test_id: str = "T11"
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
            if self.group.telemetry_ifc.ctam_baseboard_gpu_processor_metrics():
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Passed")
            else:
                step1.add_log(LogSeverity.FATAL, f"{self.test_id} : Failed")
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
