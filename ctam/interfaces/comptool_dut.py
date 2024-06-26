"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import os
import typing as ty
import redfish
import subprocess
import platform
import json
import time
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd

from prettytable import PrettyTable
from ocptv.output import Metadata
from ocptv.output import Dut

from interfaces.uri_builder import UriBuilder
# from sshtunnel import SSHTunnelForwarder, HandlerSSHTunnelForwarderError
from utils.ssh_tunnel_utils import SSHTunnel


class CompToolDut(Dut):
    """
    This subclass derived from OCP dut allows for faster turnaround to add new functionality.
    Periodically this class can be reviewed to determine what functionality should be moved
    to ocptv Dut

    :param Dut: OCP super class
    :type Dut: ocptv.output.Dut
    """

    def __init__(
        self,
        id: str,
        config,
        package_config,
        redfish_uri_config,
        net_rc,
        debugMode: bool,
        console_log: bool,
        logger,
        test_info_logger,
        workspace_dir,
        test_uri_response_check,
        redfish_response_messages,
        logger_path,
        name: ty.Optional[str] = None,
        metadata: ty.Optional[Metadata] = None,
    ):
        """
        Passes same parameter to super class

        :param id: identification
        :type id: str
        :param debugMode: true if in debug mode
        :type debugMode: bool
        :param name: name to identify dyt, defaults to None
        :type name: ty.Optional[str], optional
        :param metadata: additional descriptive data, defaults to None
        :type metadata: ty.Optional[Metadata], optional
        """
        self._debugMode: bool = debugMode
        self._console_log: bool = console_log
        self.__package_config_file = package_config
        self.dut_config = config["properties"]
        self.redfish_uri_config = redfish_uri_config
        self.uri_builder = UriBuilder(redfish_uri_config)
        self.current_test_name = ""
        self.net_rc = net_rc
        self.logger = logger
        self.workspace_dir = workspace_dir
        self.logger_path = logger_path
        self.test_info_logger = test_info_logger
        self.test_uri_response_check = test_uri_response_check
        self.redfish_response_messages = redfish_response_messages
        self.cwd = self.get_cwd()
        super().__init__(id, name, metadata)
        self.connection_ip_address = config["properties"]["ConnectionIPAddress"][
            "value"
        ]
        self.default_prefix = self.uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
        self.port_list = config["properties"]["SSHTunnelPortList"]["value"]
        self.protocol = config["properties"]["SSHTunnelProtocol"]["value"]
        self.remote_port = config["properties"]["SSHTunnelRemotePort"]["value"]
        self.__user_name, _, self.__user_pass = self.net_rc.authenticators(
            self.connection_ip_address
        )
        self.multipart_form_data = redfish_uri_config.get("GPU", {}).get("MultiPartFormData", False)
        self.binded_port = None
        self.SSHTunnelRemoteIPAddress = None
        self.ssh_tunnel_required = config["properties"].get("SSHTunnel", {}).get("value", False)
        if self.ssh_tunnel_required:
            self.SSHTunnelRemoteIPAddress = config["properties"].get("SSHTunnelRemoteIPAddress", {}).get("value", None)
            if not self.SSHTunnelRemoteIPAddress:
                raise Exception("SSHTunnelRemoteIPAddress must be provided when SSHTunnel is set to True.")
            #self.AMCIPAddress = config["properties"].get("AMCIPAddress", {}).get("value", None) TODO - Commented for now, can we remove this? 
        
        self.redfish_ifc = None
        self.redfish_auth = config["properties"].get("AuthenticationRequired", {}).get("value", False)
        self.ssh_tunnel = SSHTunnel(self.test_info_logger)
    
    def get_cwd(self):
        cwd = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return "" if cwd == "/tmp" else cwd


    def set_up_connection(self):
        """
        This method sets up connection to the DUT,
        which includes ssh_tunneling, Redfish client setup and login if needed
        """
        # Set up SSH Tunneling if requested
        if self.ssh_tunnel_required:
            # Set up port forwarding
            if not self.SSHTunnelRemoteIPAddress:#TODO - Is this needed again? 
                raise Exception("SSHTunnelRemoteIPAddress must be provided when SSHTunnel is set to True.")
            self.binded_port = self.ssh_tunnel.setup_ssh_tunnel(remote_host=self.SSHTunnelRemoteIPAddress, remote_port=self.remote_port,
                                             ssh_host=self.connection_ip_address, ssh_port=22,
                                             ssh_username=self.user_name, ssh_password=self.user_pass,
                                             local_port=self.port_list)
            
            self.connection_ip_address = "127.0.0.1:" + str(self.binded_port) 
            self.__user_name, _, self.__user_pass = self.net_rc.authenticators(
                self.SSHTunnelRemoteIPAddress
            )
        
        # TODO investigate storing FW update files via add_software_info() in super
        self.__connection_url = f"{self.protocol}://" + self.connection_ip_address
        self.redfish_ifc = redfish.redfish_client(
            self.__connection_url,
            username=self.__user_name,
            password=self.__user_pass,
            default_prefix=self.default_prefix,
            timeout=30
        )

        if self.redfish_auth:
            self.redfish_ifc.login(auth="basic")   #TODO investigate 'session' token auth
            self.test_info_logger.log("Redfish login is successful.")

    @property
    def package_config(self):
        _package_config = {}
        if os.path.isfile(self.__package_config_file):
            with open(self.__package_config_file) as package_info_json:
                _package_config = json.load(package_info_json)
            return _package_config
        else:
            self.test_info_logger.log("No package_info.json file found...")
            return {}
            # raise Exception("Please provide package info config file...")

    @property
    def user_name(self):
        return self.__user_name
    
    @user_name.setter
    def user_name(self, value):
        raise Exception("Username can not be override...")

    @property
    def user_pass(self):
        return self.__user_pass
    
    @user_pass.setter
    def user_pass(self, value):
        raise Exception("Password can not be override...")
    
    @property
    def connection_url(self):
        return self.__connection_url
    
    @connection_url.setter
    def connection_url(self, value):
        raise Exception("Connection IP can not be override...")

    def run_redfish_command(self, uri, mode="GET", body=None, headers=None, timeout=None):
        """
        This method is for running redfish commands according to mode and log the output into
        a formatted log file and return the response
        
        :param uri: uri for redfish connection
        :type uri: str
        :param mode: Mode for fetching data or updating
        :type mode: str
        :param body: body for requests
        :type body: ty.Optional[dict], optional
        :param header: header for requests, defaults to None
        :type metadata: ty.Optional[dict], optional

        :return: response for requests
        :rtype: response object or None in case of failure
        """
        try:
            start_time = time.time()
            response = None
            msg = {
                    "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                    "TestName": self.current_test_name,
                    "URI": uri,
            }
            kwargs = {"path": uri, "headers": headers}
            if timeout is not None:
                kwargs.update({"timeout": timeout})
                
            if mode == "POST":
                msg.update({"Method":"POST"})
                #msg.update({"Method":"POST","Data":"{}".format(body),}) # FIXME: It floods the logs. Do we need to log the entire body? 
                kwargs.update({"body": body})
                response = self.redfish_ifc.post(**kwargs) # path=uri, body=body, headers=headers
            elif mode == "PATCH":
                msg.update({"Mode":"PATCH","Data":"{}".format(body),})
                kwargs.update({"body": body})
                response = self.redfish_ifc.patch(**kwargs) # path=uri, body=body, headers=headers
            elif mode == "GET":
                msg.update({"Method":"GET",})
                response = self.redfish_ifc.get(**kwargs) # path=uri, headers=headers
            elif mode == "DELETE":
                msg.update({"Method":"DELETE",})
                response = self.redfish_ifc.delete(**kwargs) # path=uri, headers=headers   
            
            end_time = time.time()
            time_difference_seconds = end_time - start_time
            time_difference = datetime.utcfromtimestamp(time_difference_seconds) - datetime.utcfromtimestamp(0)
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = int(time_difference.microseconds / 1000)
            formatted_time = "{:02d}H:{:02d}M:{:02d}S:{:03d}MS".format(hours, minutes, seconds, milliseconds)
            
            msg.update({"ResponseTime": "{}".format(formatted_time)})

            if response.status in range (200,204) and response.text: # FIXME: Add error handling in case the request fails
                msg.update({
                    "ResponseCode": response.status,
                    "Response":response.dict, # FIXME: self-test report cannot be converted to dict # FIXED: Throws error in some cases when response.dict is used and the response body is empty
                    }) 
            elif response.status in range (200,204):
                msg.update({
                    "ResponseCode": response.status,
                    "Response":"Success but no response body",
                    })
            elif response.status > 300: 
                msg.update({
                    "ResponseCode": response.status,
                    "Response":f"Unexpected Response: {response.text}",
                    })
            else:
                msg.update({
                    "ResponseCode": f"Unexpected status: {response.status}",
                    "Response": response.text,
                    })
        except Exception as e:
            msg.update({
            "ResponseCode": None,
            "Response":f"FATAL: Exception occurred while running redfish command - {e}",
            })
        finally:                         
            self.logger.write(json.dumps(msg))
            return response
        
    
    def run_request_command(self, uri, mode="GET", body=None, headers=None, timeout=None, files=None, verify=False):
        """
        This method is for running redfish commands according to mode and log the output into
        a formatted log file and return the response
        
        :param uri: uri for redfish connection
        :type uri: str
        :param mode: Mode for fetching data or updating
        :type mode: str
        :param body: body for requests
        :type body: ty.Optional[dict], optional
        :param header: header for requests, defaults to None
        :type metadata: ty.Optional[dict], optional

        :return: response for requests
        :rtype: response object or None in case of failure
        """
        try:
            start_time = time.time()
            response = None
            msg = {
                    "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                    "TestName": self.current_test_name,
                    "URI": uri,
            }
            url = self.connection_url + uri
            kwargs = {"path": uri, "headers": headers}
            auth = HTTPBasicAuth(self.user_name, self.user_pass)
            if timeout is not None:
                kwargs.update({"timeout": timeout})
                
            if mode == "POST":
                msg.update({"Method":"POST"})
                #msg.update({"Method":"POST","Data":"{}".format(body),}) # FIXME: It floods the logs. Do we need to log the entire body? 
                kwargs.update({"body": body})
                response = requests.post(url=url, data=body, files=files, headers=headers, auth=auth, verify=verify) # path=uri, body=body, headers=headers
            elif mode == "PATCH":
                msg.update({"Mode":"PATCH","Data":"{}".format(body),})
                kwargs.update({"body": body})
                response = requests.patch(url=url, data=body, files=files, headers=headers, auth=auth, verify=verify) # path=uri, body=body, headers=headers
            elif mode == "GET":
                msg.update({"Method":"GET",})
                response = requests.get(url=url, data=body, files=files, headers=headers, auth=auth, verify=verify)# path=uri, headers=headers
            elif mode == "DELETE":
                msg.update({"Method":"DELETE",})
                response = requests.delete(url=url, data=body, files=files, headers=headers, auth=auth, verify=verify) # path=uri, headers=headers   
            
            end_time = time.time()
            time_difference_seconds = end_time - start_time
            time_difference = datetime.utcfromtimestamp(time_difference_seconds) - datetime.utcfromtimestamp(0)
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = int(time_difference.microseconds / 1000)
            formatted_time = "{:02d}H:{:02d}M:{:02d}S:{:03d}MS".format(hours, minutes, seconds, milliseconds)
            
            msg.update({"ResponseTime": "{}".format(formatted_time)})

            if response.status_code in range (200,204) and response.text: # FIXME: Add error handling in case the request fails
                msg.update({
                    "ResponseCode": response.status_code,
                    "Response":response.json(), # FIXME: self-test report cannot be converted to dict # FIXED: Throws error in some cases when response.dict is used and the response body is empty
                    }) 
            elif response.status_code in range (200,204):
                msg.update({
                    "ResponseCode": response.status_code,
                    "Response":"Success but no response body",
                    })
            elif response.status_code > 300: 
                msg.update({
                    "ResponseCode": response.status_code,
                    "Response":f"Unexpected Response: {response.text}",
                    })
            else:
                msg.update({
                    "ResponseCode": f"Unexpected status: {response.status_code}",
                    "Response": response.text,
                    })
        except Exception as e:
            msg.update({
            "ResponseCode": None,
            "Response":f"FATAL: Exception occurred while running redfish command - {e}",
            })
        finally:                         
            self.logger.write(json.dumps(msg))
            return response

    def check_uri_response(self, uri, response):
        if not self.test_uri_response_check:
            msg = {"Message":"FATAL: Please provide the file name in test runner config"}
            self.test_info_logger.write(json.dumps(msg))
            return True
        try:
            def get_val_from_str(string, dct):
                keys = string.split('.')
                v = dct
                for key in keys:
                    v = v.get(key, {})
                return True if v else False
            nested_data = []
            
            data = pd.read_excel(self.test_uri_response_check).to_dict(orient='records')
            attributes = ""
            result = True
            for d in data:
                if uri in d["URI"]:
                    attributes = d["Response"]
            if attributes:
                for i in attributes.split("\n"):
                    if "." not in i:
                        if i not in response:
                            result = False
                    else:
                        nested_data = get_val_from_str(i, response)
                        if not nested_data:
                            result = False
            return result
        except Exception as e:
            msg = {
                "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                "TestName": self.current_test_name,
                "Message": "FATAL: Exception occurred while reading the config file. Please see below exception",
                "Exception": str(e)
            }
            self.test_info_logger.write(json.dumps(msg))
            
    
    def is_debug_mode(self) -> bool:
        """
        Typically shouldn't be necessary. Log messages of LogSeverity.DEBUG are filtered.
        So they can exist in final code, and will only be visible if system debug mode is enabled.
        ex self._test_run.add_log(severity=LogSeverity.DEBUG, message=msg)
        However, this can be queried if additional functionality should occur for debug

        :return: _description_
        :rtype: _type_
        """
        return self._debugMode
    
    @property
    def is_console_log(self) -> bool:
        return self._console_log
    
    def clean_up(self):
        if self.binded_port:
            self.ssh_tunnel.kill_ssh_tunnel()
        if self.redfish_auth and self.redfish_ifc:
            self.redfish_ifc.logout()
            self.test_info_logger.log("Redfish logout is successful.")

    def check_ping_status(self, ip_address):
        p = '-n' if platform.system().lower()=='windows' else '-c'
        response = os.system(f'ping {p} 1 ' + ip_address)
        if response == 0:
            return True
        return False
        
    
    def GetSystemDetails(self, print_details=0): # FIXME: Use logging method and fix the uri
        """
        :Description:        Gets the System information from BMC.

        :returns:	         System Details & BMC Frimware Version
        :rtype:              None
        """
        try:
            MyName = __name__ + "." + self.GetSystemDetails.__qualname__
            able_to_get_system_details = True
            t = PrettyTable(["Component", "Value"])
            system_detail_uri = self.uri_builder.format_uri(redfish_str="{BaseURI}{SystemURI}", component_type="BMC")
            bmc_fw_inv_uri = self.uri_builder.format_uri(
                redfish_str="{BaseURI}{BMCFWInventory}/",component_type="BMC")
            system_details = self.run_redfish_command(system_detail_uri).dict
            bmc_fw_inv = self.run_redfish_command(bmc_fw_inv_uri).dict
            if system_details and ("error" not in system_details):
                t.add_row(["Model", system_details.get("Model")])
                t.add_row(["Manufacturer", system_details.get("Manufacturer")])
                t.add_row(["HostName", system_details.get("HostName")])
                t.add_row(["System UUID", system_details.get("UUID")])
                t.add_row(["Bios Version", system_details.get("BiosVersion")])
                t.add_row(["PartNumber", system_details.get("PartNumber")])
                t.add_row(["SerialNumber", system_details.get("SerialNumber")])
                t.add_row(["Processor Model", system_details.get("ProcessorSummary").get("Model")])
                t.add_row(
                    [
                        "Processor Health",
                        system_details.get("ProcessorSummary").get("Status").get("Health"),
                    ]
                )
                t.add_row(
                    [
                        "Processor State",
                        system_details.get("ProcessorSummary").get("Status").get("State"),
                    ]
                )
            else:
                able_to_get_system_details = False
            if "error" not in bmc_fw_inv:
                t.add_row(["BMC Version", bmc_fw_inv["Version"]])
            else:
                able_to_get_system_details = False
            if able_to_get_system_details and print_details:
                print(t)
            return [system_details, bmc_fw_inv], able_to_get_system_details
        except Exception as e:
            print("[FATAL] Exception occurred during system discovery. Please see below exception...")
            print(str(e))
            return ["[FATAL] Exception occurred during system discovery. Please see below exception...",str(e)], False
