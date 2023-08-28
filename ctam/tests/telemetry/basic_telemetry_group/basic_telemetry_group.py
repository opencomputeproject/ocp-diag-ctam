"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
from typing import Optional, List
from tests.test_group import TestGroup
from interfaces.telemetry_ifc import TelemetryIfc


class BasicTelemetryTestGroup(TestGroup):
    """
    Checks basic status of the dut

    :param TestGroup: super class for all test groups
    :type TestGroup:
    """

    tags: List[str] = []
    group_id : str = "GT1"
    # exclude_tags: List[str] = []

    def __init__(self):
        """
        The test environment uses an auto discovery search and will instantiate all test groups and assign all of the
        group test cases to self.test_list[]   Since not all groups will be run, keep this init function minimal. Use
        configure_interfaces for most initialization
        """
        super().__init__()

    def configure_interfaces(self, tele_ifc: TelemetryIfc):
        """
        See description for __init__() above. The framework uses lazy initialization.  This interfaces for this
        function are only instantiated if there are any test cases in this group that will be executed.
        """
        self.telemetry_ifc = tele_ifc

    def setup(self):
        """
        configure common environment state for all test cases in this group
        """
        # call super first
        super().setup()

        # add custom setup here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  setup()...")
        with step1.scope():
            pass

    def teardown(self):
        """
        undo environment state change from setup(), this function is called even if test cases fail or raise exception
        """
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            pass

        # call super teardown last
        super().teardown()
