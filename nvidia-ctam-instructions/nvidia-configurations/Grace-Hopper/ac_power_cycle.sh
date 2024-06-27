#!/bin/bash

#################################################################################################
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Description: This script is used to control power to Raritan PDUs.​
# Usage: bash ac_power_cycle.sh -c <config_file_path> -m <power_mode> -w <power_off_wait_sec>
#
# Available power_mode options: on/off/cycle
#
# power_off_wait_sec defines how long to hold AC power off before turning AC back on, in seconds.
# This argument is optional. Default is 120 sec.
#################################################################################################

# EXIT STATUS
SUCCESS=0
INVALID_ARGS=1
MISSING_ARG=2
MISSING_CONFIG=3
FAILURE=99

function usage { 
	echo -e "USAGE: bash $(basename $0) -c <config_file_path> -m <power_mode> -w <power_off_wait_sec>\
	\npower_off_wait_sec arguement is optional. Default is 120 sec.\
	\nAvailable power_mode options: on/off/cycle";
}

function control_pdu() {
	local mode=$1
	if [[ $mode == "on" ]]; then
		pstate_value=1
	elif [[ $mode == "off" ]]; then
		pstate_value=0
	else
		echo "Invalid mode $mode passed to $0 function. Supported options: on/off"
		return $FAILURE 
	fi

	num_of_pdus=0
	num_of_success=0
	# Iterate through PDUs
	machine_name=$(jq -r '.MachineName? // empty' "$config_file")
	machine_ip=$(jq -r '.MachineIpAddress? // empty' "$config_file")
	if [[ -z $machine_name ]]; then
		echo "Failed to read machine name from config file. Make sure it is provided correctly."
		return $FAILURE
	# FIXME: WIP
	# elif [[ -z $machine_ip ]]; then
	# 	echo "Missing machine IP address. Please provide machine IP adddress in the config file so that power status can be verified."
	fi
	shopt -s lastpipe
	jq -c '.PDU[]' "$config_file" | while read pdu; do 
		((num_of_pdus++))
		# Find the outlet group for the machine_name
		pdu_ip=$(jq -r '.IPAddress? // empty' <<<"$pdu")
		username=$(jq -r '.Username? // empty' <<<"$pdu")
		password=$(jq -r '.Password? // empty' <<<"$pdu")
		if [[ -z $pdu_ip || -z $username || -z $password ]]; then
			echo -e "Failed to parse PDU details. These are the values read from config file:\
			\npdu_ip=\"$pdu_ip\", username=\"$username\", password=\"$password\""
			continue
		fi
		echo -en "\nLooking for outlet group of ${machine_name} in ${pdu_ip} ... "
		for i in {1..11}; do
			result=$(curl -skd '{"jsonrpc": "2.0", "method": "getSettings", "params": {}, "id": 42}' https://"$username":"$password"@"$pdu_ip"/model/outletgroup/$i)
			ret_code=$?
			if [[ $ret_code -eq 0 ]]; then
				name=$(jq -r '.result._ret_.name' <<<"$result" 2>/dev/null)
				if [[ ${name,,} == ${machine_name,,} ]]; then
					echo "FOUND"
					# Outlet group is found! Now switch on/off
					echo -en "\tPowering $mode pdu $pdu_ip outletgroup $i ... "
					result=$(curl -skd '{"jsonrpc": "2.0", "method": "setAllOutletPowerStates", "params": {"pstate": '"$pstate_value"'}, "id": 42}' https://"$username":"$password"@"$pdu_ip"/model/outletgroup/$i)
					ret_code=$?
					jq -e '.error?' <<<"$result" >/dev/null
					error_present=$?
					if [[ $ret_code -eq 0 && $error_present -ne 0 ]]; then
						echo "SUCCESS"
						((num_of_success++))
						
					else 
						echo "FAILED" 
						echo "Failed to power $mode pdu $pdu_ip outletgroup $i. Command response: $result" >&2
					fi
					break # Continue to next PDU
				fi
			fi
		done
		if [[ $i -gt 10 ]]; then
			echo "Failed to locate the outletgroup for PDU: $pdu_ip of machine $machine_name"
		fi
	done

	# FIXME: WIP. There is a slight delay after the command when the power status actually changes.
	# Verify the power status of the machine
	# if [[ -z $machine_ip ]]; then
	# 	echo "Missing machine IP address. Please provide machine IP adddress in the config file so that power status can be verified."
	# else
	# 	echo -en "\tVerifying machine power status..."
	# 	sleep 5
	# 	ping -c 1 $machine_ip >/dev/null
	# 	ping_return=$?
	# 	if [[ ping_return -ne $pstate_value ]]; then
	# 		echo "SUCCESS"
	# 	else
	# 		echo "FAILED"
	# 	fi
	# fi

	# Ensure all PDU controls were successful
	if [[ $num_of_success -eq $num_of_pdus ]]; then
		echo -e "\nAll $num_of_pdus PDUs powered ${mode} successfully."
		return $SUCCESS
	else
		echo -e "\nNumber of failed PDU control: $(($num_of_pdus-$num_of_success))"
		return $FAILURE
	fi
}

# Parse arguments
while getopts ":hc:m:w:" opt; do
	case $opt in
		h) usage ; exit $SUCCESS ;;
		c) config_file=$OPTARG;;
		m) mode=$OPTARG;;
		w) power_off_wait_sec=$OPTARG;;
		:) echo "Option -$opt requires an argument" >&2 ; exit $INVALID_ARGS ;;
		\?) echo "Invalid option: -$opt" >&2 ; usage ; exit $INVALID_ARGS ;;
	esac
done
shift $((OPTIND-1))

# Check arg/options sanity
if [[ -z  $config_file || -z $mode ]]; then
	echo "All options are required." >&2 ; usage ;
	exit $MISSING_ARG
fi

if [[ ! -f $config_file ]]; then
	echo "$config_file does not exist." >&2
	exit $MISSING_CONFIG
fi

if [[ -z $power_off_wait_sec  ]]; then
	power_off_wait_sec=120
fi

if [[ $mode != "on" && $mode != "off" && $mode != "cycle" ]]; then
	echo "Invalid mode! Supported modes: on/off/cycle. Provided: $mode"
	exit $INVALID_ARGS
elif [[ $mode == "cycle" ]]; then
	control_pdu "off"
	# Not checking the return code as we want to continue even if the powering off fails.
	# It is to avoid any case where 1 of 2 PDUs fails to power off and the other PDU
	# stays power off since the code did't continue to power on.
	echo -en "\nWaiting $power_off_wait_sec seconds before turning AC back on ..."
	sleep $power_off_wait_sec
	echo -e " Done."
	control_pdu "on"
elif [[ $mode == "on" ]]; then
	control_pdu "on"
else
	control_pdu "off"
fi
control_pdu_ret_code=$?
exit $control_pdu_ret_code