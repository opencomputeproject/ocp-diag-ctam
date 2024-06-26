"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
from operator import contains
import os
import json
import subprocess
import time
import ast
import shlex
from datetime import datetime
from typing import Optional, List
import ocptv.output as tv
from ocptv.output import LogSeverity

from interfaces.comptool_dut import CompToolDut
from utils.fwpkg_utils import FwpkgSignature, PLDMFwpkg

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
    

    def get_JSONFWFilePayload_file(self, image_type="default", corrupted_component_id=None):
        """
        :Description:           Get Payload file

        :param expanded:		image type

        :returns:	            File path
        :rtype:                 string
        """

        # FIXME: Refactor.. Lots of repeated code
        # if not self.dut().package_config:
        #     raise Exception("Please provide data in package config file to run this test case...")
        has_signature = self.dut().package_config.get("GPU_FW_IMAGE", {}).get("HasSignature", "")
        singature_struct_bytes = self.dut().package_config.get("GPU_FW_IMAGE", {}).get("SignatureStructBytes", "")
        package_config = self.dut().package_config
        cwd = self.dut().cwd
        if image_type == "default":
            return os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
            )
        elif image_type == "large":
            if package_config.get("GPU_FW_IMAGE_LARGE", {}).get("Package", "") != "":
                return os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE_LARGE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE_LARGE", {}).get("Package", ""),
                )
            else:
                golden_fwpkg_path = os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
                )
                JSONData = self.ctam_getus()
                max_bundle_size = JSONData.get("MaxImageSizeBytes") # FIXME: Do we need a default?
                return PLDMFwpkg.make_large_package(golden_fwpkg_path, max_bundle_size)
                
        elif image_type == "invalid_sign":
            if package_config.get("GPU_FW_IMAGE_INVALID_SIGNED", {}).get("Package", "") != "":
                return os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE_INVALID_SIGNED", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE_INVALID_SIGNED", {}).get("Package", ""),
                )
            else:
                golden_fwpkg_path = os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
                )
                return FwpkgSignature.invalidate_signature_in_pkg(golden_fwpkg_path)
            
        elif image_type == "invalid_pkg_uuid":
            golden_fwpkg_path = os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
            )
            return PLDMFwpkg.corrupt_package_UUID(golden_fwpkg_path)
            
        elif image_type == "invalid_device_uuid":
            golden_fwpkg_path = os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
            )
            return PLDMFwpkg.corrupt_device_record_uuid_in_pkg(golden_fwpkg_path,
                                                                               has_signature, singature_struct_bytes)
        
        elif image_type == "empty_metadata":
            if corrupted_component_id is None:
                corrupted_component_id = self.ctam_get_component_to_be_corrupted()
            msg = f"Corrupted component ID: {corrupted_component_id}"
            self.test_run().add_log(LogSeverity.DEBUG, msg)
            golden_fwpkg_path = os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
            )
            metadata_size = package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("MetadataSizeBytes", 4096)
            return PLDMFwpkg.clear_component_metadata_in_pkg(golden_fwpkg_path, corrupted_component_id, metadata_size)
        
        elif image_type == "corrupt_component":
            if package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("Package", "") != "":
                return os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("Package", ""),
                )
            else:
                if corrupted_component_id is None:
                    corrupted_component_id = self.ctam_get_component_to_be_corrupted()
                msg = f"Corrupted component ID: {corrupted_component_id}"
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                golden_fwpkg_path = os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
                )
                return PLDMFwpkg.clear_component_image_in_pkg(golden_fwpkg_path, corrupted_component_id)
        
        elif image_type == "backup":
            return os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE_BACKUP", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE_BACKUP", {}).get("Package", ""),
            )
        elif image_type == "old_version":
            return os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE_OLD", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE_OLD", {}).get("Package", ""),
            )

        elif image_type == "unsigned_component_image":
            # As of now, there is no suitable way to update the component's signature on-the-fly.
            # So vendor needs to provide a bundle with an unsigned component image
            return os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE_UNSIGNED_COMPONENT", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE_UNSIGNED_COMPONENT", {}).get("Package", ""),
            )
                
        elif image_type == "unsigned_bundle":
            if package_config.get("GPU_FW_IMAGE_UNSIGNED_BUNDLE", {}).get("Package", "") != "":
                return os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE_UNSIGNED_BUNDLE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE_UNSIGNED_BUNDLE", {}).get("Package", ""),
                )
            else:
                golden_fwpkg_path = os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
                )
                return FwpkgSignature.clear_signature_in_pkg(golden_fwpkg_path)
        
        elif image_type == "corrupt":
            if package_config.get("GPU_FW_IMAGE_CORRUPT", {}).get("Package", "") != "":
                return os.path.join(
                cwd,
                package_config.get("GPU_FW_IMAGE_CORRUPT", {}).get("Path", ""),
                package_config.get("GPU_FW_IMAGE_CORRUPT", {}).get("Package", ""),
                )
            else:
                corrupted_component_id = self.ctam_get_component_to_be_corrupted() if corrupted_component_id is None else corrupted_component_id
                msg = f"Corrupted component ID: {corrupted_component_id}"
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                golden_fwpkg_path = os.path.join(
                    cwd,
                    package_config.get("GPU_FW_IMAGE", {}).get("Path", ""),
                    package_config.get("GPU_FW_IMAGE", {}).get("Package", ""),
                )
                metadata_size = package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("MetadataSizeBytes", 4096)
                return PLDMFwpkg.corrupt_component_image_in_pkg(golden_fwpkg_path, corrupted_component_id, metadata_size,
                                                                has_signature, singature_struct_bytes)
                
        elif image_type == "negate":
            self.test_run().add_log(LogSeverity.INFO, "Negative Test Case")
            return ""
        return ""

    def get_PLDMPkgJson_file(self, image_type="default"):
        """
        :Description:           Get PLDM package file

        :param expanded:		image type

        :returns:	            File path
        :rtype:                 string
        """
        # if not self.dut().package_config:
        #     raise Exception("Please provide data in package config file to run this test case...")
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
            
        elif image_type == "corrupt_component":
            pldm_json_file = os.path.join(
                self.dut().cwd,
                self.dut().package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("Path", ""),
                self.dut().package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("JSON", ""),
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
        :Description:       Get Update Service
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
    
    def get_events(self):
        ctam_getes_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/EventService/Subscriptions", component_type="GPU")
        response = self.dut().run_redfish_command(uri=ctam_getes_uri)
        return response.dict, ctam_getes_uri

    def ctam_getes(self, path=None):
        """
        :Description:       Get Event Service and child collection items.
        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """

        MyName = __name__ + "." + self.ctam_getes.__qualname__

        if path == "Subscriptions":
            SubscriptionsList = []
            response, ctam_getes_uri = self.get_events()
            members = response["Members"]
            if not members:
                # create event if members are empty
                self.ctam_create_es(
                destination="https://172.17.0.202:8081/redfish/v1/RedfishEvents/EventReceiver/5",
                RegistryPrefixes="ResourceEvent", Context="rm_server_5", Protocol="Redfish")
                response, _ = self.get_events()
                members = response["Members"]
            for  member in members:
                memberId = member["@odata.id"].split('/')[-1].strip()
                ctam_getsid_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/EventService/Subscriptions", component_type="GPU")
                ctam_getsid_uri = ctam_getsid_uri + "/" + memberId
                response = self.dut().run_redfish_command(uri=ctam_getsid_uri)
                SubscriptionsList.append(memberId)
            data = SubscriptionsList
        else:
            ctam_getes_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/EventService", component_type="GPU")
            response = self.dut().run_redfish_command(uri=ctam_getes_uri)
            data = response.dict

        msg = f"The Redfish Command URI is : {ctam_getes_uri} \nThe Response for this command is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data

    def ctam_create_es(self, destination, RegistryPrefixes, Context, Protocol):
        """
        :Description:       Create a subscription
        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """
        MyName = __name__ + "." + self.ctam_create_es.__qualname__

        ctam_uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/EventService/Subscriptions", component_type="GPU"
        )

        payload = {"Destination": destination, "RegistryPrefixes": [RegistryPrefixes], "Context": Context, "Protocol": Protocol, "HttpHeaders": []}
        response = self.dut().run_redfish_command(uri=ctam_uri, mode="POST", body=payload)

        data = response.dict
        msg = f"The Redfish Command URI is : {ctam_uri} \nThe Response for this command is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data

    def ctam_gettsks(self):
        """
        :Description:       Get Task Service
        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """
        MyName = __name__ + "." + self.ctam_getus.__qualname__

        ctam_gettsks_uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/TaskService", component_type="GPU"
        )

        response = self.dut().run_redfish_command(uri=ctam_gettsks_uri)
        data = response.dict
        msg = f"The Redfish Command URI is : {ctam_gettsks_uri} \nThe Response for this command is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data

    def NodeACReset(self):
        """
        :Description:        It will Reset the node.

        :returns:	         None
        :rtype:              None
        """
        MyName = __name__ + "." + self.NodeACReset.__qualname__
        power_off_command = self.dut().dut_config.get("PowerOffCommand", {}).get("value", "")
        power_on_command = self.dut().dut_config.get("PowerOnCommand", {}).get("value", "")
        if not power_off_command or not power_on_command:
            self.test_run().add_log(LogSeverity.INFO, "Please provide both power on and power off command in dut config!")
            return 
        # execute power off
        self.test_run().add_log(LogSeverity.INFO, json.dumps(power_off_command, indent=4))
        arguments = shlex.split(power_off_command)
        cwd_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        cwd_path = None if cwd_path == "/tmp" else cwd_path
        subprocess.check_output(arguments, cwd=cwd_path)
        time.sleep(self.dut().dut_config.get("PowerOffWaitTime", {}).get("value", 60))
        self.test_run().add_log(LogSeverity.INFO, "Power Off wait time done")
        # execute power on
        self.test_run().add_log(LogSeverity.INFO, json.dumps(power_on_command, indent=4))
        arguments = shlex.split(power_on_command)
        subprocess.check_output(arguments, cwd=cwd_path)
        time.sleep(self.dut().dut_config.get("PowerOnWaitTime", {}).get("value", 300))
        self.test_run().add_log(LogSeverity.INFO, "Power ON wait time done")
        return

    def IsGPUReachable(self):
        """
        :Description:        It will check for GPU is available or not using Redfish command

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
    
    def ctam_activate_ac(self, check_time=False, gpu_check=True, fwupd_hyst_wait=True):
        """
        :Description:					Activate AC
        
        :param check_time:              Check the activation time does not exceed maximum time per spec

        :returns:				    	ActivationStatus
        :rtype: 						Bool
        """
        MyName = __name__ + "." + self.ctam_activate_ac.__qualname__
        ActivationStatus = False
        
        if check_time:
            FwActivationTimeMax = self.dut().dut_config["FwActivationTimeMax"]["value"]
            if self.dut().dut_config["PowerOnWaitTime"]["value"] > FwActivationTimeMax:
                msg = f"PowerOnWaitTime is greater than FwActivationTimeMax as per the json config file. Setting FwActivationTimeMax = PowerOnWaitTime"
                self.test_run().add_log(LogSeverity.WARNING, msg)
                FwActivationTimeMax = self.dut().dut_config["PowerOnWaitTime"]["value"]
        
        self.NodeACReset()  # NodeACReset declaration pending
        
        if gpu_check:
            ActivationStartTime = time.time() - self.dut().dut_config["PowerOnWaitTime"]["value"] # When the system was reset
            while "error" in self.IsGPUReachable():  # declaration pending
                msg = "GPU showing error"
                self.test_run().add_log(LogSeverity.DEBUG, msg)
            while (self.IsGPUReachable())["Status"][
                "State"
            ] != "Enabled" \
                    and (not check_time or (check_time and (time.time() - ActivationStartTime) <= FwActivationTimeMax)): # declaration pending
                msg = "Waiting for GPU to be back up, {}".format(
                    (self.IsGPUReachable())["Status"]["State"]
                )
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                time.sleep(30)
            ActivationEndTime = time.time()
            
            if check_time and (ActivationEndTime - ActivationStartTime) > FwActivationTimeMax:
                ActivationStatus = False
                msg = f"Activation is taking longer than the maximum time specified {FwActivationTimeMax} seconds."
                self.test_run().add_log(LogSeverity.WARNING, msg)
            else:
                ActivationStatus = True
        
        if fwupd_hyst_wait == True:
            IdleWaitTime = self.dut().dut_config["IdleWaitTimeAfterFirmwareUpdate"]["value"]
            msg = f"Execution will be delayed by {IdleWaitTime} seconds."
            self.test_run().add_log(LogSeverity.INFO, msg)
            time.sleep(IdleWaitTime)
            msg = f"Execution is delayed successfully by {IdleWaitTime} seconds."
            self.test_run().add_log(LogSeverity.INFO, msg)
            
        return True and ActivationStatus
    
    def RedfishTriggerDumpCollection(self, DiagnosticDataType, URI, OEMDiagnosticDataType=None):
        """
        :Description:                     It will trigger the collection of diagnostic data.
        :param DiagnosticDataType:		  e.g. Manager, OEM etc.
        :param URI:		                  URI for creating URL
        :param OEMDiagnosticDataType:     Type of OEM Diagnostic. default=None.

        :returns:		      JSON data after executing redfish command
        :rtype:               JSON Dict
        """
        MyName = __name__ + "." + self.RedfishTriggerDumpCollection.__qualname__
        URL = URI + "/LogServices/Dump/Actions/LogService.CollectDiagnosticData"
        msg = "Dump Collection URL = {}".format(URL)
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        
        payload = { "DiagnosticDataType": DiagnosticDataType }
        if OEMDiagnosticDataType:
            payload["OEMDiagnosticDataType"] = "DiagnosticType=" + OEMDiagnosticDataType
        response = self.dut().run_redfish_command(uri=URL, mode="POST", body=payload)
        JSONData = response.dict

        msg = "{0}: RedFish Input: {1} Result: {2}".format(MyName, payload, JSONData)
        self.test_run().add_log(LogSeverity.INFO, msg)
        
        return JSONData
    
    def RedfishDownloadDump(self, DumpURI):
        """
        :Description:              It will download the specified dump using redfish command and untar the downloaded dump.
        :param DumpLocation:	   Dump location URI 

        :returns:				   DumpPath (Path to downloaded dump)
        :rtype:                    string
        """
        MyName = __name__ + "." + self.RedfishDownloadDump.__qualname__
        URL = DumpURI + "/attachment"
        msg = "Dump Entry URL = {}".format(URL)
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        
        dt = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        dump_tarball_path = os.path.join( 
                self.dut().workspace_dir,
                "{}_dump.tar.xz".format(dt))
        response =  self.dut().run_redfish_command(uri=URL, timeout=60)
        try:
            with open(dump_tarball_path, 'wb') as fd:
                fd.write(response.read)
            # Unzip the .tar file
            import tarfile
            dump = tarfile.open(dump_tarball_path)
            DumpPath = os.path.join( 
                self.dut().workspace_dir, 
                "{}_dump".format(dt))
            dump.extractall(DumpPath) # This will create a directory if it's not present already.
            dump.close()
            os.remove(dump_tarball_path) # Delete the tarball as it's not needed anymore
            folder_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(DumpPath) for filename in filenames)
            if folder_size > 0:
                return DumpPath
            else:
                print("Downloaded folder size is 0 KB.")
                return None
        except Exception as e:
            print(str(e))
            return None
    
    def ctam_monitor_task(self, TaskID=""):
        """
        :Description:       CTAM Monitor a Task
        :param TaskID       Task ID of TaskService/Tasks (for accelerator management) to monitor
        :returns:	        (Task_Completed, JSONData response)
        :rtype:             Tuple
        """
        Task_Completed = False
        JSONData = {}
        if not TaskID:
            # need to implement the flow for no task uri
            self.test_run().add_log(LogSeverity.DEBUG,
                    "No Task ID provided."
                )
            return Task_Completed, JSONData
        TaskURI = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}{TaskServiceURI}" + "{}".format(TaskID), component_type="GPU"
        )
        if self.dut().is_debug_mode():
            self.test_run().add_log(LogSeverity.DEBUG, f"Task URI: {TaskURI}")
            
        response = self.dut().run_redfish_command(TaskURI)
        JSONData = response.dict
        while JSONData["TaskState"] == "Running":
            response = self.dut().run_redfish_command(TaskURI)
            JSONData = response.dict
            if self.dut().is_debug_mode():
                self.test_run().add_log(LogSeverity.DEBUG,
                    "Task Percentage_Completion = {}".format(JSONData["PercentComplete"])
                )
            time.sleep(30)
        if JSONData["TaskState"] == "Completed" and JSONData["TaskStatus"] == "OK":
            Task_Completed = True
        else:
            Task_Completed = False
        
        return Task_Completed, JSONData


    def check_all_staging_tasks(self):
        task_service_uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}{TaskServiceURI}", component_type="GPU"
        )
        response = self.dut().run_redfish_command(uri=task_service_uri)
        json_data = response.dict
        task_list = [i["@odata.id"] for i in json_data["Members"]]
        for task in task_list:
            self.ctam_monitor_task(TaskID=task)
    
    
    
    def ctam_redfish_uri_deep_hunt(self, URI, uri_hunt="", uri_listing=[], uri_analyzed=[],action=0):
        """
        :Description:			CTAM Redfish URI Deep Hunt - a recursive function to look deep till we find all instances URI
        :param URI:             The top uri under which we are searching for the uri instances (type string)
        :param uri_hunt:        URI we are hunting for (type string).
        :param uri_listing:     An array that will eventually contain a list of all URIs that house the member to hunt.
        :param uri_analyzed:    An array that will eventually contain a list of all URIs that have been searched for. 
                                IMPORTANT - This filed must be passed else it will pick the list from previous test cases. 
        :param action           Should be set if we are searching for action uris. 

        :returns:				None
        """
        response = self.dut().run_redfish_command("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
        JSONData = response.dict
        if uri_hunt in JSONData:
            uri_listing.append(URI + "/" + uri_hunt)
            uri_analyzed.append(URI + "/" + uri_hunt)
            JSONData.pop(uri_hunt)
        if "Actions" in JSONData and (action == 1):
            self.ctam_redfish_action_hunt(JSONData["Actions"], uri_hunt,uri_listing,uri_analyzed)
            JSONData.pop("Actions")
        for element in JSONData:
            # Consider the case of nested dictionary
            if type(JSONData[element]) == type(dict()) and ("@odata.id" in JSONData[element]):
                URI = JSONData[element]["@odata.id"]
                if URI not in uri_analyzed:
                    uri_analyzed.append(URI)
                    self.ctam_redfish_uri_deep_hunt(URI, uri_hunt, uri_listing, uri_analyzed,action)
            # Consider the case of list of dictionaries                
            elif type(JSONData[element]) == type([]):
                for dictionary in JSONData[element]:
                    # Verify that it is indeed an array of dictionaries
                    URI = None 
                    if type(dictionary) == type(dict()) and ("@odata.id" in dictionary):
                        URI = dictionary["@odata.id"]
    
                    if URI and URI not in uri_analyzed:
                        uri_analyzed.append(URI)
                        self.ctam_redfish_uri_deep_hunt(URI, uri_hunt, uri_listing, uri_analyzed,action)

    def ctam_redfish_uri_hunt(self, URI, uri_hunt="", uri_listing=[]):
        """
        :Description:			CTAM Redfish URI Hunt - a recursive function to look into Members till we find all instances URI
        :param URI:             The top uri under which we are searching for the uri instances (type string)
        :param uri_hunt:        URI we are hunting for (type string).
        :param uri_listing:     An array that will eventually contain a list of all URIs that house the member to hunt.

        :returns:				None
        """
        response = self.dut().run_redfish_command(uri="{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
        JSONData = response.dict
        if uri_hunt in JSONData:
            uri_listing.append(URI + "/" + uri_hunt)
            return
        elif "Id" in JSONData and (uri_hunt in JSONData["Id"]):
            # possible for member to not have a name, like EventLog
            uri_listing.append(URI)
        elif "Members" in JSONData:
            i = 0
            for element in JSONData["Members"]:
                if "@odata.id" in element:
                    URI = JSONData["Members"][i]["@odata.id"]
                    self.ctam_redfish_uri_hunt(URI, uri_hunt, uri_listing)
                    i = i + 1

    def ctam_redfish_action_hunt(self, ActionJson, target_action_hunt="", uri_listing=[],uri_analyzed=[]):
        """
        :Description:			CTAM Redfish Action Hunt - a recursive function to look deep till we find all instances that contain a "target" or "actioninfo" whose value has target_action_hunt
        :param ActionJson:              Actions JSON Dict object to work on
        :param target_action_hunt:      URI we are hunting for (type string).
        :param uri_listing:             An array that will eventually contain a list of all URIs that house the member to hunt.
        :param uri_analyzed:            An array that contains the list of uris which are already analyzed. 
        :returns:				        None
        """
        
        if "target" in ActionJson and target_action_hunt in ActionJson["target"] and ActionJson["target"] not in uri_analyzed:
            uri_listing.append(ActionJson["target"])
            uri_analyzed.append(ActionJson["target"])
            ActionJson.pop("target")
        if "@Redfish.ActionInfo" in ActionJson and target_action_hunt in ActionJson["@Redfish.ActionInfo"] and ActionJson["@Redfish.ActionInfo"] not in uri_analyzed:
            uri_listing.append(ActionJson["@Redfish.ActionInfo"])
            uri_analyzed.append(ActionJson["@Redfish.ActionInfo"])
            ActionJson.pop("@Redfish.ActionInfo")
        for element in ActionJson:
            # Consider the case of nested dictionary
            if type(ActionJson[element]) == type(dict()):
                    self.ctam_redfish_action_hunt(ActionJson[element], target_action_hunt, uri_listing, uri_analyzed)

    def write_test_info(self, message):
        """
        :Description:           JSON Formatter for CTAM TestInfo File Logging

        :param message:		    MEssage to be added

        :returns:	            None
        """
        msg = {
                "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                "TestName": self.dut().current_test_name,
                "Message": message,
            }
        self.dut().test_info_logger.write(json.dumps(msg))
        
    def ctam_verify_expanded(self, JSONData):
        """
        :Description:					Check if the Redfish API response is expanded correctly (level 1)
        
        :param JSONData:                Redfish response in json/dictionary format
        :type JSONData:                 dictionary
        
        :returns:				    	result (Pass/Fail)
        :rtype: 						Bool
        """
        result = True
        for element in JSONData:
            # Simple dictionary
            if type(JSONData[element]) == type(dict()) and ("@odata.id" in JSONData[element]):
                if "@odata.type" not in JSONData[element]:
                    self.test_run().add_log(LogSeverity.ERROR, f"{JSONData[element]} is not expanded.")
                    result = False
                    break
            # List of dictionaries
            elif type(JSONData[element]) == type([]):
                for dictionary in JSONData[element]:
                    if type(dictionary) == type(dict()) and ("@odata.id" in dictionary):
                        if "@odata.type" not in dictionary:
                            self.test_run().add_log(LogSeverity.ERROR, f"{dictionary} is not expanded.")
                            result = False
                            break
        return result

    def ctam_getepc(self, expanded=1):
        """
        :Description:       Get Expanded Processor Collection

        :param expanded:		Expand Param

        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """
        # [TODO] need to figure out a way to grab all of them.
        MyName = __name__ + "." + self.ctam_getepc.__qualname__
        if expanded == 1:
            baseboard_ids = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
            for id in baseboard_ids:
                uri = "/Systems/" + id + "/Processors?$expand=*($levels=1)"
                ctam_getepc_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
                response = self.dut().run_redfish_command(uri=ctam_getepc_uri)
                data = response.dict

        msg = f"Command is : {ctam_getepc_uri} \nThe Response is : {data}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return data
    

    def ctam_deles(self):
        """
        :Description:       Get Event Service and child collection items.
        :returns:	        JSON Data after running Redfish command
        :rtype:             JSON Dict
        """
        # List all subscritions then grabbing one of them and delete

        MyName = __name__ + "." + self.ctam_deles.__qualname__
        ctam_getes_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/EventService/Subscriptions", component_type="GPU")
        subscriptionList = self.ctam_getes("Subscriptions")
        self.test_run().add_log(LogSeverity.INFO, "subscriptionList is {}\n".format(subscriptionList))
        # FIXME: Handle when subscriptionList is empty
        if not subscriptionList:
            self.ctam_create_es(
                destination="https://172.17.0.202:8081/redfish/v1/RedfishEvents/EventReceiver/5",
                RegistryPrefixes="ResourceEvent", Context="rm_server_5", Protocol="Redfish")
            subscriptionList = self.ctam_getes("Subscriptions")
        ctam_getes_uri = ctam_getes_uri + "/" + subscriptionList[-1]
        response = self.dut().run_redfish_command(uri=ctam_getes_uri, mode="DELETE")
        status = response.status
        if (status == 200 or status == 201):
            self.test_run().add_log(LogSeverity.INFO, "Test JSON")
            self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(ctam_getes_uri, status))
            result = True
        else:
            self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(ctam_getes_uri, status))
            result = False
        return result

    def ctam_redfish_GET_status_ok(self, uri):
        """
        :Description:   Check if the Redfish API response status is OK
        
        :param uri:     Redfish uri
        :type uri:      str
        
        :returns:       result (Pass/Fail)
        :rtype:         bool
        """
        result = True
        response = self.dut().run_redfish_command(uri=uri)
        JSONData = response.dict
        status = response.status
        if status == 200 or status == 201:
            self.test_run().add_log(LogSeverity.INFO, "GET request Passed: {} : {}".format(uri, JSONData))
        else:
            self.test_run().add_log(LogSeverity.FATAL, "GET request Failed: {} : {}".format(uri, JSONData))
            result = False
        return result
