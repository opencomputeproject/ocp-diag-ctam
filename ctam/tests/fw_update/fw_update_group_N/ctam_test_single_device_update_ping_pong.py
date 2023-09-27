"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Single Device Update Ping Pong
:Test ID:		F89
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case entails performing firmware updates in a loop, one device at a time but using different versions
				for each update.

:Usage 1:		python ctam.py -w ..\workspace -t F89
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Single Device Update Ping Pong"

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
from tests.fw_update.fw_update_group_N._fw_update_group_N import (
    FWUpdateTestGroupN,
)

class CTAMTestSingleDeviceUpdatePingPong(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Single Device Update Ping Pong"
    test_id: str = "F89"
    score_weight: int = 10
    tags: List[str] = ["Single"]

    def __init__(self, group: FWUpdateTestGroupN):
        """
        _summary_
        """
        super().__init__()
        self.group = group
        self.specific_targets = []
        self.excluded_targets = []

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
        loops = 2

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if self.group.fw_update_ifc.ctam_selectpartiallist(
                count=1,
                excluded_targets=self.excluded_targets,
                specific_targets=self.specific_targets
            ):
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
            else:
                step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                result = False

        for i in range(loops):
            image_t = "default" if i % 2 == 0 else "backup"

            if result:
                step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2_{i}")  # type: ignore
                with step2.scope():
                    if not self.group.fw_update_ifc.ctam_fw_update_precheck(image_type=image_t):
                        step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                    else:
                        step2.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Not Required, going ahead nevertheless")
                        
            if result:
                step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3_{i}")  # type: ignore
                with step3.scope():
                    if self.group.fw_update_ifc.ctam_stage_fw(partial=1, image_type=image_t):
                        step3.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
                    else:
                        step3.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed")
                        result = False

            if result:
                step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4_{i}")  # type: ignore
                with step4.scope():
                    if self.group.fw_update_ifc.ctam_activate_ac():
                        step4.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Activate")
                    else:
                        step4.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Activation Failed")
                        result = False

            if result:
                step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5_{i}")
                with step5.scope():
                    if self.group.fw_update_ifc.ctam_fw_update_verify(image_type=image_t):
                        step5.add_log(LogSeverity.INFO, f"{self.test_id} : Update Verification Completed")
                    else:
                        step5.add_log(LogSeverity.INFO, f"{self.test_id} : Update Verification Failed")
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