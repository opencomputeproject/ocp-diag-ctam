r"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test AC Cycles In Loop
:Test ID:		H100
:Group Name:	health_check
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description:	AC Cycle is essential for activation flow of firmware update and many other flows.
                This test runs AC cycles in a loop to test platform stability. This is a prerequisite
                to many other test cases that need the activation flow.

                PASS Criteria: The test passes if all AC cycles complete successfully without errors.
                FAIL Criteria: The test fails if any AC cycle encounters an error.

:Usage 1:		python ctam.py -w ..\workspace -t H100
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test AC Cycles In Loop"
 
:Dependencies: 

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <GPUCheckURI>
                                           Optional - None
                            
        <dut_info.json>                   : Required - <FwActivationTimeMax>, <PowerOnWaitTime>, <PowerOffCommand>, <PowerOnCommand>, <PowerOffWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>, <SingleShotPowerCycleTimeOut>
"""

from typing import List, Union
from tests.test_case import TestCase
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.health_check.long_health_check_group.long_health_check_test_group import LongHealthCheckTestGroup

class CTAMTestAcCyclesInLoop(TestCase):
    """
        :param gpu_bb acc:		Accelerator Object
        :param Logger logger:	Logger Object

        :returns:				Test result [Pass/Fail], Test score
        """
    test_name: str = "CTAM Test AC Cycles In Loop"
    test_id: str = 'H100'
    score_weight:int = 10
    tags: List[str] = ["L3"]
    compliance_level: str = "L3"
    spec_versions: Union[str, List[str]] = ">= 1.0"

    def __init__(self, group: LongHealthCheckTestGroup):
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
        failure_reason = ""
        loops = 1

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  
        with step1.scope():
            for i in range(loops):
                if result:
                    if self.group.health_check_ifc.ctam_activate_ac():
                        msg = f"{self.test_id} : AC Cycle Passed Loop {i}"
                        self.test_run().add_log(LogSeverity.DEBUG, msg)  
                    else:
                        msg = f"{self.test_id} : AC Cycle Failed Loop {i}"
                        self.test_run().add_log(LogSeverity.DEBUG, msg)
                        failure_reason += f"AC Cycle Failed Loop {i}"
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