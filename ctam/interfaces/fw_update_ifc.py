"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
import os
import json
import time
import random
from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc
from ocptv.output import LogSeverity
from utils.json_utils import *


class FWUpdateIfc(FunctionalIfc):
    """
    API's related to general health check of the dut
    """

    _instance: Optional["FWUpdateIfc"] = None

    def __new__(cls, *args, **kwargs):
        """
        ensure only 1 instance can be created

        :return: instance
        :rtype: FWUpdateIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = super(FWUpdateIfc, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.PostInstallVersionDetails = {}
        self.PreInstallVersionDetails = {}

    @classmethod
    def get_instance(cls, *args, **kwargs):
        """
        if there is an existing instance, return it, otherwise create the singleton instance and return it

        :return: instance
        :rtype: FWUpdateIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = cls(*args, **kwargs)
        return cls._instance

    def ctam_get_fw_version(self, PostInstall=0):
        """
        :Description:				Get Firmware Version
        :param PostInstall:		Get Version after install the Firmware or before installing

        :returns:				    None
        """
        
        MyName = __name__ + "." + self.ctam_get_fw_version.__qualname__
        JSONData = self.ctam_getfi(expanded=1)
        if PostInstall:
            self.PostInstallDetails = JSONData["Members"]
            jsonmultihunt(
                self.PostInstallDetails, "Id", "Version", self.PostInstallVersionDetails
            )
        else:
            self.PreInstallDetails = JSONData["Members"]
            jsonmultihunt(
                self.PreInstallDetails, "Id", "Version", self.PreInstallVersionDetails
            )
        msg = f"Post install version details are {self.PostInstallVersionDetails} and Pre install details are {self.PreInstallVersionDetails}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)

    def ctam_fw_update_precheck(self, image_type="default"):
        """
        :Description:				Check Firmware before installation
        :param image_type:		Type of the Firmware image

        :returns:				    VersionsDifferent
        :rtype: 					Bool
        """
        MyName = __name__ + "." + self.ctam_fw_update_precheck.__qualname__
        VersionsDifferent = True
        self.included_targets = []

        PLDMPkgJson_file = self.get_PLDMPkgJson_file(image_type=image_type)

        with open(PLDMPkgJson_file, "r") as f:
            PLDMPkgJson = json.load(f)
        self.ctam_get_fw_version(PostInstall=0)
        for element in self.PreInstallDetails:
            if str(element["Updateable"]) == "True" and element["SoftwareId"] != "":
                Package_Version = jsonhunt(
                    PLDMPkgJson,
                    "ComponentIdentifier",
                    str(hex(int(element["SoftwareId"], 16))),
                    "ComponentVersionString",
                )
                if Package_Version is None:
                        msg = "{} : {} : {} : Not in the PLDM bundle".format(
                            element["Id"],
                            element["SoftwareId"],
                            element["Version"]
                        )
                        self.test_run().add_log(LogSeverity.DEBUG, msg)
                elif element["Version"] != Package_Version and (
                    self.included_targets == []
                    or element["@odata.id"] in self.included_targets
                ):
                    VersionsDifferent = False
                    msg = f"Pre Install Details: {element['Id']} : {element['SoftwareId']} : {element['Version']} : Update Capable to {Package_Version}"
                    self.test_run().add_log(LogSeverity.DEBUG, msg)

                elif (
                    self.included_targets == []
                    or element["@odata.id"] in self.included_targets
                ):
                    msg = f"Pre Install Details: {element['Id']} : {element['SoftwareId']} : {element['Version']} : Update Not Needed."
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
        return VersionsDifferent

    def ctam_stage_fw(
        self, partial=0, image_type="default", wait_for_stage_completion=True,
        corrupted_component_id=None, corrupted_component_list=[],
        check_time=False, return_task_id=False
    ):
        """
        :Description:							Stage Firmware
        :param partial:							Partial
        :param image_type:						Type of Firmware Image
        :param wait_for_stage_completion:		Wait for stage completion
        :param corrupted_component_id:          ComponentIdentifier of the component image to be corrupted for specific negative tests
        :param corrupted_component_list:        List component names (Ids) which are corrupted
        :param check_time:                      Check the staging time does not exceed maximum time per spec
        :param return_task_id:                  Return the task id of the FW update staging task.

        :returns:				    			StageFWOOB_Status or StageFWOOB_Status, return_task_id 
        :rtype: 								Bool or (Bool, Bool)
        """
        MyName = __name__ + "." + self.ctam_stage_fw.__qualname__
        StartTime = time.time()

        if partial == 0:
            self.ctam_pushtargets()

        JSONFWFilePayload = self.get_JSONFWFilePayload_file(image_type=image_type, corrupted_component_id=corrupted_component_id)

        if self.dut().is_debug_mode():
            print(JSONFWFilePayload)
        uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )
        if self.dut().is_debug_mode():
            self.test_run().add_log(LogSeverity.DEBUG, f"URI : {uri}")
        
        JSONData = self.RedFishFWUpdate(JSONFWFilePayload, uri)
        StagingStartTime = time.time()

        if self.dut().is_debug_mode():
            self.test_run().add_log(LogSeverity.DEBUG, f"{MyName}  {JSONData}")

        FwUpdTaskID = JSONData.get("Id")
        if "error" not in JSONData:
            if wait_for_stage_completion:
                TaskID = JSONData["@odata.id"]

                if self.dut().is_debug_mode():
                    self.test_run().add_log(LogSeverity.DEBUG, TaskID)
                DeployTime = time.time()
                v1_str = self.dut().uri_builder.format_uri(
                    redfish_str="{GPUMC}" + "{}".format(TaskID), component_type="GPU"
                )
                response = self.dut().run_redfish_command(uri=v1_str)
                JSONData = response.dict

                FwStagingTimeMax = self.dut().dut_config["FwStagingTimeMax"]["value"]
                while JSONData["TaskState"] == "Running" \
                        and (not check_time or (check_time and (time.time() - StagingStartTime) <= FwStagingTimeMax)):
                    response = self.dut().run_redfish_command(uri=v1_str)
                    JSONData = response.dict
                    if self.dut().is_debug_mode():
                        print(
                            f"GPU FW Update Percentage_completion = {JSONData['PercentComplete']}"
                        )
                    msg = f"GPU FW Update Percentage_completion = {JSONData['PercentComplete']}"
                    self.test_run().add_log(LogSeverity.DEBUG, msg)

                    time.sleep(30)
                EndTime = time.time()
                if JSONData["TaskState"] == "Completed":
                    StageFWOOB_Status = True
                else:
                    StageFWOOB_Status = False
                    
                if check_time and (EndTime - StagingStartTime) > FwStagingTimeMax:
                    msg = f"FW copy operation exceeded the maximum time {FwStagingTimeMax} seconds."
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
                    StageFWOOB_Status = False

                msg = "{0}: GPU Deployment Time: {1} GPU Update Time: {2} \n Redfish Outcome: {3}".format(
                    MyName,
                    DeployTime - StartTime,
                    EndTime - StartTime,
                    json.dumps(JSONData, indent=4),
                )
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                if image_type in ["invalid_sign", "unsigned", "corrupt", "invalid_uuid", "empty_metadata", "empty_component"]:
                    if "TaskState" in JSONData and "TaskStatus" in JSONData:
                        if (
                            JSONData["TaskState"] == "Exception"
                            and JSONData["TaskStatus"] == "Critical"
                        ):
                            msg = "Staging failed with as expected TaskState = {}, TaskStatus = {}".format(
                                JSONData["TaskState"], JSONData["TaskStatus"]
                            )
                            self.test_run().add_log(LogSeverity.DEBUG, msg)
                            if image_type == "empty_component":
                                StageFWOOB_Status = self.ctam_check_component_fwupd_failure(
                                    task_message_list=JSONData["Messages"],
                                    corrupted_component_id=corrupted_component_id
                                    )
                            else:
                                StageFWOOB_Status = True
                        else:
                            msg = "Staging failed but with an unexpected TaskState = {}, TaskStatus = {}".format(
                                JSONData["TaskState"], JSONData["TaskStatus"]
                            )
                            self.test_run().add_log(LogSeverity.DEBUG, msg)
                            StageFWOOB_Status = False
            else:
                StageFWOOB_Status = True
        else:
            if image_type == "large":
                GPULargeFWMessage = "{GPULargeFWMessage}".format(**self.dut().redfish_uri_config.get("GPU"))
                if GPULargeFWMessage in JSONData["error"]:
                    StageFWOOB_Status = True
                else:
                    StageFWOOB_Status = False
            elif not (image_type in ["invalid_sign", "unsigned", "corrupt", "invalid_uuid", "empty_metadata", "empty_component"]):
                msg = "Staging failed with incorrect error message {}".format(
                    JSONData["error"]
                )
                self.test_run().add_log(LogSeverity.DEBUG, msg)

                StageFWOOB_Status = False
        if return_task_id:
            return StageFWOOB_Status, FwUpdTaskID
        else:
            return StageFWOOB_Status

    def ctam_fw_update_verify(self, image_type="default", corrupted_component_id=None):
        """
        :Description:				    Firmware Update verification
        :param image_type:			    Firmware image type
        :param corrupted_component_id:  ComponentIdentifier (in hex format) of the corrupted component image

        :returns:				        Update_Verified
        :rtype: 					    Bool
        """
        MyName = __name__ + "." + self.ctam_fw_update_verify.__qualname__
        Update_Verified = True

        PLDMPkgJson_file = self.get_PLDMPkgJson_file(image_type=image_type)
        # check again above code
        if PLDMPkgJson_file:
            with open(PLDMPkgJson_file, "r") as f:
                PLDMPkgJson = json.load(f)
        self.ctam_get_fw_version(PostInstall=1)
        msg = json.dumps(self.PostInstallDetails, indent=4)
        self.test_run().add_log(LogSeverity.DEBUG, msg)

        for element in self.PostInstallDetails:
            if str(element["Updateable"]) == "True" and element["SoftwareId"] != "":
                if image_type == "negate" \
                    or (image_type == "corrupt_component" and element["SoftwareId"] == corrupted_component_id):
                    ExpectedVersion = self.PreInstallVersionDetails[element["Id"]]
                    msg = "negative test case, expected version = {}".format(
                        ExpectedVersion
                    )
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
                    
                else:
                    ExpectedVersion = jsonhunt(
                        PLDMPkgJson,
                        "ComponentIdentifier",
                        str(hex(int(element["SoftwareId"], 16))),
                        "ComponentVersionString",
                    )
                if (
                    self.included_targets == []
                    or element["@odata.id"] in self.included_targets
                ):
                    if ExpectedVersion is None:
                        msg = "{} : {} : {} : Not in the PLDM bundle".format(
                            element["Id"],
                            element["SoftwareId"],
                            element["Version"]
                        )
                        self.test_run().add_log(LogSeverity.DEBUG, msg)
                    elif element["Version"] != ExpectedVersion:
                        # Positive Cases.
                        Update_Verified = False
                        msg = "{} : {} : {} : Update Failed : Expected {}".format(
                            element["Id"],
                            element["SoftwareId"],
                            element["Version"],
                            ExpectedVersion,
                        )
                        self.test_run().add_log(LogSeverity.DEBUG, msg)

                    elif image_type == "negate":
                        # Negative test case, but expected.
                        msg = "{} : {} : {} : Update Interrupted".format(
                            element["Id"], element["SoftwareId"], element["Version"]
                        )
                        self.test_run().add_log(LogSeverity.DEBUG, msg)
                    
                    else:
                        # Positive test case but a failure
                        msg = "{} : {} : {} : Update Successful".format(
                            element["Id"], element["SoftwareId"], element["Version"]
                        )
                        self.test_run().add_log(LogSeverity.DEBUG, msg)

        return Update_Verified

    def ctam_pushtargets(self, targets=[], illegal=0):
        MyName = __name__ + "." + self.ctam_pushtargets.__qualname__
        PushSuccess = False
        targets = [
            self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}"
                + "/UpdateService/FirmwareInventory/{}".format(element),
                component_type="GPU",
            )
            for element in targets
        ]
        Payload = {"HttpPushUriTargets": targets}

        v1_str = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )

        response = self.dut().run_redfish_command(uri=v1_str, mode="PATCH", body=Payload)

        JSONData = response.dict

        #print(json.dumps(JSONData, indent=4))

        if jsondeephunt(JSONData, "Message") == "The request completed successfully.":
            JSONData = self.ctam_getus()
            if str(JSONData["HttpPushUriTargets"]) == str(targets):
                PushSuccess = True
                self.included_targets = targets

                msg = f"Myname: {MyName} and Included Targets: {self.included_targets}"
                self.test_run().add_log(LogSeverity.DEBUG, msg)
            else:
                msg = f"MyName: {MyName} and HttpPushUriTargets: {JSONData['HttpPushUriTargets']}"
                self.test_run().add_log(LogSeverity.DEBUG, msg)

                print("{} {}".format(MyName, str(targets)))
        return PushSuccess

    def RedFishFWUpdate(self, BinPath, URI):
        """
        :Description:         It will update system firmware using redfish command.
        :param BinPath:		  Path for the bin
        :param URI:		      URI for creating URL

        :returns:		      JSON data after executing redfish command
        :rtype:               JSON Dict
        """
        MyName = __name__ + "." + self.RedFishFWUpdate.__qualname__
        FileName = BinPath

        URL = URI  # + '"' + FileName + '"'
        if self.dut().SshTunnel \
            or self.dut().dut_config.get("UnstructuredHttpPush", {}).get("value", False):
            # Unstructured HTTP push update
            headers = {"Content-Type": "application/octet-stream"}
            body = open(FileName, "rb").read()
        else:
            headers = {"Content-Type": "multipart/form-data"}
            body = {}
            body["UpdateFile"] = (
                FileName,
                open(FileName, "rb"),
                "application/octet-stream",
            )
        response = self.dut().run_redfish_command(uri=URL, mode="POST", body=body, headers=headers)
        JSONData = response.dict
        msg = "{0}: RedFish Input: {1} Result: {2}".format(MyName, FileName, JSONData)
        # msg_2 = "FW Update URL = {}".format(URL)
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return JSONData

    def ctam_build_updatable_device_list(self, illegal=0):
        MyName = __name__ + "." + self.ctam_build_updatable_device_list.__qualname__
        JSONData = self.ctam_getfi(expanded=1)
        updateable_devices = []
        true = True
        false = False
        if not illegal:
            jsonhuntall(JSONData, "Updateable", true, "Id", updateable_devices)
        else:
            jsonhuntall(JSONData, "Updateable", false, "Id", updateable_devices)
        if updateable_devices == []:
            self.test_run().add_log(LogSeverity.DEBUG, "No updatable devices found")
        return updateable_devices

    def ctam_selectpartiallist(self, count=0, excluded_targets=[], specific_targets=[], illegal=0):
        MyName = __name__ + "." + self.ctam_selectpartiallist.__qualname__
        PartialDeviceSelected = True
        self.ctam_pushtargets()
        device_list = self.ctam_build_updatable_device_list(illegal)
        if specific_targets == []:
            if count == 0:
                count = len(device_list)
            device_list_new = [device for device in device_list if not device in excluded_targets]
            RandomListOfDevices = random.choices(device_list_new, k=random.randint(1, count))
            self.test_run().add_log(LogSeverity.INFO, RandomListOfDevices)
            if self.ctam_pushtargets(RandomListOfDevices, illegal):
                PartialDeviceSelected = True
        else:
            if all(device in device_list for device in specific_targets):
                PartialDeviceSelected = True
                self.ctam_pushtargets(specific_targets, illegal)
            else:
                PartialDeviceSelected = False
                self.test_run().add_log(LogSeverity.INFO, "specific_targets is not available in Device list")
            JSONData = self.ctam_getus()
        return PartialDeviceSelected
    
    def ctam_get_component_to_be_corrupted(self):
        """
        :Description:         It will check the package_info.json for CorruptComponentIdentifier.
                              If it is not provided, it'll find the first updatabele element from firmware inventory.

        :returns:		      SoftwareID of the component to be corrupted (in hex format)
        :rtype:               str
        """
        MyName = __name__ + "." + self.ctam_get_component_to_be_corrupted.__qualname__        
        corrupt_component_id = self.dut().package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("CorruptComponentIdentifier", "")
        
        if corrupt_component_id == "":
            JSONData = self.ctam_getfi(expanded=1)
            for element in JSONData["Members"]:
                if str(element["Updateable"]) == "True":
                    corrupt_component_id = element["SoftwareId"]
        #component_id = hex(int(corrupt_component_id, 16))
        msg = f"{MyName} returned component ID to be corrupted: {corrupt_component_id}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        
        return corrupt_component_id
    
    def ctam_check_component_fwupd_failure(self, task_message_list, corrupted_component_id):
        """
        :Description:                       It will check if the task status message list is showing the
                                            corrupted component update failed and all other component
                                            copying (staging) went through.
        
        :param task_message_list:           List of message from the task status response
        :param corrupted_component_id:      ComponentIdentifier (in hex format) of the corrupted component image

        :returns:				    	    NonCorruptCompStaging_Success
        :rtype:                             Bool
        """
        MyName = __name__ + "." + self.ctam_check_component_fwupd_failure.__qualname__        
        NonCorruptCompStaging_Success = True
        
        corrupted_component_list = self.ctam_get_component_list(corrupted_component_id)
        
        for message in task_message_list:
            # Check if the component is not corrupted, but the severity is not OK
            if (not any(item in corrupted_component_list for item in message["MessageArgs"])) \
                and "Update" in message["MessageId"] \
                and message["Severity"] != "OK":
                    NonCorruptCompStaging_Success = False
                    return
            
        return NonCorruptCompStaging_Success
    
    def ctam_get_component_list(self, component_id):
        """
        :Description:                       It will check FW Inventory and find all the components with
                                            the provided component ID.
        
        :param component_id:                Component ID / SoftwareID

        :returns:				    	    List of components with the component ID
        :rtype:                             list
        """
        JSONData = self.ctam_getfi(expanded=1)
        component_list = []
        jsonhuntall(JSONData, "SoftwareId", component_id, "Id", component_list)
        return component_list
        
        
    