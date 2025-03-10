# Copyright (c) NVIDIA CORPORATION
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from  sshtunnel import SSHTunnelForwarder, HandlerSSHTunnelForwarderError
import subprocess
import os
from abc import ABC, abstractmethod

class SSHTunnel(ABC):
    def __init__(self, logger) -> None:
        self.test_info_logger = logger
        self.ssh_tunnel = None
        self.binded_port = None

    @abstractmethod
    def create_tunnel(self, local_port, remote_host, remote_port, ssh_host, ssh_port, ssh_username, ssh_password):
        pass

    @abstractmethod
    def setup_ssh_tunnel(self, local_port, remote_host, remote_port, ssh_host, ssh_port, ssh_username, ssh_password):
        pass

    @abstractmethod
    def kill_ssh_tunnel(self):
        pass

class SSHTunnelWithLibrary(SSHTunnel):

    def create_tunnel(self, local_port, remote_host, remote_port, ssh_host, ssh_port, ssh_username, ssh_password):
        try:
            return True, SSHTunnelForwarder(
                    (ssh_host, ssh_port),
                    ssh_username=ssh_username,
                    ssh_password=ssh_password,
                    remote_bind_address=(remote_host, remote_port),
                    local_bind_address=('localhost', local_port),
                    )
        except HandlerSSHTunnelForwarderError:
            self.test_info_logger.log(f"Port {ssh_host} is already in use. Skipping..")
            return False, None
        except Exception as error:
            print(error)
            return False, None

    def setup_ssh_tunnel(self, local_port, remote_host, remote_port, ssh_host, ssh_port, ssh_username, ssh_password):
        """
        Setup SSH Tunneling to AMC

        :raises Exception: failed port forwarding/ssh tunneling
        :return: None
        :rtype: None
        """
        if self.ssh_tunnel:
            return

        if not local_port:
            raise Exception(f"Expecting list of ports to ssh tunnelling, found none!")
        self.port_list = local_port
        for port in self.port_list:
            status, self.ssh_tunnel = self.create_tunnel(local_port=port, remote_host=remote_host, remote_port=remote_port, 
                                             ssh_host=ssh_host, ssh_port=ssh_port,
                                            ssh_username=ssh_username, ssh_password=ssh_password)
            if status:
                self.binded_port = port
                self.ssh_tunnel.start()
                break
            self.test_info_logger.log(f"Failed to bind port {port}.")
        if self.binded_port is None:
            raise Exception(f"Failed to bind port! Please make sure the host machine has port forwarding enabled and there is at least one port available in {self.port_list}.")
        msg = f"SSH tunnel established at port: {self.binded_port}"
        self.test_info_logger.log(msg)
        return self.binded_port
    
    def kill_ssh_tunnel(self):
        """
        Kill SSH Tunneling to AMC

        :return: None
        :rtype: None
        """
        if self.ssh_tunnel:
            self.ssh_tunnel.close()
            self.test_info_logger.log("SSH tunnel is killed successfully!")
            self.binded_port = None


class SSHTunnelWithSshpass(SSHTunnel):

    def create_tunnel(self, local_port, remote_host, remote_port, ssh_host, ssh_port, ssh_username, ssh_password):
        ssh_cmd = "sshpass -p {ssh_password} ssh -4 -o StrictHostKeyChecking=no -fNT -L\
                {binded_port}:{amc_ip}:{remote_port} {ssh_username}@{bmc_ip} -p {ssh_port}".format(
                    ssh_password = ssh_password,
                    binded_port = local_port,
                    ssh_username = ssh_username,
                    bmc_ip = ssh_host,
                    amc_ip = remote_host,
                    ssh_port=ssh_port,
                    remote_port=remote_port
                    )
        process = subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout_data, stderr_data = process.communicate()
        return process, stderr_data

    def setup_ssh_tunnel(self, local_port, remote_host, remote_port, ssh_host,
                        ssh_port, ssh_username, ssh_password):
        """
        Setup SSH Tunneling to AMC

        :raises Exception: failed port forwarding/ssh tunneling
        :return: None
        :rtype: None
        """
        if self.ssh_tunnel:
            return

        if not local_port:
            raise Exception(f"Expecting list of ports to ssh tunnelling, found none!")
        self.port_list = local_port
        for port in self.port_list:
            process, stderr_data = self.create_tunnel(local_port=port, remote_host=remote_host, remote_port=remote_port,
                                             ssh_host=ssh_host, ssh_port=ssh_port,
                                            ssh_username=ssh_username, ssh_password=ssh_password)
            if process.returncode != 0 or stderr_data:
                msg = f"Failed to bind port {port}.\nReturnCode: {process.returncode}\nError: {stderr_data}\nTrying the next one..."
                self.test_info_logger.log(msg)
            else:
                self.binded_port = port
                self.ssh_tunnel = True
                break
        if self.binded_port is None:
            raise Exception(f"Failed to bind port! Please make sure the host machine has port forwarding enabled and there is at least one port available in {local_port}.")
        msg = f"SSH tunnel established at port: {self.binded_port}"
        self.test_info_logger.log(msg)
        return self.binded_port

    def kill_ssh_tunnel(self):
        """
        Kill SSH Tunneling to AMC

        :return: None
        :rtype: None
        """
        # First, find all the PIDs associated with the binded port
        port_pid = ["lsof", "-t", "-i", ":{0}".format(self.binded_port)] # ANother option is to add -sTCP:LISTEN
        process = subprocess.Popen(port_pid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        my_pid = os.getpid()
        for this_pid in list(filter(None, stdout.decode().strip().split('\n'))):
            # Make sure to not kill this running process
            if int(this_pid) != my_pid:
                kill_cmd = "kill {}".format(this_pid)
                process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout_data, stderr_data = process.communicate()
                if process.returncode != 0 or stderr_data:
                    msg = f"WARNING: Couldn't close the port forwarding! {kill_cmd}\nReturnCode: {process.returncode}\nError: {stderr_data}"
                    self.test_info_logger.log(msg)
                else:
                    self.test_info_logger.log("SSH tunnel is killed successfully!")
                    self.binded_port = None # Just for sanity in case of multi-threading