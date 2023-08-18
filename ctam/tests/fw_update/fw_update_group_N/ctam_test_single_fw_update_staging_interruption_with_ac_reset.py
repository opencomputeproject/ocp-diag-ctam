"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Single FW update staging interruption with AC reset
:Test ID:		F62
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case focuses on the scenario where an image transfer is initiated for a firmware update.
				The objective is to ensure that after the image transfer is completed, the system proceeds without waiting
				for its full completion. Instead, it should immediately move on to resetting the activation flow for the full
				firmware update process.
:Usage 1:		python ctam.py -w ..\workspace -t F62
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Single FW update staging interruption with AC reset"

"""
import ast
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

class CTAMTestSingleFWUpdateStagingInterruptionWithACReset(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Single FW update staging interruption with AC reset"
    test_id: str = "F62"
    score_weight: int = 10
    tags: List[str] = []

    def __init__(self, group: FWUpdateTestGroupN):
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

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if self.group.fw_update_ifc.ctam_selectpartiallist(
                count=1,
                specific_targets=ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{specific_targets}", component_type="GPU"))
            ):
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
            else:
                step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                result = False

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                if not self.group.fw_update_ifc.ctam_fw_update_precheck(image_type="backup"):
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                else:
                    step2.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Not Required, going ahead nevertheless")
                        
        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                if self.group.fw_update_ifc.ctam_stage_fw(partial=1, wait_for_stage_completion=False, image_type="backup"):
                    step3.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staging Initiated")
                else:
                    step3.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Initiation Failed")
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")  # type: ignore
            with step4.scope():
                if self.group.fw_update_ifc.ctam_activate_ac():
                    step4.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Activate, interrupting staging flow with reset")
                else:
                    step4.add_log(LogSeverity.ERROR, f"{self.test_id} : FW Update Activation Failed")
                    result = False

        if result:
            step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5")
            with step5.scope():
                if self.group.fw_update_ifc.ctam_fw_update_verify(image_type="negate"):
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