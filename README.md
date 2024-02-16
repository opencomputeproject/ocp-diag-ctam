# Compliance Tool for Accelerator Management

The [**OCP Test & Validation Initiative**](https://github.com/opencomputeproject/ocp-diag-core) is a collaboration between datacenter hyperscalers having the goal of standardizing aspects of the hardware validation/diagnosis space, along with providing necessary tooling to enable both diagnostic developers and executors to leverage these interfaces.

Specifically, the [ocp-diag-ctam](https://github.com/opencomputeproject/ocp-diag-ctam) tool provides acceptance testing for Accelerator Management in cloud data centers.

---

This project is part of [OCPTV](https://github.com/opencomputeproject/ocp-diag-core) and exists under the same [MIT License Agreement](https://github.com/opencomputeproject/ocp-diag-ctam/LICENSE).

## Getting Started

### Prerequisites
Before you begin, ensure you have met the following requirements:

    - Python 3.9 or higher is installed
    - Python virtualenv and pip is installed
    - Install some key libraries:
         sudo apt-get install python3-tk sshpass jq
    - Docker is installed (Skip unless you want to create a binary)    


### Setup 

1. Clone the repo,

    ```https://github.com/opencomputeproject/ocp-diag-ctam```

### Setting up the workspace

1. Sample workspace files are present inside `json_spec` directory. Modify these file as per your infra details.

1. `input` dir inside `json_spec` contains sample input file that ctam require to run

1. Create a workspace directory and copy the configuration files from `json_spec/input` directory into `workspace` dir.

   -  `.netrc` - contains bmc ipaddress, username and password
   -  `dut_config.json` - contains various params for running the test cases
   -  `package_info.json` - contains details about the firmware 
   - `redfish_uri_config.json` - redfish config file
   - `test_runner.json` - config file for test run, can be overridden by cli flags

### Flag description


| CLI Argument         | Type    | Definition |
| :---                 | :---    | :---       |
|  `-t` or `--testcase`                | string  |  Runs a single test case. Overrides test_runner.json in the workspace
|  `-test_seq` or `--testcase_sequence`                | string  |  Runs a single test case. Overrides test_runner.json in the workspace
|  `-group_seq` or `--group_sequence`                | string  |  Runs no of groups with given sequence
|  `-s` or `--Suite`                |   |   Run full ACT Suite
|  `-g` or `--group`                |   |    Run tests for a single group. Overrides test_runner.json in the workspace
|  `-d` or `--Discovery`                |   |     Path to workspace directory that contains test run files
|  `-l` or `--list`                | string  |    List all test cases. If combined with -G then list all cases of the chosen group
|  `-v` or `--version`                |   |    Lists the current version



### Running the tool locally

1. Optional: create python [virtual environment](https://docs.python.org/3/library/venv.html) and activate.
    ```
    python -m venv venv
    source ./venv/bin/activate
    ```
1. Install dependencies
    ```
    python -m pip install -r pip-requirements.txt
    ```
1. For full documentation, from `/docs` directory, run
    ```
    ./make html
    ``````
    Open `docs/build/html/index.html` for full documentation including architecture and test case details

1. To run suite,
    ```
    cd ctam
    python ctam.py -w ..\example_workspace
    ```
    Logs will be created under `example_workspace\TestRuns`
1. To list all test cases 
    ```
    cd ctam
    python ctam.py -l
    ```
1. To run a specific test case 
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -t <test case id>
    ```
    Logs will be created under `example_workspace\TestRuns`
1. To run test cases of a specifc test group
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -g <test group name>
    ```
    Logs will be created under `example_workspace\TestRuns`
1. To run test cases with sequence
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -test_seq <test case name or id> <test case name or id>
    ```
    Logs will be created under `example_workspace\TestRuns`
1. To run groups with sequence
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -group_seq <group name or id> <group name or id>
    ```
    Logs will be created under `example_workspace\TestRuns`
1. Choose test cases to run by using tags and specifying the tags to include/exclude in test_runner.json 
1. Choose test sequence in test_runner.json if you want to run it from test runner config.

### Binary

1. One file Binary executable can be created using Makefile, to create binary run following command. This will create binary and sample workspace dir inside the dist folder. 
    
    `make build_image`

1. You can run the binary the same way running the python file. Just that now python file replaced by binary executalbe. Sample command to list all test cases. 

    Note: Please move your workspace directory inside dist directory before running the binary.

    `cd dist  && ./ctam -l`

1. To clear build files, run:

    ```make clean```


## Log Files created

1. OCPTV Log file - All logs in OCPTV defined logging format. 
1. Test_Score_<>.json - All test cases result + Final score. 
1. Test_Report_<>.log - Tabulated report of test run
1. Test_Info_<>.json - Optional log file used by test interfaces (for debug)
1. RedfishCommandDetails/RedfishCommandDetails_<Test_ID>_ <Test_Name>_<>.json - Redfish Commands used & return values (for debug)

## Test Runner Knobs
Test runner knobs can be modified in `test_runner.json` to enable different logging mode.

| Variable           | Type    | Definition |
| :---               | :---    | :---       |
| `debug_mode`               | boolean  | For debug logs
| `console_mode`               | boolean  | For console logs
| `progress_bar`               | boolean  | For for progress bar indicator

## Tags

### 1. Group Tag

- We can give tags at group level also.
- If we provide any tag to a particular group, then all the test case under that group will be considered as the same tag.
- If we run according to group tag, then all the test case will run under the group irrespective of the test case tag. 

### 2. Test Case Tags
- We can assign different tags to different test cases.
- If we run according to test case tag, then all the test cases which assigned with that tag would run irrespective of group tags.

**Note: - Tags = Group Tags Union Test Case Tags
group tags = ["G1"] and test case tags = ["L1"], so the final tags will be ["G1", "L1"]**

## Developer notes
### VS Code

`VS Code` is not required for development, however it does have workspace configurations to assist in development.

To use `VS Code`, open the `ctam.code-workspace` file.

In lieu of `VS Code` usage, the following items should be configured for other editors or the developer should perform
steps manually to ensure the consistency of the code base.

- automatic file formatting using python black formatter on file save.
    - "--line-length", "120"
- Indent set to 4 spaces
- Auto docstring configured for sphinx, type 3 double quotes below python class or function and the documentation header is automatically stubbed out.
- Automatic mypy checking of code
- Spell checking
- Useful git extensions
- Useful debugger configurations defined in launch.json, extensible
- Useful Code snippets to jump start new test development
    - Snippets for interfaces, test groups and test cases simplify new tests.
    - easy replace of TODO in the snippet creates runnable test case quickly.

## Upcoming changes 

- More test cases
- Logging improvements
- Ability to set test sequence
- PLDM validator, and auto creation of PLDM bundles with error injection.

### Contact

Feel free to start a new [discussion](https://github.com/opencomputeproject/ocp-diag-ctam/discussions), or otherwise post an [issue/request](https://github.com/opencomputeproject/ocp-diag-ctam/issues).

An email contact is also available at: ocp-test-validation@OCP-All.groups.io

