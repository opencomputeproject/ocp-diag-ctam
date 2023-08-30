"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc

from ocptv.output import LogSeverity


class HealthCheckIfc(FunctionalIfc):
    """
    API's related to general health check of the dut
    """

    _instance: Optional["HealthCheckIfc"] = None

    def __init__(self):
        super().__init__()
        self.logservice_uri_list = []
        self.entries_uri_list = []
        self.eventlog_uri_list = []
        self.dumplog_uri_list = []
        self.journal_uri_list = []

    def __new__(cls, *args, **kwargs):
        """
        ensure only 1 instance can be created

        :return: instance
        :rtype: HealthCheckIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = super(HealthCheckIfc, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def get_instance(cls, *args, **kwargs):
        """
        if there is an existing instance, return it, otherwise create the singleton instance and return it

        :return: instance
        :rtype: HealthCheckIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = cls(*args, **kwargs)
        return cls._instance
    
    def ctam_get_logservice_uris(self):
        if self.logservice_uri_list == []:
            self.ctam_redfish_uri_deep_hunt(
                "/redfish/v1/Systems", "LogServices", self.logservice_uri_list
            )
            self.ctam_redfish_uri_deep_hunt(
                "/redfish/v1/Managers", "LogServices", self.logservice_uri_list
            )
            self.ctam_redfish_uri_deep_hunt(
                "/redfish/v1/Chassis", "LogServices", self.logservice_uri_list
            )
        self.write_test_info("{}".format(self.logservice_uri_list))
        return self.logservice_uri_list
        
    def ctam_get_logdump_uris(self):
        if self.logservice_uri_list == []:
            self.logservice_uri_list = self.ctam_get_logservice_uris()
        for uri in self.logservice_uri_list:
            self.ctam_redfish_uri_hunt(uri, "Dump", self.dumplog_uri_list)
        return self.dumplog_uri_list

    def ctam_clear_log_dump(self):
        result = True
        if self.dumplog_uri_list == []:
            self.dumplog_uri_list = self.ctam_get_logdump_uris()
            if self.dumplog_uri_list == []:
                result = False
        for dumplog_uri in self.dumplog_uri_list:
            clear_dump_uri = dumplog_uri + "/Actions/LogService.ClearLog" + " -d 0"
            print(clear_dump_uri)
            uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU")
            self.dut().run_redfish_command(uri=uri)
            # Need to check again
            # self.dut_obj.RedFishCommand(
            #     "{}{}".format(self.dut_obj.gpu_redfish_data["GPUMC"], clear_dump_uri)
            # )
        return result
