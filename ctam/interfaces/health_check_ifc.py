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
