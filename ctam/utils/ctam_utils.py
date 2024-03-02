import os
import shlex
import subprocess
import shutil
import stat
from os import path
import tempfile

from alive_progress import alive_bar

class GitUtils():

    def __init__(self) -> None:
        self.repo_path = ""
        self.temp_dir = tempfile.gettempdir()
        pass

    def clone_repo(self, repo_url, repo_path, branch_name="", install_requirements=True):
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
            
            log_path = os.path.join(log_path, file_name)
            file_name = os.path.join(self.repo_path, file_name)
            schema_directory = os.path.join(self.repo_path, "SchemaFiles")
            try:
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
                with alive_bar(0,theme="classic", stats=False) as bar:
                    result = subprocess.run(shlex.split(service_command, posix=False), capture_output=True)
                    print(result.returncode, result.stderr)
                    if result.returncode != 0 and result.stderr:
                        error = result.stderr.decode("utf-8").strip()
                        raise Exception(error)
                    bar()
                    result = result.stdout.decode("utf-8").strip()
                    # print("Res: ",result)
                    data = result.replace("\r", "").split("\n")[-1]
                    # print("Data: ", data)
                    s_idx = result.index("Elapsed time:")
                    data = result[s_idx:]
                    # print("Index: ", data)
                    import re
                    res = re.findall(r"pass:\s+(\d+)", data)
                    print("REGEX: ",res)
                    if res and res[0].isdigit() and int(res[0]) > 0:
                        # res = int(res[0])
                        # if res > 0:
                        return True
                    # if "fail" in data.lower():
                    #     msg = "Redfish ServiceVerification has failed. Please check log file for more details."
                    #     print(msg)
                    #     return False
                    return False
            except Exception as e:
                print(f"Exception Occurred: {e}")
                return False
    
class MetaNull(type):
    pass

# def show_loading_bar():
#     with alive_bar(0,theme="classic", stats=False) as bar:
#         result = subprocess.run(shlex.split(run_command), capture_output=True)
#         bar()
#         if result.stderr:
#             raise Exception(result.stderr)