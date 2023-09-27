"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Single Device Update
:Test ID:		F4
:Group Name:	fw_update
:Score Weight:	10

:Description:	Basic test case of Single Device firmware update. All updatable devices are updated and activated, one device at a time.
                Any device fail would lead to test case fail. 

:Usage 1:		python ctam.py -w ..\workspace -t F4
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Single Device Update"

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

class CTAMTestSingleDeviceUpdate(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Single Device Update"
    test_id: str = "F4"
    score_weight: int = 10
    tags: List[str] = ["Single"]

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
        updated_devices = []
        failed_devices = []

        if component_list := self.group.fw_update_ifc.ctam_build_updatable_device_list():
            for device in component_list:
                result = True
                step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1_{device}")  # type: ignore
                with step1.scope():
                    if self.group.fw_update_ifc.ctam_selectpartiallist(count=1, specific_targets=[device]):
                        step1.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
                    else:
                        step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                        result = False
                
                step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2_{device}")  # type: ignore
                with step2.scope():
                    if not self.group.fw_update_ifc.ctam_fw_update_precheck():
                        step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                    else:
                        step2.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update Not Required, going ahead nevertheless"
                        )

                step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3_{device}")  # type: ignore
                with step3.scope():
                    if self.group.fw_update_ifc.ctam_stage_fw(partial=1):
                        step3.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
                    else:
                        step3.add_log(
                            LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                        )
                        result = False

                if result:
                    step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4_{device}")  # type: ignore
                    with step4.scope():
                        if self.group.fw_update_ifc.ctam_activate_ac():
                            step4.add_log(
                                LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                            )
                        else:
                            step4.add_log(
                                LogSeverity.ERROR,
                                f"{self.test_id} : FW Update Activation Failed",
                            )
                            result = False

                if result:
                    step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5_{device}")
                    with step5.scope():
                        if self.group.fw_update_ifc.ctam_fw_update_verify():
                            step5.add_log(
                                LogSeverity.INFO,
                                f"{self.test_id} : Update Verification Completed",
                            )
                        else:
                            step5.add_log(
                                LogSeverity.INFO, f"{self.test_id} : Update Verification Failed"
                            )
                            result = False
                
                if result:
                    updated_devices.append(device)
                else:
                    failed_devices.append(device)
            #After completing all devices
            step6 = self.test_run().add_step(f"{self.__class__.__name__} run(), step6")
            with step6.scope():
                step6.add_log(LogSeverity.INFO, f"{updated_devices} : Successfully updated devices")
                step6.add_log(LogSeverity.INFO, f"{failed_devices} : Failed to update devices")
                if len(failed_devices) !=0:
                    result = False
        else:
            step6.add_log(LogSeverity.INFO, f"{self.test_id} : No updatable devices, exiting")
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
