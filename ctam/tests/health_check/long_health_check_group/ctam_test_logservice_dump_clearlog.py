"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the 
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test LogService Dump Clear
:Test ID:		H96
:Group Name:	health_check
:Score Weight:	10

:Description:	Basic test case to clear all entries of all instances of LogService Dumps
				
:Usage 1:		python ctam.py -w ..\workspace -t H96
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test LogService Dump Clear"

"""
from typing import List
from tests.test_case import TestCase
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.health_check.basic_health_check_group.basic_health_check_test_group import BasicHealthCheckTestGroup

class CTAMTestLogserviceDumpClearlog(TestCase):

    """
        :param gpu_bb acc:		Accelerator Object
        :param Logger logger:	Logger Object

        :returns:				Test result [Pass/Fail], Test score
        """

    test_name: str = "CTAM Test LogService Dump Clear"
    test_id: str = 'H96'
    score_weight:int = 10
    tags: List[str] = []

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
        super().setup()
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  setup()...")
        with step1.scope():
            pass
        
    def run(self) -> TestResult:
        """
        actual test verification
        """
        result = True

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  
        with step1.scope():
            if result:= self.group.health_check_ifc.ctam_clear_log_dump(): 
                msg = f"{self.test_id} : Test Passed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)  
            else:
                msg = f"{self.test_id} : Test Failed"
                self.test_run().add_log(LogSeverity.DEBUG, msg) 
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