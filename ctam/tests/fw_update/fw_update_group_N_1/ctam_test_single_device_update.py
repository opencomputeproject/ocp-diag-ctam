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

                PASS Criteria:
                - All updatable devices are updated and activated successfully, one device at a time.
                
                FAIL Criteria:
                - Any device fails to update or activate.

:Usage 1:		python ctam.py -w ..\workspace -t F4
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Single Device Update"

:Dependencies: 

    .. code-block:: text

        <redfish_uri_config.json>         : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                                           Optional - <exclude_targets_list>, <HttpPushUriTargets>, <IsMultiPart>, <MultiPartFormData>
                            
        <dut_info.json>                   : Required - <CompareFirmwareInventoryCount>, <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                                           Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>

        <package_info.json>               : Required - <Path>, <Package>, <JSON>
                                           Optional - <HasSignature>, <SignatureStructBytes>
                                                        
        <redfish_response_messages.json>  : Required - <UpdateProgress_Message>
                                           Optional -  <LargeFWImageUpdate>
"""

from typing import Optional, List, Union
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
    tags: List[str] = ["L3", "Single_Device"]
    compliance_level: str = "L3"
    spec_versions: Union[str, List[str]] = ">= 1.0"

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
        failure_reason = ""

        if component_list := self.group.fw_update_ifc.ctam_get_updateable_devices_in_bundle():
            for device in component_list:
                result = True
                step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1_{device}")  # type: ignore
                with step1.scope():
                    if self.group.fw_update_ifc.ctam_selectpartiallist(count=1, specific_targets=[device]):
                        step1.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
                    else:
                        step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                        failure_reason += f"{self.test_id} : Single Device Selection Failed"
                        result = False
                
                step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2_{device}")  # type: ignore
                with step2.scope():
                    status, status_msg = self.group.fw_update_ifc.ctam_fw_update_precheck()
                    failure_reason += " " + status_msg
                    if not status:
                        step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
                    else:
                        step2.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update Not Required, going ahead nevertheless"
                        )

                step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3_{device}")  # type: ignore
                with step3.scope():
                    status, status_msg, task_id = self.group.fw_update_ifc.ctam_stage_fw(partial=1, specific_targets=[device])
                    failure_reason += " " + status_msg
                    if status:
                        step3.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
                    else:
                        step3.add_log(
                            LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                        )
                        failure_reason += " FW Update Stage Failed"
                        result = False

                if result:
                    step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4_{device}")  # type: ignore
                    with step4.scope():
                        status, status_msg = self.group.fw_update_ifc.ctam_activate_ac()
                        failure_reason += " " + status_msg
                        if status:
                            step4.add_log(
                                LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                            )
                        else:
                            step4.add_log(
                                LogSeverity.ERROR,
                                f"{self.test_id} : FW Update Activation Failed",
                            )
                            failure_reason += " FW Update Activation Failed"
                            result = False

                if result:
                    step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5_{device}")
                    with step5.scope():
                        status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify()
                        failure_reason += " " + status_msg
                        if status:
                            step5.add_log(
                                LogSeverity.INFO,
                                f"{self.test_id} : Update Verification Completed",
                            )
                        else:
                            step5.add_log(
                                LogSeverity.INFO, f"{self.test_id} : Update Verification Failed"
                            )
                            failure_reason += " Update Verification Failed"
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
                    failure_reason += " " + "Failed to update devices"
        else:
            step6 = self.test_run().add_step(f"{self.__class__.__name__} run(), step6")
            step6.add_log(LogSeverity.INFO, f"{self.test_id} : No updatable devices, exiting")
            failure_reason += "No updatable devices, exiting"
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
