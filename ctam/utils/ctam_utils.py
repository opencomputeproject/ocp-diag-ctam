import os
import re
import shlex
import subprocess
import shutil
import stat
from os import path
import tempfile
import progressbar
import time
import threading
from ocptv.output import LogSeverity

class GitUtils():
    """_summary_
    GitUtils:
        This class is based on all git operations line cloning a repo. 
        Deleting after use
        Running any script provided to run using the cloned repo.
    """

    def __init__(self) -> None:
        """_summary_
        """
        self.repo_path = ""
        self.temp_dir = tempfile.gettempdir()
        pass

    def clone_repo(self, repo_url, repo_path, branch_name="", install_requirements=True):
        """_summary_
        This method helps to clone a git repo in destination path and install all the requirements.

        Args:
            repo_url (str): Git repo url that needs to be cloned.
            repo_path (str): Path where we need to clone the repo.
            branch_name (str, optional): Branch name that will be cloned. Defaults to "".
            install_requirements (bool, optional): If true then install the requirement files. Defaults to True.

        Raises:
            Exception: If there are any error is there in stderr or the return code is not 0, Then raise exception.
            Exception: If any exception occurred during cloning the repo then raise

        Returns:
            _type_: bool
        """
        try:
            self.repo_path = os.path.join(self.temp_dir, repo_path)

            if not os.path.exists(self.repo_path):
                os.makedirs(self.repo_path)
            branch = ""
            if branch_name:
                branch = f"-b {branch_name}"
            cmd = f"git clone {branch} {repo_url} {self.repo_path}"
            print(cmd)
            result = subprocess.run(shlex.split(cmd, posix=False), capture_output=True)
            print(result)
            if result.returncode != 0 and result.stderr:
                error = result.stderr.decode("utf-8").strip()
                msg = f"Exception occurred while cloning a repo. Please see below exception...\n{error}"
                raise Exception(msg)
            if install_requirements:
                for filename in os.listdir(self.repo_path):
                    if "requirement" in filename:
                        cmd = "python -m pip install -r {} ".format(os.path.join(self.repo_path, filename))
                        res  =subprocess.run(shlex.split(cmd, posix=False))
                        # res.check_returncode()
                        if res.returncode != 0 and res.stderr:
                            error = result.stderr.decode("utf-8").strip()
                            msg = f"Exception occurred while installing python pip packages. Please see below exception...\n{error}"
                            raise Exception(msg)
            return True
        except Exception as e:
            print(e)
            return False

    def clean_repo(self, repo_path=""):
        """_summary_
        This method helps to clean the repo after cloning and running the required test cases.
        It will clean after all test cases completed.

        Args:
            repo_path (str, optional): The path where repo is cloned. Defaults to "".

        Returns:
            _type_: bool
        """
        try:
            if not repo_path:
                repo_path = self.repo_path
            
            for root, dirs, files in os.walk(self.repo_path):  
                for dir in dirs:
                    os.chmod(path.join(root, dir), stat.S_IRWXU)
                for file in files:
                    os.chmod(path.join(root, file), stat.S_IRWXU)
            shutil.rmtree(repo_path)
            return True
        except Exception as e:
            print(f"Exception occurred while cleaning up the git repo. Please remove manually...\n{str(e)}")
            return False


    def validate_redfish_service(self, file_name, connection_url, user_name, user_pass,
                                  log_path, schema_directory, depth, service_uri, *args, **kwargs):
        """_summary_
        This method helps to run the Service validator command,
        In this method we are creating the command using the method arguments.

        Args:
            file_name (str): Which file we need to run from service validator.
            connection_url (str): need top give the protocol, ip and port for running the service validator
            user_name (str): Username for the system ip
            user_pass (str): Password for the system ip
            log_path (str): The path where we need to store the logs for service validator
            schema_directory (str): The schema file directory.
            depth (str): Need to give depth for running single or across the whole redfish uri's as Tree
            service_uri (str): The URI from where it will start validation.

        Returns:
            _type_: (bool, str): return status with pass and fail msg
        """
            
        result = False
        log_path = os.path.join(log_path, file_name)
        file_name = os.path.join(self.repo_path, file_name)
        schema_directory = os.path.join(self.repo_path, "SchemaFiles")
        service_command = "python {file_name}.py --ip {ip} \
                -u {user} -p {pwd} --logdir {log_dir} \
                --schema_directory {schema_directory} \
                    --payload {depth} {uri}".format(
                        file_name=file_name,
                        ip=connection_url,
                        user=user_name,
                        pwd=user_pass,
                        log_dir=log_path,
                        schema_directory=schema_directory,
                        depth=depth,
                        uri=service_uri
                    )
                    
        status, result = self.__class__.ctam_run_dmtf_command(service_command)
        if not status:
            return status, result
        result = ''.join(result).strip()
        data = result.replace("\r", "").split("\n")[-1]
        s_idx = result.index("Elapsed time:")
        data = result[s_idx:]
        res = re.findall(r"pass:\s+(\d+)", data)
        if res and res[0].isdigit() and int(res[0]) > 0:
            return True, "PASS"
        return False, "FAIL"
    
    @classmethod
    def ctam_redfish_interop_validator(cls, file_name, connection_url, user_name, user_pass,
                                        log_path, profile, *args, **kwargs):
        """_summary_
        This method helps to run the Interop command line. It will construct the interop command using the arguments.
        If we are passing some arguments through **kwargs, then it will combine the key and value for those arguments and run the command.

        Args:
            file_name (str): File name that needs to be run from command line
            connection_url (str): The protocol, ip and port where we need to run the validation(https://127.0.0.1:1234)
            user_name (str): user name for the system ip
            user_pass (str): password for the system ip
            log_path (str): The path where we need to store the logs for Interop validator
            profile (str): The profile we need to validate against redfish interop uri
        Returns:
            _type_: (bool): returns if successfully validated or not
        """
        service_base_command = "python {file_name}.py --ip {ip} \
                -u {user} -p {pwd} --logdir {log_dir}".format(
                        file_name=file_name,
                        ip=connection_url,
                        user=user_name,
                        pwd=user_pass,
                        log_dir=log_path)
        
        service_base_command += f"".join(f" --{k} {v} " for k, v in kwargs.items())
        service_base_command += " {}".format(profile)
        status, result = cls.ctam_run_dmtf_command(service_base_command)
        if not status:
            return False
        result = ''.join(result).strip()
        data = result.replace("\r", "").split("\n")[-1]
        s_idx = result.find("Elapsed time:")
        if s_idx < 0:
            return False
        data = result[s_idx:]
        validation_msg = data.split("\n")[-1]
        if "succeeded".lower() in validation_msg.lower():
            return True, 0
        else:
            error_count = re.search(r'\d+', validation_msg).group()
            return False, int(error_count)
        
    @classmethod
    def ctam_run_dmtf_command(cls, command):
        """_summary_
        This method helps to run any command on a command prompt using subprocess. 
        After running the command it will check for any error or any issue. If there are no errors, then
        it will return the output as list with status.

        Args:
            command (str): The command we need to run through subprocess

        Raises:
            Exception: Raise exception for keyboard interrupt like ctrl+c
            Exception: Raise exception if the commad is failed or give any issue while running

        Returns:
            _type_: (bool, list): returns status and the stdout result as list
        """
        try:
            command = repr(command)[1:-1]
            with subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            # Set up a progress bar; assume you know the number of iterations (like 4 for 4 pings)
            
                def read_stream(stream, buffer):
                    for line in iter(stream.readline, ''):
                        buffer.append(line)
                    stream.close()

                stdout_lines = []
                stderr_lines = []
                stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines))
                stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines))

                # Start the threads
                stdout_thread.start()
                stderr_thread.start()
                with progressbar.ProgressBar(max_value=progressbar.UnknownLength) as pbar:
                    while True:
                        if process.poll() is not None:
                            break
                        pbar.update(1)  # Update the progress bar with each line processed
                        time.sleep(0.1)  # Simulate some delay (optional)
        except KeyboardInterrupt:
            process.terminate()  # Terminate the subprocess
            process.wait()
            print("\nProcess interrupted. Cleaning up...")
            raise Exception("[ERROR] Keyboard Interrupted...")
        except Exception as e:
            process.terminate()  # Terminate the subprocess
            process.wait()
            raise Exception(LogSeverity.INFO, "[ERROR] Exception occurred during running the command. {}".format(str(e)))
        finally:
            # Ensure the progress bar reaches 100% before finishing or stopping
            pbar.update(100)
            pbar.finish()
            stdout_thread.join()
            stderr_thread.join()

        if stderr_lines:
            print(stderr_lines)
            return False, stderr_lines
        return True, stdout_lines
    
class MetaNull(type):
    pass
