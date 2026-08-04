"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Description:        This file holds all the useful firmware package manipulators.

:Command line:       Library functions are made as generic as possible.

"""

import os
import shutil
import struct
import uuid
import zlib
import math
import random


def copy_fwpkg(golden_fwpkg_path, clear_signature=False, signature_struct_bytes=1024):
    # Make a copy of the given fwpkg
    corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
    corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
    if clear_signature:
        if not signature_struct_bytes or not isinstance(signature_struct_bytes, int):
            signature_struct_bytes = FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.seek(-signature_struct_bytes, os.SEEK_END)
                file.write(bytearray(signature_struct_bytes))
            print("Signature cleared successfully!")
        except Exception as e:
            print(f"Error in clearing the package signature: {e}")
    return corrupted_package_path


class PLDMFwpkg:
    """
    Methods related to PLDM fwpkg in general
    """

    @staticmethod
    def corrupt_package_UUID(golden_fwpkg_path):
        """
        :Description:                       Corrupt the PackageHeaderIdentifier (UUID) of the .

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.write(bytearray(16)) # UUID is 16 bytes
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

    @staticmethod
    def clear_component_metadata_in_pkg(golden_fwpkg_path, component_id=None, metadata_size=4096):
        """
        :Description:                       Clear metadata of any component in the PLDM bundle.
                                            If component_id is provided, corrupt the respective component's image.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int component_id:            ComponentIdentifier of the component image to be corrupted. Default is None.
        :param int metadata_size:           Metadata size in bytes. Default is 4096 bytes.

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)

        pldm_parser = PLDMUnpack(corrupted_package_path)
        if result := pldm_parser.parse_pldm_package():
            result = pldm_parser.corrupt_component_metadata_in_pkg(component_id, metadata_size)

        if not result:
            print(f"Error in corrupting the package.")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

    @staticmethod
    def corrupt_component_image_in_pkg(golden_fwpkg_path, component_id=None, metadata_size=4096,
                                       has_signature=False, singature_struct_bytes=1024):
        """
        :Description:                       Corrupt image/payload of any component in the PLDM bundle.
                                            If component_id is provided, corrupt the respective component's image.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int component_id:            ComponentIdentifier of the component image to be corrupted. Default is None.
        :param int metadata_size:           Metadata size in bytes. Default is 4096 bytes.

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path, has_signature, singature_struct_bytes)

        pldm_parser = PLDMUnpack(corrupted_package_path)
        if result := pldm_parser.parse_pldm_package():
            result = pldm_parser.corrupt_component_image_in_pkg(component_id, metadata_size)
        if not result:
            print(f"Error in corrupting the package..")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

    @staticmethod
    def clear_component_image_in_pkg(golden_fwpkg_path, component_id=None):
        """
        :Description:                       Clear image/payload of any component in the PLDM bundle.
                                            If component_id is provided, corrupt the respective component's image.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int component_id:            ComponentIdentifier of the component image to be corrupted. Default is None.

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)

        pldm_parser = PLDMUnpack(corrupted_package_path)
        if result := pldm_parser.parse_pldm_package():
            # Once unpacked, clear metadata of any component
            result = pldm_parser.clear_component_image_in_pkg(component_id)
        if not result:
            print(f"Error in corrupting the package.")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

    @staticmethod
    def make_large_package(golden_fwpkg_path, max_bundle_size):
        """
        :Description:                       Create a package that is larger than the allowed max size.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int max_bundle_size:         Maximum allowed size of the PLDM bundle.

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)

        with open(golden_fwpkg_path, 'rb') as infile:
            golden_fwpkg_content = infile.read()
        golden_fwpkg_size = os.path.getsize(golden_fwpkg_path)
        try:
            with open(corrupted_package_path, 'w+b') as large_fwpkg:
                for i in range(max_bundle_size//golden_fwpkg_size+1):
                    large_fwpkg.write(golden_fwpkg_content)
        except Exception as e:
            print(f"Error in creating a large package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

    @staticmethod
    def corrupt_device_record_uuid_in_pkg(golden_fwpkg_path, has_signature=False, singature_struct_bytes=None):
        """
        :Description:                       Corrupt UUID of all devices in the FirmwareDeviceIDRecords section

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path, has_signature, singature_struct_bytes)

        pldm_parser = PLDMUnpack(corrupted_package_path)
        result = pldm_parser.corrupt_device_record_uuid_in_pkg()
        if not result:
            print(f"Error in corrupting the package.")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path


class FwpkgSignature:
    """
    Methods related to PLDM fwpkg signature
    """
    PKG_SIGNATURE_STRUCT_BYTES = 1024
    HeaderV2 = 2
    HeaderV3 = 3

    @staticmethod
    def get_major_minor_version_of_package_signature(package_path):
        """
        :Description:                       Get the major and minor version of the FW Update Package Signature Format.

        :param str fwpkg_path:      	    Path to firmware package

        :returns:                           The major and minor versions extracted from the package. (-1, -1) in case of failure.
        :rtype:                             Tuple[int, int]
        """
        try:
            with open(package_path, 'rb') as infile:
                infile.seek(-FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES, os.SEEK_END)
                infile.seek(4, 1)
                major_version = infile.read(1)
                minor_version = infile.read(1)

            return ord(major_version), ord(minor_version)
        except:
            return -1, -1

    @staticmethod
    def corrupt_single_byte_in_package_signature(fwpkg_path, skip_byte, value):
        """
        :Description:                       Corrupt a given single byte in the given FW package.

        :param str fwpkg_path:      	    Path to firmware package to be corrupted
        :param int skip_byte:               The offset of the byte to be corrupted from the start of signature header
        :param int value:                   The new value of the byte to be written

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        try:
            with open(fwpkg_path, 'r+b') as file:
                file.seek(-FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES + skip_byte, os.SEEK_END)
                file.write(bytes([value]))
            return True
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            return False

    @staticmethod
    def corrupt_signature_type_in_package(golden_fwpkg_path):
        """
        :Description:                       Corrupts the signature type in the FW package,
                                            which is present at 14th byte from the start of signature header.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        major_package_version, _ = FwpkgSignature.get_major_minor_version_of_package_signature(golden_fwpkg_path)
        if int(major_package_version) not in [FwpkgSignature.HeaderV2, FwpkgSignature.HeaderV3]:
            print(
                f"Package Major Version is not supported: {major_package_version}"
            )
            return None

        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)

        if not FwpkgSignature.corrupt_single_byte_in_package_signature(corrupted_package_path, 13, 255):
            print("Failed to corrupt the signature type")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
        return corrupted_package_path

    @staticmethod
    def invalidate_signature_in_pkg(golden_fwpkg_path):
        """
        :Description:                       Corrupts the magic number in the FW package,
                                            which is present at 14th byte from the start of signature header.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.seek(-FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES, os.SEEK_END)
                file.write(bytearray(4)) # 4 bytes long Magic
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
        return corrupted_package_path

    @staticmethod
    def clear_entire_signature_in_pkg(golden_fwpkg_path):
        """
        :Description:                       Clear the signature data appended at the end of
                                            the PLDM bundle.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.seek(-FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES, os.SEEK_END)
                file.write(bytearray(FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES))
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

    @staticmethod
    def clear_signature_in_pkg(golden_fwpkg_path):
        """
        :Description:                       Clear the signature field in the PLDM bundle signature.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails.
        :rtype:                             str
        """
        major_package_version, _ = FwpkgSignature.get_major_minor_version_of_package_signature(golden_fwpkg_path)
        if int(major_package_version) not in [FwpkgSignature.HeaderV2, FwpkgSignature.HeaderV3]:
            print(
                f"Package Major Version is not supported: {major_package_version}"
            )
            return None

        corrupted_package_path = copy_fwpkg(golden_fwpkg_path)
        try:
            with open(corrupted_package_path, 'r+b') as file:
                signature_offset_index = 7 # Magic number is at index 0
                file.seek(-FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES + signature_offset_index, os.SEEK_END)
                signature_offset = int.from_bytes(file.read(2),
                                                 byteorder='big',
                                                 signed=False) # Offset to Signature is UINT16
                file.seek(-FwpkgSignature.PKG_SIGNATURE_STRUCT_BYTES+signature_offset, os.SEEK_END) # Move to signature size index
                signature_size = int.from_bytes(file.read(2),
                                                 byteorder='big',
                                                 signed=False) # Signature Size  is UINT16
                file.write(bytearray(signature_size))
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

class PLDMUnpack:
    """
    PLDMUnpack class implements a PLDM parser and the unpack tool
    along with its required features.
    """
    def __init__(self, package_name: str):
        """
        Contructor for PLDMUnpack class
        """
        self.unpack = True
        self.package = package_name
        self.fwpkg_fd = 0
        self.header_map = {}
        self.device_id_record_count = 0
        self.fd_id_record_list = []
        self.component_img_info_list = []
        self.full_header = {
            "PackageHeaderInformation": {},
            "FirmwareDeviceIdentificationArea": {},
            "ComponentImageInformationArea": {},
            "Package Header Checksum": ''
        }
        self.verbose = False
        self.little_endian_list = [
            "IANA Enterprise ID", "PCI Vendor ID", "PCI Device ID",
            "PCI Subsystem Vendor ID", "PCI Subsystem ID"
        ]

    def parse_header(self):
        """
        :Description:                       Parse PLDM header data into self.header_map

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        # check if UUID is valid (support PLDM v1.0 through v1.3)
        pldm_fw_header_id_v1_0 = b'\xf0\x18\x87\x8c\xcb\x7d\x49\x43\x98\x00\xa0\x2f\x05\x9a\xca\x02'
        pldm_fw_header_id_v1_1 = b'\x12\x44\xd2\x64\x8d\x7d\x47\x18\xa0\x30\xfc\x8a\x56\x58\x7d\x5a'
        pldm_fw_header_id_v1_2 = b'\x31\x19\xce\x2f\xe8\x0a\x4a\x99\xaf\x6d\x46\xf8\xb1\x21\xf6\xbf'
        pldm_fw_header_id_v1_3 = b'\x7b\x29\x1c\x99\x6d\xb6\x42\x08\x80\x1b\x02\x02\x6e\x46\x3c\x78'
        valid_uuids = {
            str(uuid.UUID(bytes=pldm_fw_header_id_v1_0)): "1.0",
            str(uuid.UUID(bytes=pldm_fw_header_id_v1_1)): "1.1",
            str(uuid.UUID(bytes=pldm_fw_header_id_v1_2)): "1.2",
            str(uuid.UUID(bytes=pldm_fw_header_id_v1_3)): "1.3",
        }
        try:
            self.header_map["PackageHeaderIdentifier"] = str(
                uuid.UUID(bytes=self.fwpkg_fd.read(16)))
        except ValueError:
            print("Error: incorrect package format.")
            return False
        if self.header_map["PackageHeaderIdentifier"] not in valid_uuids:
            log_msg = "Expected PLDM v1.0/v1.1/v1.2/v1.3 but PackageHeaderIdentifier is "\
            + self.header_map["PackageHeaderIdentifier"]
            print(log_msg)
            return False
        self.header_map["PackageHeaderFormatVersion"] = str(
            int.from_bytes(self.fwpkg_fd.read(1),
                           byteorder='little',
                           signed=False))
        self.header_map["PackageHeaderSize"] = int.from_bytes(
            self.fwpkg_fd.read(2), byteorder='little', signed=False)
        timestamp = self.fwpkg_fd.read(13)
        self.header_map["PackageReleaseDateTime"] = get_timestamp_str(
            timestamp)
        self.header_map["ComponentBitmapBitLength"] = int.from_bytes(
            self.fwpkg_fd.read(2), byteorder='little', signed=False)
        self.header_map["PackageVersionStringType"] = int.from_bytes(
            self.fwpkg_fd.read(1), byteorder='little', signed=False)
        version_str_len = int.from_bytes(self.fwpkg_fd.read(1),
                                         byteorder='little',
                                         signed=False)
        self.header_map["PackageVersionStringLength"] = version_str_len
        self.header_map["PackageVersionString"] = self.fwpkg_fd.read(
            version_str_len).split(b'\x00')[0].decode('utf-8')
        self.full_header["PackageHeaderInformation"] = self.header_map
        return True

    def parse_device_id_records(self):
        """
        :Description:                       Parse PLDM FirmwareDeviceIDRecords data into self.fd_id_record_list

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        # pylint: disable=line-too-long
        self.device_id_record_count = int.from_bytes(self.fwpkg_fd.read(1),
                                                     byteorder='little',
                                                     signed=False)
        for _ in range(self.device_id_record_count):
            id_record_map = {}
            id_record_map["RecordLength"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            id_record_map["DescriptorCount"] = int.from_bytes(
                self.fwpkg_fd.read(1), byteorder='little', signed=False)
            id_record_map["DeviceUpdateOptionFlags"] = int.from_bytes(
                self.fwpkg_fd.read(4), byteorder='little', signed=False)
            id_record_map[
                "ComponentImageSetVersionStringType"] = int.from_bytes(
                    self.fwpkg_fd.read(1), byteorder='little', signed=False)
            id_record_map[
                "ComponentImageSetVersionStringLength"] = int.from_bytes(
                    self.fwpkg_fd.read(1), byteorder='little', signed=False)
            id_record_map["FirmwareDevicePackageDataLength"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            if int(self.header_map.get("PackageHeaderFormatVersion", "0")) >= 4:
                id_record_map["ReferenceManifestLength"] = int.from_bytes(
                    self.fwpkg_fd.read(4), byteorder='little', signed=False)
            applicable_component_size = math.ceil(
                self.header_map["ComponentBitmapBitLength"] / 8)
            id_record_map["ApplicableComponents"] = int.from_bytes(
                self.fwpkg_fd.read(applicable_component_size),
                byteorder='little',
                signed=False)
            id_record_map[
                "ComponentImageSetVersionString"] = self.fwpkg_fd.read(
                    id_record_map["ComponentImageSetVersionStringLength"]
                ).split(b'\x00')[0].decode('utf-8')
            descriptors = []
            for j in range(id_record_map["DescriptorCount"]):
                descriptor_map = {}
                if j == 0:
                    descriptor_map["InitialDescriptorType"] = int.from_bytes(
                        self.fwpkg_fd.read(2),
                        byteorder='little',
                        signed=False)
                    descriptor_map["InitialDescriptorLength"] = int.from_bytes(
                        self.fwpkg_fd.read(2),
                        byteorder='little',
                        signed=False)
                    value = self.fwpkg_fd.read(
                        descriptor_map["InitialDescriptorLength"])
                    descriptor_map["InitialDescriptorData"] = value

                else:
                    descriptor_map[
                        "AdditionalDescriptorType"] = int.from_bytes(
                            self.fwpkg_fd.read(2),
                            byteorder='little',
                            signed=False)
                    descriptor_map[
                        "AdditionalDescriptorLength"] = int.from_bytes(
                            self.fwpkg_fd.read(2),
                            byteorder='little',
                            signed=False)
                    if descriptor_map["AdditionalDescriptorType"] == 0xFFFF:
                        descriptor_map[
                            "VendorDefinedDescriptorTitleStringType"] = int.from_bytes(
                                self.fwpkg_fd.read(1),
                                byteorder='little',
                                signed=False)
                        descriptor_map[
                            "VendorDefinedDescriptorTitleStringLength"] = int.from_bytes(
                                self.fwpkg_fd.read(1),
                                byteorder='little',
                                signed=False)
                        descriptor_map[
                            "VendorDefinedDescriptorTitleString"] = self.fwpkg_fd.read(
                                descriptor_map[
                                    "VendorDefinedDescriptorTitleStringLength"]
                            ).decode('utf-8')
                        vendor_def_data_len = (
                            descriptor_map["AdditionalDescriptorLength"] -
                            (2 + descriptor_map[
                                "VendorDefinedDescriptorTitleStringLength"]))
                        descriptor_map[
                            "VendorDefinedDescriptorData"] = self.fwpkg_fd.read(
                                vendor_def_data_len).hex()
                    else:
                        descriptor_map[
                            "AdditionalDescriptorIdentifierData"] = self.fwpkg_fd.read(
                                descriptor_map["AdditionalDescriptorLength"])
                descriptors.append(descriptor_map)
            id_record_map["RecordDescriptors"] = descriptors
            id_record_map["FirmwareDevicePackageData"] = self.fwpkg_fd.read(
                id_record_map["FirmwareDevicePackageDataLength"]).decode(
                    'utf-8')
            if "ReferenceManifestLength" in id_record_map and id_record_map["ReferenceManifestLength"] > 0:
                self.fwpkg_fd.read(id_record_map["ReferenceManifestLength"])
            self.fd_id_record_list.append(id_record_map)
        self.full_header["FirmwareDeviceIdentificationArea"] = {
            "DeviceIDRecordCount": self.device_id_record_count,
            "FirmwareDeviceIDRecords": self.fd_id_record_list
        }
        return True

    def parse_downstream_device_identification_area(self):
        """
        :Description:                       Parse PLDM DownstreamDeviceIdentificationArea (v1.3+)

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        downstream_device_id_record_count = int.from_bytes(
            self.fwpkg_fd.read(1), byteorder='little', signed=False)
        self.full_header["DownstreamDeviceIdentificationArea"] = {
            "DownstreamDeviceIDRecordCount": downstream_device_id_record_count
        }
        return True

    def parse_component_img_info(self):
        """
        :Description:                       Parse PLDM Component Image info data into self.fd_id_record_list

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        component_image_count = int.from_bytes(self.fwpkg_fd.read(2),
                                               byteorder='little',
                                               signed=False)
        for _ in range(component_image_count):
            comp_info = {}
            comp_info["ComponentClassification"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            comp_info["ComponentIdentifier"] = hex(
                int.from_bytes(self.fwpkg_fd.read(2),
                               byteorder='little',
                               signed=False))
            comp_info["ComponentComparisonStamp"] = int.from_bytes(
                self.fwpkg_fd.read(4), byteorder='little', signed=False)
            comp_info["ComponentOptions"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            comp_info["RequestedComponentActivationMethod"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            # RequestedComponentActivationMethod can have any combination of bits 0:5 set
            # Any value above 0x3F is invalid
            activation_val = comp_info["RequestedComponentActivationMethod"]
            if activation_val > 0x3F:
                print(f"Found invalid value for RequestedComponentActivationMethod={activation_val}")
            comp_info["ComponentLocationOffset"] = int.from_bytes(
                self.fwpkg_fd.read(4), byteorder='little', signed=False)
            comp_info["ComponentSize"] = int.from_bytes(self.fwpkg_fd.read(4),
                                                        byteorder='little',
                                                        signed=False)
            comp_info["ComponentVersionStringType"] = int.from_bytes(
                self.fwpkg_fd.read(1), byteorder='little', signed=False)
            comp_info["ComponentVersionStringLength"] = int.from_bytes(
                self.fwpkg_fd.read(1), byteorder='little', signed=False)
            comp_info["ComponentVersionString"] = self.fwpkg_fd.read(
                comp_info["ComponentVersionStringLength"]).split(b'\x00')[0].decode('utf-8')
            if int(self.header_map.get("PackageHeaderFormatVersion", "0")) >= 3:
                comp_info["ComponentOpaqueDataLength"] = int.from_bytes(
                    self.fwpkg_fd.read(4), byteorder='little', signed=False)
                if comp_info["ComponentOpaqueDataLength"] > 0:
                    comp_info["ComponentOpaqueData"] = self.fwpkg_fd.read(
                        comp_info["ComponentOpaqueDataLength"]).hex()
            self.component_img_info_list.append(comp_info)
        self.full_header["ComponentImageInformationArea"] = {
            "ComponentImageCount": component_image_count,
            "ComponentImageInformation": self.component_img_info_list
        }
        return True

    def get_pldm_header_checksum(self):
        """
        :Description:                       Read PLDM header checksum

        :returns:                           None
        :rtype:                             None
        """
        self.full_header['Package Header Checksum'] = int.from_bytes(
            self.fwpkg_fd.read(4), byteorder='little', signed=False)

    def parse_pldm_package(self):
        """
        :Description:                       Parse the PLDM package and get information about components included in the FW image.

        :param str package_name:	        Path to the firmware package to be parsed

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        try:
            with open(self.package, "rb") as self.fwpkg_fd:
                parsing_valid = self.parse_header()
                if parsing_valid:
                    parsing_valid = self.parse_device_id_records()
                if parsing_valid and int(self.header_map.get("PackageHeaderFormatVersion", "0")) >= 4:
                    parsing_valid = self.parse_downstream_device_identification_area()
                if parsing_valid:
                    parsing_valid = self.parse_component_img_info()
                    self.get_pldm_header_checksum()
            return parsing_valid
        except IOError as e_io_error:
            log_message = f"Couldn't open or read given FW package ({e_io_error})"
            print(log_message)
            return False

    def corrupt_component_metadata_in_pkg(self, component_id=None, metadata_size=4096):
        """
        :Description:                       Corrupt a component's metadata in the given FW package.
                                            If component_id is provided, corrupt the respective component's image.
                                            Otherwise, corrupt the first component image in the package.

        :param int component_id:            ComponentIdentifier (in hex format) of the component image to be corrupted. Default is None.
        :param int metadata_size:           Metadata size in bytes. Default is 4096 bytes.

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        corruption_status = False
        package_size = os.path.getsize(self.package)
        for index, info in enumerate(self.component_img_info_list):
            if component_id is not None and info["ComponentIdentifier"] != hex(int(component_id, 16)):
                continue
            offset = info["ComponentLocationOffset"]
            size = info["ComponentSize"]
            if offset + size > package_size:
                log_msg = f"Error: ComponentLocationOffset {offset} + \
                ComponentSize {size} exceeds given package size {package_size}"
                print(log_msg)
            print(f"Corrupting metadata of component: {self.component_img_info_list[index]}")
            try:
                with open(self.package, 'r+b') as self.fwpkg_fd:
                    self.fwpkg_fd.seek(offset)
                    self.fwpkg_fd.write(bytearray(metadata_size))
                corruption_status = True
                break  # corrupt only the first matching component
            except IOError as e_io_error:
                log_message = f"Couldn't open or read given FW package ({e_io_error})"
                print(log_message)

        # For PLDM v1.3 (format revision 4+): update the NVIDIA payload CRC32 after
        # zeroing the metadata bytes so the HMC accepts the package at the package-level
        # check and proceeds to per-component validation (which is what F26 tests).
        if corruption_status:
            self._update_nvidia_payload_checksum_v1_3()

        return corruption_status

    def corrupt_component_image_in_pkg(self, component_id=None, metadata_size=4096):
        """
        :Description:                       Corrupt a component's image/payload in the given FW package.
                                            If component_id is provided, corrupt the respective component's image.
                                            Otherwise, corrupt the first component image in the package.

        :param int component_id:            ComponentIdentifier (in hex format) of the component image to be corrupted. Default is None.
        :param int metadata_size:           Metadata size in bytes. Default is 4096 bytes.

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        corruption_status = False
        package_size = os.path.getsize(self.package)
        for index, info in enumerate(self.component_img_info_list):
            if component_id is not None and info["ComponentIdentifier"] != hex(int(component_id, 16)):
                continue
            offset = info["ComponentLocationOffset"]
            size = info["ComponentSize"]
            if offset + size > package_size:
                log_msg = f"Error: ComponentLocationOffset {offset} + \
                ComponentSize {size} exceeds given package size {package_size}"
                print(log_msg)
            print(f"Corrupting component: {self.component_img_info_list[index]}")
            try:
                with open(self.package, 'r+b') as self.fwpkg_fd:
                    self.fwpkg_fd.seek(offset + metadata_size)
                    self.fwpkg_fd.write(bytearray(math.floor(size / 2)))
                corruption_status = True
                break  # corrupt only the first matching component
            except IOError as e_io_error:
                log_message = f"Couldn't open or read given FW package ({e_io_error})"
                print(log_message)

        # For PLDM v1.3 (format revision 4+): update the NVIDIA payload CRC32 stored in
        # the PackageHeaderChecksum field so the HMC accepts the package at the package-level
        # check and proceeds to per-component authentication (which is what F23 tests).
        if corruption_status:
            self._update_nvidia_payload_checksum_v1_3()

        return corruption_status

    def clear_component_image_in_pkg(self, component_id=None):
        """
        :Description:                       Clear a component's image/payload in the given FW package.
                                            If component_id is provided, corrupt the respective component's image.
                                            Otherwise, corrupt the first component image in the package.

        :param int component_id:            ComponentIdentifier (in hex format) of the component image to be corrupted. Default is None.

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        corruption_status = False
        package_size = os.path.getsize(self.package)
        for index, info in enumerate(self.component_img_info_list):
            if component_id is not None and info["ComponentIdentifier"] != hex(int(component_id, 16)):
                continue
            # Lseek to the component from the PLDM fwpkg
            offset = info["ComponentLocationOffset"]
            size = info["ComponentSize"]
            if offset + size > package_size:
                log_msg = f"Error: ComponentLocationOffset {offset} + \
                ComponentSize {size} exceeds given package size {package_size}"
                print(log_msg)
            print(f"Corrupting component: {self.component_img_info_list[index]}")
            try:
                with open(self.package, 'r+b') as self.fwpkg_fd:
                    self.fwpkg_fd.seek(offset)
                    # Zero out and save the bundle
                    self.fwpkg_fd.write(bytearray(size))
                corruption_status = True
                break  # corrupt only the first matching component
            except IOError as e_io_error:
                log_message = f"Couldn't open or read given FW package ({e_io_error})"
                print(log_message)

        # For PLDM v1.3 (format revision 4+): NVIDIA stores a CRC32 of all component
        # image data in the PackageHeaderChecksum field. Zeroing a component image
        # invalidates this checksum — update it so the HMC accepts the package at the
        # package-level check and then fails at the per-component level (as F55 intends).
        if corruption_status:
            self._update_nvidia_payload_checksum_v1_3()

        return corruption_status

    def _update_nvidia_payload_checksum_v1_3(self):
        """
        For PLDM v1.3 bundles (PackageHeaderFormatVersion == 4), NVIDIA repurposes
        the PackageHeaderChecksum field (last 4 bytes of the header, at offset
        PackageHeaderSize - 4) to hold a CRC32 of the entire component image payload:
            CRC32( data[PackageHeaderSize : last_component_end] )

        After modifying any component image bytes (e.g. zeroing for F55), this
        checksum must be recalculated so the HMC passes the package-level check
        and proceeds to per-component authentication — which is what F55 tests.

        For format revisions < 4 (PLDM v1.1/v1.2) this field is a standard PLDM
        header CRC and is not modified by CTAM's corruption tools.
        """
        fmt_rev = int(self.header_map.get("PackageHeaderFormatVersion", "0"))
        if fmt_rev < 4:
            return  # Not PLDM v1.3 — leave the standard header CRC untouched

        header_size = self.header_map["PackageHeaderSize"]
        checksum_offset = header_size - 4

        last_comp_end = max(
            c["ComponentLocationOffset"] + c["ComponentSize"]
            for c in self.component_img_info_list
        )

        with open(self.package, 'rb') as f:
            data = f.read()

        payload_crc = zlib.crc32(data[header_size:last_comp_end]) & 0xFFFFFFFF

        with open(self.package, 'r+b') as f:
            f.seek(checksum_offset)
            f.write(struct.pack('<I', payload_crc))

        print(f"[v1.3] Updated PackageHeaderChecksum (payload CRC32) → 0x{payload_crc:08x}")

    def corrupt_device_record_uuid_in_pkg(self):
        """
        :Description:                       Corrupt UUID of all devices in the FirmwareDeviceIDRecords section

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        corruption_status = False
        try:
            with open(self.package, 'r+b') as self.fwpkg_fd:
                parsing_valid = self.parse_header()
                if parsing_valid:
                    package_header_size = 36 +  self.header_map["PackageVersionStringLength"]
                    parsing_valid = self.parse_device_id_records()
                    if parsing_valid:
                        fmt_rev = int(self.header_map.get("PackageHeaderFormatVersion", "0"))
                        # Skip DownstreamDeviceIdentificationArea for v1.3+
                        downstream_area_size = 0
                        if fmt_rev >= 4:
                            downstream_area_size = 1  # 1 byte for DownstreamDeviceIDRecordCount (assuming 0 records)
                        device_id_fixed_fields_size = 11 if fmt_rev < 4 else 15  # v1.3 adds 4-byte ReferenceManifestLength
                        device_id_record_start_index = package_header_size + 1 # 1 byte for DeviceIDRecordCount
                        for id_record_map in self.fd_id_record_list:
                            record_descriptors_start_index = device_id_record_start_index + device_id_fixed_fields_size\
                                                            + math.ceil(self.header_map["ComponentBitmapBitLength"] / 8)\
                                                            + id_record_map["ComponentImageSetVersionStringLength"]
                            for j in range(id_record_map["DescriptorCount"]):
                                self.fwpkg_fd.seek(record_descriptors_start_index)
                                record_descriptor_type =  int.from_bytes(
                                                            self.fwpkg_fd.read(2),
                                                            byteorder='little',
                                                            signed=False)
                                record_descriptor_length = int.from_bytes(
                                                            self.fwpkg_fd.read(2),
                                                            byteorder='little',
                                                            signed=False)
                                if record_descriptor_type == 0x0002: # Descriptor Identifier Type is UUID
                                    self.fwpkg_fd.seek(record_descriptors_start_index + 4)
                                    random_uuid = bytes([random.randint(0, 255) for _ in range(record_descriptor_length)])
                                    self.fwpkg_fd.write(random_uuid)
                                    corruption_status = True
                                    break # Go to next Device Record
                                record_descriptors_start_index += (4 + record_descriptor_length)
                            device_id_record_start_index += id_record_map["RecordLength"]
        except IOError as e_io_error:
            log_message = f"Couldn't open or read given FW package ({e_io_error})"
            print(log_message)
            corruption_status = False
        return corruption_status

    def get_applicable_component_index(self, applicable_component):
        """
        Return list of indices of applicable component images from
        applicable_component index bitmap.
        """
        # number of images in the image section
        max_bits = len(self.component_img_info_list)
        indices = []
        for shift in range(max_bits):
            # for each index check if the bit at that position is set in applicable_component
            mask = 1 << shift
            result = applicable_component & mask
            if result == mask:
                indices.append(shift)
        return indices

    def decode_descriptor_data(self, desc_type_name, desc_data):
        """ Formatting for descriptor data based on endianess"""
        desc_val = ""
        if desc_type_name in self.little_endian_list:
            desc_val = get_padded_hex(desc_data)
        else:
            desc_val = "0x" + desc_data.hex()
        return desc_val

    def get_full_metadata_json(self):
        """ Decode byte value descriptors for full package metadata command """
        for device_records in self.full_header[
                'FirmwareDeviceIdentificationArea']['FirmwareDeviceIDRecords']:
            device_records[
                'ApplicableComponents'] = self.get_applicable_component_index(
                    device_records['ApplicableComponents'])
            records = device_records["RecordDescriptors"]
            descriptors = []
            if len(records) == 0:
                continue
            desc = records[0]
            desc["InitialDescriptorType"] = get_descriptor_type_name(
                records[0]["InitialDescriptorType"])
            desc["InitialDescriptorData"] = self.decode_descriptor_data(
                desc["InitialDescriptorType"], desc["InitialDescriptorData"])
            descriptors.append(desc)
            for i in range(1, len(records)):
                desc = records[i]
                desc[
                    "AdditionalDescriptorType"] = get_descriptor_type_name(
                        records[i]["AdditionalDescriptorType"])
                if desc["AdditionalDescriptorType"] == 'Vendor Defined':
                    desc["VendorDefinedDescriptorTitleString"] = records[i][
                        "VendorDefinedDescriptorTitleString"]
                    desc_data = records[i]["VendorDefinedDescriptorData"]
                    desc["VendorDefinedDescriptorData"] = '0x' + str(desc_data)
                else:
                    desc[
                        "AdditionalDescriptorIdentifierData"] = self.decode_descriptor_data(
                            desc["AdditionalDescriptorType"],
                            desc["AdditionalDescriptorIdentifierData"])
                descriptors.append(desc)
            device_records["RecordDescriptors"] = descriptors
        return self.full_header

def get_timestamp_str(timestamp):
    """
    :Description:                       Parse timestamp string from 13 byte binary data
                                        according to PLDM Base specification

    :param str timestamp:      	        Timestamp bytes to be parsed

    :returns:                           Timestamp in PLDM base spec format
    :rtype:                             str
    """
    year = timestamp[11]
    year = year << 8
    year = year | timestamp[10]
    time_str = str(year) + "-"
    time_str = time_str + str(timestamp[9])
    time_str = time_str + "-" + str(timestamp[8])
    time_str = time_str + " " + str(timestamp[7])
    time_str = time_str + ":" + str(timestamp[6])
    time_str = time_str + ":" + str(timestamp[5])
    micro_sec = timestamp[4]
    micro_sec = micro_sec << 8
    micro_sec = micro_sec | timestamp[3]
    micro_sec = micro_sec << 8
    micro_sec = micro_sec | timestamp[2]
    time_str = time_str + ":" + str(micro_sec)
    utc_offset = timestamp[1]
    utc_offset = utc_offset << 8
    utc_offset = utc_offset | timestamp[0]
    sign = "+"
    if utc_offset < 0:
        utc_offset = utc_offset * -1
        sign = "-"
    time_str = time_str + " " + sign + str(utc_offset)
    return time_str

def get_descriptor_type_name(desc_type):
    """
    Return the descriptive name for given integer descriptor type.
    """
    desc_type_dict = {
        0x0000: "PCI Vendor ID",
        0x0001: "IANA Enterprise ID",
        0x0002: "UUID",
        0x0003: "PnP Vendor ID",
        0x0004: "ACPI Vendor ID",
        0x0005: "IEEE Assigned Company ID",
        0x0006: "SCSI Vendor ID",
        0x0100: "PCI Device ID",
        0x0101: "PCI Subsystem Vendor ID",
        0x0102: "PCI Subsystem ID",
        0x0103: "PCI Revision ID",
        0x0104: "PnP Product Identifier",
        0x0105: "ACPI Product Identifier",
        0x0106: "ASCII Model Number",
        0x0107: "ASCII Model Number",
        0x0108: "SCSI Product ID",
        0x0109: "UBM Controller Device Code",
        0xffff: "Vendor Defined",
    }

    name = desc_type_dict.get(desc_type, f'{desc_type:#x}')
    return name

def get_padded_hex(byte_arr):
        """
        Get hex formatted version of a byte array padded with 0
        """
        total_len = len(byte_arr)
        hex_str = hex(
            int.from_bytes(byte_arr, byteorder='little', signed=False))[2:]
        padded_str = '0x' + hex_str.zfill(total_len * 2)
        return padded_str