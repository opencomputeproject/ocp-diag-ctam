"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
import json
from enum import Enum


class UriBuilder:
    """
    Due to varying architectures,  not all redfish paths will be exactly the same in all cases.
    Rather than distribute those variations across the system, this class localizes the changes here.
    See 'format_uri' documentation below for specifics
    """

    def __init__(self, redfish_uri_config):
        """
        Read in dut json data

        :param dut_info: json data from dut_info.json
        :type dut_info: json data
        :raises Exception: on invalid data set
        """

        """
        Following are the variables for substitution in redfish strings.
        Note at a minimum, if the variable is in the incoming string, it will be replaced with "/"
        Therefore incoming strings must take this into account.

        """
        self.redfish_uri_config = redfish_uri_config

    def format_uri(self, redfish_str: str, component_type: str) -> str:
        """
        This method substitutes uri variables with values configured for the particular system under test.
        The available variables are listed in redfish_uri_variables above.  Note the variable substitutes will
        always have a trailing forward slash '/'.  Therefore, the incoming strings must take this into account.

        For example:
        uri_builder.format_uri("{gpu_prefix}redfish/v1/")

        If there is no prefix for this DUT,   "/redfish/v1/" will be returned.

        :param redfish_str: incoming unformatted string
        :type redfish_str: str
        :return: formatted string
        :rtype: str
        """
        uri = redfish_str.format(**self.redfish_uri_config.get(component_type, {}))
        # print("URL: {}".format(uri))
        return uri
