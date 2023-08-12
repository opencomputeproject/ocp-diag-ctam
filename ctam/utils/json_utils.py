"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Description:        This file holds all the useful json manipulators. 

:Command line:       Library functions are made as generic as possible.

"""
import json


# Deep searches for a key-value pair and returns the value of a key from the same dictionary set.
# Useful when the same keys are used across different members of the json.
# For eg, we can use this to get version number of a component, given the ComponentIdentifier=0xff00  .
def jsonhunt(jsondata, jsonkey, jsonvalue, jsonhuntkey):
    """
    :Description:                       Deep searches for a key-value pair and returns the value of a key from the same dictionary set.
                                        For eg, we can use this to get version number of a component, given the ComponentIdentifier=0xff00

    :param JSON Dict jsondata:		    Dict object for JSON Data
    :param str jsonkey:		            Json key
    :param str jsonvalue:		        Json Value
    :param str jsonhuntkey:		        Json Key

    :returns:                           jsonhuntvalue
    :rtype:                             JSON Dict
    """
    if type(jsondata) == type(dict()):
        # print(jsondata.keys())
        if jsonkey in jsondata.keys():
            # print("found key")
            if jsondata[jsonkey] == jsonvalue:
                # print("found value")
                return jsondata[jsonhuntkey]
        elif len(jsondata.keys()) > 0:
            for key in jsondata.keys():
                jsonhuntvalue = jsonhunt(jsondata[key], jsonkey, jsonvalue, jsonhuntkey)
                if jsonhuntvalue != None:
                    return jsonhuntvalue
    elif type(jsondata) == type([]):
        for node in jsondata:
            jsonhuntvalue = jsonhunt(node, jsonkey, jsonvalue, jsonhuntkey)
            if jsonhuntvalue != None:
                return jsonhuntvalue


# Deep searches for a key-value pair and returns a list of values of a key from the same dictionary set.
# Useful when the same keys are used across different members of the json.
# For eg, we can use this to get a list of all "id"s whose key is "updatable" and corresponding value is true
def jsonhuntall(jsondata, jsonkey, jsonvalue, jsonhuntkey, huntvalue_list):
    """
    :Description:                       Deep searches for a key-value pair and returns a list of values of a key from the same dictionary set.
                                        Useful when the same keys are used across different members of the json.

    :param JSON Dict jsondata:		    Dict object for JSON Data
    :param str jsonkey:		            Json key
    :param str jsonvalue:		        Json Value
    :param str jsonhuntkey:		        Json Key
    :param str huntvalue_list:		    List of json key

    :returns:                           None
    :rtype:                             None
    """
    if type(jsondata) == type(dict()):
        # print(jsondata.keys())
        if jsonkey in jsondata.keys():
            # print("found key")
            if jsondata[jsonkey] == jsonvalue:
                # print("found value")
                huntvalue_list.append(jsondata[jsonhuntkey])
                return
        elif len(jsondata.keys()) > 0:
            # print("digging into each key")
            for key in jsondata.keys():
                jsonhuntall(
                    jsondata[key], jsonkey, jsonvalue, jsonhuntkey, huntvalue_list
                )
    elif type(jsondata) == type([]):
        for node in jsondata:
            # print("going into each node")
            jsonhuntall(node, jsonkey, jsonvalue, jsonhuntkey, huntvalue_list)


# Returns a new json in jsonextract, by pairing the values from the two json key arguments passed assuming there are multiple instances of the two keys.
# if there is a dictionary A = {"a":"b","c":"d","e":"f"} then jsonmultihunt(A,"c","e",B) will create a dictionary B which holds {"d":"f"}.
# For eg. we can use this to build a dictionary of [ComponentIdentifier]:[Version] for all components
def jsonmultihunt(jsondata, jsonkey1, jsonkey2, jsonextract):
    """
    :Description:                       Returns a new json in jsonextract, by pairing the values from the two-
                                        json key arguments passed assuming there are multiple instances of the two keys.


    :param JSON Dict jsondata:		    Dict object for JSON Data
    :param str jsonkey1:		        Json key
    :param str jsonkey2:		        Json Value
    :param str jsonextract:		        Json Dict Object

    :returns:                           None
    :rtype:                             None
    """
    if type(jsondata) == type(dict()):
        # print(jsondata.keys())
        if jsonkey1 in jsondata.keys():
            # print("found key")
            jsonextract[jsondata[jsonkey1]] = jsondata[jsonkey2]
            # print("found value")
            return
        elif len(jsondata.keys()) > 0:
            for key in jsondata.keys():
                jsonmultihunt(jsondata[key], jsonkey1, jsonkey2, jsonextract)
    elif type(jsondata) == type([]):
        for node in jsondata:
            jsonmultihunt(node, jsonkey1, jsonkey2, jsonextract)


# Recursively parses a json data till it finds the jsonkey to return its value. jsonkey should be an exact match, by case too. The return could be a json too.
def jsondeephunt(jsondata, jsonkey):
    """
    :Description:                       Recursively parses a json data till it finds the jsonkey to return its value.
                                        jsonkey should be an exact match, by case too. The return could be a json too.


    :param JSON Dict jsondata:		    Dict object for JSON Data
    :param str jsonkey:		            Json key

    :returns:                           jsonvalue
    :rtype:                             str
    """
    jsonvalue = ""
    if type(jsondata) == type(dict()):
        if jsonkey in jsondata.keys():
            # print("key Found")
            return jsondata[jsonkey]
        elif len(jsondata.keys()) > 0:
            # print("Found Multiple Elements")
            for key in jsondata.keys():
                jsonvalue = jsondeephunt(jsondata[key], jsonkey)
                if jsonvalue != "":
                    return jsonvalue
    elif type(jsondata) == type([]):
        # print("Found Array")
        for node in jsondata:
            jsonvalue = jsondeephunt(node, jsonkey)
    return jsonvalue


# Quite often we only need the value against a member. Assumes that json file has "named" json members which have a key of interest. Returns a json dictionary with json member name : value of json key
def json_collapse(jsondata, jsonkey):
    """
    :Description:                       Quite often we only need the value against a member. Assumes that json file has "named" json members which have a key of interest.
                                        Returns a json dictionary with json member name : value of json key


    :param JSON Dict jsondata:		    Dict object for JSON Data
    :param str jsonkey:		            Json key

    :returns:                           collapsed_json
    :rtype:                             JSON Dict
    """
    collapsed_json = {}
    for json_member in jsondata.keys():
        collapsed_json[str(json_member)] = jsondata[json_member][jsonkey]
    return collapsed_json


def dump_cmd_result(
    file_path, file_name, cmd, json_data, curr_test, curr_test_id, status_code
):
    """
    :Description:                      Dump JSON Dict object into file


    :param str file_path:		        JSON file location
    :param str file_name:		        JSON file name
    :param str cmd:		                Command line
    :param str json_data:		        JSON Dict Data
    :param str curr_test:		        Current Test name
    :param str curr_test_id:		    Current Test ID

    :returns:                           None
    :rtype:                             NOne
    """
    res = {}
    res["command"] = cmd
    res["test_name"] = curr_test
    res["test_id"] = curr_test_id
    res["status_code"] = status_code
    res["Result"] = json_data
    with open(get_path(file_path, file_name), "a") as f:
        json.dump(res, f, indent=4)
        f.write("\n")


def get_redfish_hardcodes(file_path, type="GPU"):
    with open(file_path, "r") as f:
        json_data = json.load(f)
    return json_data.get(type, {}) if json_data else {}


import os


def get_path(*args):
    print("Paths are : {}".format(args))
    path = os.path.join("", *args)
    return path
