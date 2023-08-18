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

    def get_software_inventory(self, expanded=False):
        """
        :Description:       Act Get Software Inventory

        :param expanded:    Expand Param

        :returns:          JSON Data after running Redfish command
        :rtype:             JSON Dict
        """

        # here are some example response attributes that can be used
        v1_str = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}", component_type="GPU"
        )
        response = self.dut().redfish_ifc.get(v1_str)
        msg = f"Response is {response.dict}"
        self.test_run().add_log(severity=LogSeverity.DEBUG, message=msg)
        # self.test_run().add_log(response.status)
        # self.test_run().add_log(response.task_location)
        # self.test_run().add_log(response.dict)

        return response.dict
    
    def ctam_redfish_uri_deep_hunt(self, URI, uri_hunt="", uri_listing=[], uri_analyzed=[]):
        """
        :Description:			CTAM Redfish URI Hunt - a recursive function to look deep till we find al instances URI
        :param URI:             The top uri under which we are searching for the uri instances (type string)
        :param uri_hunt:        URI we are hunting for (type string).
        :param uri_listing:     An array that will eventually contain a list of all URIs that house the member to hunt.

        :returns:				None
        """
        response = self.dut().redfish_ifc.get("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
        JSONData = response.dict
        if uri_hunt in JSONData:
            uri_listing.append(URI + "/" + uri_hunt)
            uri_analyzed.append(URI + "/" + uri_hunt)
            JSONData.pop(uri_hunt)
        for element in JSONData:
            # Consider the case of nested dictionary
            if type(JSONData[element]) == type(dict()) and ("@odata.id" in JSONData[element]):
                URI = JSONData[element]["@odata.id"]
                if URI not in uri_analyzed:
                    uri_analyzed.append(URI)
                    self.ctam_redfish_uri_deep_hunt(URI, uri_hunt, uri_listing, uri_analyzed)
            # Consider the case of list of dictionaries
            elif type(JSONData[element]) == type([]):
                for dictionary in JSONData[element]:
                    # Verify that it is indeed an array of dictionaries
                    if type(dictionary) == type(dict()) and ("@odata.id" in dictionary):
                        URI = dictionary["@odata.id"]
                        # print(URI)
                        if URI not in uri_analyzed:
                            uri_analyzed.append(URI)
                            self.ctam_redfish_uri_deep_hunt(URI, uri_hunt, uri_listing, uri_analyzed)

    def ctam_redfish_uri_hunt(self, URI, uri_hunt="", uri_listing=[]):
        response = self.dut().redfish_ifc.get("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
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
        # print("LogService List = {}".format(self.logservice_uri_list))
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
            self.dut().redfish_ifc.get(uri)
            # Need to check again
            # self.dut_obj.RedFishCommand(
            #     "{}{}".format(self.dut_obj.gpu_redfish_data["GPUMC"], clear_dump_uri)
            # )
        return result
