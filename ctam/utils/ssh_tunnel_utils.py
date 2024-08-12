# Copyright (c) NVIDIA CORPORATION
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from  sshtunnel import SSHTunnelForwarder, HandlerSSHTunnelForwarderError


class SSHTunnel():
    def __init__(self, logger) -> None:
        self.test_info_logger = logger
        self.ssh_tunnel = None
        self.binded_port = None


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