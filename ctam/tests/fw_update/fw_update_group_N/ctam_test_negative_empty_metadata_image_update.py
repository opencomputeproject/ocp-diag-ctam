"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Empty Metadata Image Update
:Test ID:		F26
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case is a Negative Test. It'll make a copy of the default FW image provided in package_info.json 
                and clear metadat of any component in the PLDM bundle. Then it'll attempt firmware update with the fwpkg containing corrupted UUID. 

:Usage 1:		python ctam.py -w ..\workspace -t F26
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Negative Empty Metadata Image Update"

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


class CTAMTestNegativeEmptyMetadataImageUpdate(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Empty Metadata Image Update"
    test_id: str = "F26"
    score_weight: int = 10
    tags: List[str] = ["Negative"]

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
            corrupted_component_id  = self.group.fw_update_ifc.ctam_get_component_to_be_corrupted()
            corrupted_component_list = self.group.fw_update_ifc.ctam_get_component_list(component_id=corrupted_component_id)
            step1.add_log(LogSeverity.INFO, f"{self.test_id} : Selected component to corrupt -> {corrupted_component_id}")
        
        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2_{corrupted_component_list[0]}")  # type: ignore
        with step2.scope():
            if self.group.fw_update_ifc.ctam_selectpartiallist(count=1, specific_targets=[corrupted_component_list[0]]):
                step2.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
            else:
                step2.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                result = False

        step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3_{corrupted_component_list[0]}")  # type: ignore
        with step3.scope():
            if self.group.fw_update_ifc.ctam_stage_fw(
                partial=1, image_type="empty_metadata", corrupted_component_id=corrupted_component_id
            ):
                step3.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : FW Update Stage Initiation Failed as Expected",
                )
            else:
                step3.add_log(
                    LogSeverity.ERROR,
                    f"{self.test_id} : FW Update Staging Initiated - Unexpected",
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
            if self.group.fw_update_ifc.ctam_pushtargets():
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Push URI Targets Reset")
            else:
                step1.add_log(LogSeverity.WARNING, f"{self.test_id} : Push URI Targets Reset - Failed")

        # call super teardown last
        super().teardown()
