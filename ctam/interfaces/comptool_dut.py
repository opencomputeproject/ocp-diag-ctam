"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
import os
import sys
import typing as ty
import redfish
import netrc
import subprocess
import platform

from prettytable import PrettyTable
from ocptv.output import Metadata
from ocptv.output import Dut

from interfaces.uri_builder import UriBuilder


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
        self.package_config = package_config
        self.dut_config = config["properties"]
        self.redfish_uri_config = redfish_uri_config
        self.uri_builder = UriBuilder(redfish_uri_config)
        self.net_rc = net_rc
        self.cwd = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        super().__init__(id, name, metadata)
        self.connection_ip_address = config["properties"]["ConnectionIPAddress"][
            "value"
        ]
        default_prefix = config["properties"]["DefaultPrefix"]["value"]
        self.__user_name, _, self.__user_pass = self.net_rc.authenticators(
            self.connection_ip_address
        )
        
        # Set up SSH Tunneling if requested
        self.BindedPort = None
        if config["properties"].get("SshTunnel"):
            self.SshTunnel = config["properties"]["SshTunnel"]["value"]
        else:
            self.SshTunnel = False
        if self.SshTunnel:
            # Set up port forwarding
            if not config["properties"].get("AMCIPAddress") or not config["properties"]["AMCIPAddress"]["value"]:
                raise Exception("AMCIPAddress must be provided when SSHTunnel is set to True.")
            self.setup_ssh_tunnel(config["properties"]["AMCIPAddress"]["value"])
            self.connection_ip_address = "127.0.0.1:" + str(self.BindedPort) 
            self.__user_name, _, self.__user_pass = self.net_rc.authenticators(
                config["properties"]["AMCIPAddress"]["value"]
            )

        # TODO investigate storing FW update files via add_software_info() in super
        connection_url = ("http://" if self.SshTunnel else "https://") + self.connection_ip_address + "/"
        if not self.check_ping_status(self.connection_ip_address): # FIXME: Use logging method
            print("[FATAL] Unable to ping the ip address. Please check the IP is valid or not.")
            sys.exit(1)
        self.redfish_ifc = redfish.redfish_client(
            connection_url,
            username=self.__user_name,
            password=self.__user_pass,
            default_prefix=default_prefix,
        )

        # self.redfish_ifc.login(auth="basic")   #TODO investigate 'session' token auth

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
    
    def setup_ssh_tunnel(self, amc_ip_address):
        """
        Setup SSH Tunneling to AMC

        :raises Exception: failed port forwarding/ssh tunneling
        :return: None
        :rtype: None
        """
        PortList = [18888, 18889]
        for port in PortList:
            ssh_cmd = "sshpass -p {ssh_password} ssh -fNT -L {binded_port}:{amc_ip}:80 {ssh_username}@{bmc_ip} -p 22".format(
                    ssh_password = self.__user_pass,
                    binded_port = port,
                    ssh_username = self.__user_name,
                    bmc_ip = self.connection_ip_address,
                    amc_ip = amc_ip_address,
                    )
            process = subprocess.Popen(ssh_cmd, shell=True)
            process.wait()
            if process.returncode != 0 or process.stdout != None:
                print(f"Failed to bind port {port}. Trying the next one...") # FIXME: Use logging method
            else:
                self.BindedPort = port
                break
        if self.BindedPort is None:
            raise Exception("Failed to bind port! Please make sure the host machine has port forwarding enabled and there is at least one port avaailable in {PortList}.")
        print(f"Binded port {self.BindedPort}") # FIXME: Use logging method
        return
    
    def kill_ssh_tunnel(self):
        # First, find all the PIDs associated with the binded port
        port_pid = ["lsof", "-t", "-i", ":{0}".format(self.BindedPort)] # ANother option is to add -sTCP:LISTEN
        process = subprocess.Popen(port_pid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate() 
        my_pid = os.getpid()
        for this_pid in list(filter(None, stdout.decode().strip().split('\n'))):
            # Make sure to not kill this running process
            if int(this_pid) != my_pid:
                kill_cmd = "kill {}".format(this_pid)
                process = subprocess.Popen(kill_cmd, shell=True)
                process.wait()
                if process.returncode != 0 or process.stdout != None:
                    print(f"WARNING: Couldn't close the port forwarding! {kill_cmd}") # FIXME: Use logging method
                else:
                    print("SSH tunnel is killed successfully!") # FIXME: Use logging method
                    self.BindedPort = None # Just for sanity in case of multi-threading
                
    def clean_up(self):
        if self.BindedPort:
            self.kill_ssh_tunnel()

    def check_ping_status(self, ip_address):
        p = '-n' if platform.system().lower()=='windows' else '-c'
        response = os.system(f'ping {p} 1 ' + ip_address)
        if response == 0:
            return True
        else:
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
            system_detail_uri = self.uri_builder.format_uri(redfish_str="{BaseURI}{SystemURI}",
                                                                component_type="BMC")
            bmc_fw_inv_uri = self.uri_builder.format_uri(redfish_str="{BaseURI}{BMCFWInventory}/",
                                                                component_type="BMC")
            system_details = self.redfish_ifc.get(system_detail_uri).dict
            bmc_fw_inv = self.redfish_ifc.get(bmc_fw_inv_uri).dict
            if system_details and ("error" not in system_details):
                t.add_row(["Model", system_details["Model"]])
                t.add_row(["Manufacturer", system_details["Manufacturer"]])
                t.add_row(["HostName", system_details["HostName"]])
                t.add_row(["System UUID", system_details["UUID"]])
                t.add_row(["Bios Version", system_details["BiosVersion"]])
                t.add_row(["PartNumber", system_details["PartNumber"]])
                t.add_row(["SerialNumber", system_details["SerialNumber"]])
                t.add_row(["Processor Model", system_details["ProcessorSummary"]["Model"]])
                t.add_row(
                    [
                        "Processor Health",
                        system_details["ProcessorSummary"]["Status"]["Health"],
                    ]
                )
                t.add_row(
                    [
                        "Processor State",
                        system_details["ProcessorSummary"]["Status"]["State"],
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
            #    self.logger.info(t)
            return [system_details, bmc_fw_inv], able_to_get_system_details
        except Exception as e:
            print("[FATAL] Exception occurred during system discovery. Please see below exception...")
            print(str(e))
            return ["[FATAL] Exception occurred during system discovery. Please see below exception...",str(e)], False
        
