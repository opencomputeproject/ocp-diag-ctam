"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Install Same Image Two Times
:Test ID:		F16
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case involves performing a full device update including verification
                followed by repeating the update process again.

:Usage 1:		python ctam.py -w ..\workspace -t F16
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Install Same Image Two Times"


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
from tests.fw_update.fw_update_group_N_1._fw_update_group_N_1 import (
    FWUpdateTestGroupNMinus1,
)


class CTAMTestInstallSameImageTwoTimes(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Install Same Image Two Times"
    test_id: str = "F16"
    score_weight: int = 10
    tags: List[str] = ["L1"]
    compliance_level: str = "L1"

    def __init__(self, group: FWUpdateTestGroupNMinus1):
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
        times = 2

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if not self.group.fw_update_ifc.ctam_fw_update_precheck():
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )

        if result:
            for i in range(times):
                step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
                with step2.scope():
                    status, status_msg, task_id = self.group.fw_update_ifc.ctam_stage_fw()
                    if status:
                        step2.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update Staged"
                        )
                    else:
                        step2.add_log(
                            LogSeverity.FATAL,
                            f"{self.test_id} : FW Update Staged Failed",
                        )
                        result = False

        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                if self.group.fw_update_ifc.ctam_activate_ac():
                    step3.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                    )
                else:
                    step3.add_log(
                        LogSeverity.FATAL,
                        f"{self.test_id} : FW Update Activation Failed",
                    )
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")
            with step4.scope():
                if self.group.fw_update_ifc.ctam_fw_update_verify():
                    step4.add_log(
                        LogSeverity.INFO,
                        f"{self.test_id} : Update Verification Completed",
                    )
                else:
                    step4.add_log(
                        LogSeverity.FATAL,
                        f"{self.test_id} : Update Verification Failed",
                    )
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
