"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
import os
import json
import subprocess
import time
from typing import Optional, List

import ocptv.output as tv
from ocptv.output import LogSeverity

from interfaces.comptool_dut import CompToolDut


class FunctionalIfc:
    """
    This super class primarily provides access to the DUT.  It should NOT be used as a collection of miscellaneous
    items.  Create additional focused subclasses from this one.
    """

    _dut: CompToolDut | None = None
    _test_run: Optional[tv.TestRun] = None  # OCP TestRun

    @staticmethod
    def SetUpAssociations(testrun: tv.TestRun, dut: CompToolDut):
        """
        The test framework will instance interfaces first, and then this class static method is used
        to create the class associations.

        :param dut: device under test
        :type dut: CompToolDut
        """
        FunctionalIfc._test_run = testrun
        FunctionalIfc._dut = dut

    @staticmethod
    def dut() -> CompToolDut:
        """
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active dut
        :rtype: CompToolDut
        """
        if FunctionalIfc._dut:
            return FunctionalIfc._dut
        else:
            raise NotImplementedError(f"need to call FunctionalIfc.SetUpAssociations")

    @staticmethod
    def test_run() -> tv.TestRun:
        """
        Robustness check to ensure associations have been setup before used at runtime

        :raises NotImplementedError: missed setup
        :return: active dut
        :rtype: CompToolDut
        """
        if FunctionalIfc._test_run:
            return FunctionalIfc._test_run
        else:
            raise NotImplementedError(f"need to call FunctionalIfc.SetUpAssociations")

    def __init__(self):
        """
        Default init for now
        """
        pass

    def get_JSONFWFilePayload_file(self, image_type="default"):
        """
        :Description:           Get Payload file

        :param expanded:		image type

        :returns:	            File path
        :rtype:                 string
        """

        if image_type == "default":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut().package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                self.dut().package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
            )
        elif image_type == "large":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut().package_config.get("GPU_FW_IMAGE_LARGE", {}).get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_LARGE", {})
                .get("Package", ""),
            )
        elif image_type == "invalid_sign":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut()
                .package_config.get("GPU_FW_IMAGE_INVALID_SIGNED", {})
                .get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_INVALID_SIGNED", {})
                .get("Package", ""),
            )
        elif image_type == "backup":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut()
                .package_config.get("GPU_FW_IMAGE_BACKUP", {})
                .get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_BACKUP", {})
                .get("Package", ""),
            )
        elif image_type == "old_version":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut().package_config.get("GPU_FW_IMAGE_OLD", {}).get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_OLD", {})
                .get("Package", ""),
            )

        elif image_type == "unsigned":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut()
                .package_config.get("GPU_FW_IMAGE_UNSIGNED", {})
                .get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_UNSIGNED", {})
                .get("Package", ""),
            )
        elif image_type == "corrupt":
            json_fw_file_payload = os.path.join(
                self.dut().cwd,
                self.dut()
                .package_config.get("GPU_FW_IMAGE_CORRUPT", {})
                .get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_CORRUPT", {})
                .get("Package", ""),
            )
        elif image_type == "negate":
            self.test_run().add_log(LogSeverity.INFO, "Negative Test Case")
            json_fw_file_payload = ""

        return json_fw_file_payload

    def get_PLDMPkgJson_file(self, image_type="default"):
        """
        :Description:           Get PLDM package file

        :param expanded:		image type

        :returns:	            File path
        :rtype:                 string
        """
        pldm_json_file = ""
        if image_type == "default":
            pldm_json_file = os.path.join(
                self.dut().cwd,
                self.dut().package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                self.dut().package_config.get("GPU_FW_IMAGE", {}).get("JSON", ""),
            )

        elif image_type == "backup":
            pldm_json_file = os.path.join(
                self.dut().cwd,
                self.dut()
                .package_config.get("GPU_FW_IMAGE_BACKUP", {})
                .get("Path", ""),
                self.dut()
                .package_config.get("GPU_FW_IMAGE_BACKUP", {})
                .get("JSON", ""),
            )
        elif image_type == "old_version":
            pldm_json_file = os.path.join(
                self.dut().cwd,
                self.dut().package_config.get("GPU_FW_IMAGE_OLD", {}).get("Path", ""),
                self.dut().package_config.get("GPU_FW_IMAGE_OLD", {}).get("JSON", ""),
            )
        return pldm_json_file

    def ctam_getfi(self, expanded=0):
        """
        :Description:               Act Get Firmware Inventory
        :param expanded:		Expand Param

        :returns:	                JSON Data after running Redfish command
        :rtype:                     JSON Dict
        """
        MyName = __name__ + "." + self.ctam_getfi.__qualname__

        if expanded == 1:
            ctam_fi_uri = self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}/UpdateService/FirmwareInventory?$expand=*($levels=1)",
                component_type="GPU",
            )
            response = self.dut().run_redfish_command(uri=ctam_fi_uri)
            data = response.dict

        else:
            ctam_fi_uri = self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}/UpdateService/FirmwareInventory",
                component_type="GPU",
            )
            response = self.dut().run_redfish_command(uri=ctam_fi_uri)
            data = response.dict
        msg = f"Command is : {ctam_fi_uri} \nThe Response is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)

        return data

    def ctam_getsi(self, expanded=0):
        """
        :Description:       Get Software Inventory

        :param expanded:		Expand Param

        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """
        MyName = __name__ + "." + self.ctam_getsi.__qualname__
        if expanded == 1:
            ctam_getsi_uri = self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}/UpdateService/SoftwareInventory?$expand=*($levels=1)",
                component_type="GPU",
            )
            response = self.dut().run_redfish_command(uri=ctam_getsi_uri)
            data = response.dict

        else:
            ctam_getsi_uri = self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}/UpdateService/SoftwareInventory",
                component_type="GPU",
            )
            response = self.dut().run_redfish_command(uri=ctam_getsi_uri)
            data = response.dict
        msg = f"Command is : {ctam_getsi_uri} \nThe Response is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data

    def ctam_getts(self):
        """
        :Description:       Act Get Telemetry Service
        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """

        MyName = __name__ + "." + self.ctam_getts.__qualname__
        ctam_getts_uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/TelemetryService", component_type="GPU"
        )
        response = self.dut().run_redfish_command(uri=ctam_getts_uri)
        data = response.dict
        msg = (
            f"Command is : {ctam_getts_uri} \nThe Response for this command is : {data}"
        )
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data

    def ctam_getus(self):
        """
        :Description:       Act Get Update Service
        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """
        MyName = __name__ + "." + self.ctam_getus.__qualname__

        ctam_getus_uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )

        response = self.dut().run_redfish_command(uri=ctam_getus_uri)
        data = response.dict
        msg = f"The Redfish Command URI is : {ctam_getus_uri} \nThe Response for this command is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data

    def NodeACReset(self):
        """
        :Description:        It will Reset the node.

        :returns:	         None
        :rtype:              None
        """
        MyName = __name__ + "." + self.NodeACReset.__qualname__
        command_to_run = ""
        command_to_run = self.dut().dut_config["PowerOffCommand"]["value"]
        self.test_run().add_log(LogSeverity.INFO, json.dumps(command_to_run, indent=4))
        subprocess.check_output(command_to_run, shell=self.dut().is_debug_mode())
        time.sleep(self.dut().dut_config["PowerOffWaitTime"]["value"])
        self.test_run().add_log(LogSeverity.INFO, "Power Off wait time done")
        command_to_run = self.dut().dut_config["PowerOnCommand"]["value"]
        self.test_run().add_log(LogSeverity.INFO, json.dumps(command_to_run, indent=4))
        subprocess.check_output(command_to_run, shell=self.dut().is_debug_mode())
        time.sleep(self.dut().dut_config["PowerOnWaitTime"]["value"])
        self.test_run().add_log(LogSeverity.INFO, "Power ON wait time done")
        return

    def IsGPUReachable(self):
        """
        :Description:        It will check fofr GPU is available or not using Redfish command

        :returns:	         JSON data after executing redfish command
        :rtype:              JSON Dict
        """
        MyName = __name__ + "." + self.IsGPUReachable.__qualname__
        ctam_getus_uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}{GPUCheckURI}", component_type="GPU"
        )

        response = self.dut().run_redfish_command(uri=ctam_getus_uri)
        JSONData = response.dict
        msg = "GPU Reachable info : {}".format(JSONData)
        self.test_run().add_log(LogSeverity.INFO, msg)
        return JSONData
    
    def ctam_activate_ac(self):
        """
        :Description:					Activate AC

        :returns:				    	ActivationStatus
        :rtype: 						Bool
        """
        MyName = __name__ + "." + self.ctam_activate_ac.__qualname__
        ActivationStatus = False
        self.NodeACReset()  # NodeACReset declaration pending

        while "error" in self.IsGPUReachable():  # declaration pending
            msg = "GPU showing error"
            self.test_run().add_log(LogSeverity.DEBUG, msg)
        while (self.IsGPUReachable())["Status"][
            "State"
        ] != "Enabled":  # declaration pending
            msg = "Waiting for GPU to be back up, {}".format(
                (self.IsGPUReachable())["Status"]["State"]
            )
            self.test_run().add_log(LogSeverity.DEBUG, msg)
        ActivationStatus = True
        return ActivationStatus
