# 🚀 Project Name
   <pre> 
   ██████╗  ████████╗   █████╗   ███╗   ███╗
  ██╔════╝  ╚══██╔══╝  ██╔══██╗  ████╗ ████║
  ██║          ██║     ███████║  ██╔████╔██║
  ██║          ██║     ██╔══██║  ██║╚██╔╝██║
  ╚██████╗     ██║     ██║  ██║  ██║ ╚═╝ ██║
   ╚═════╝     ╚═╝     ╚═╝  ╚═╝  ╚═╝     ╚═╝
  
   <b>Ｃｏｍｐｌｉａｎｃｅ - Ｔｏｏｌ - ｆｏｒ - Ａｃｃｅｌｅｒａｔｏｒ - Ｍａｎａｇｅｍｅｎｔ </b> </pre>
   
## 📌 Description
# Compliance Tool for Accelerator Management

The [**OCP Test & Validation Initiative**](https://github.com/opencomputeproject/ocp-diag-core) is a collaboration between datacenter hyperscalers having the goal of standardizing aspects of the hardware validation/diagnosis space, along with providing necessary tooling to enable both diagnostic developers and executors to leverage these interfaces.

Specifically, the [ocp-diag-ctam](https://github.com/opencomputeproject/ocp-diag-ctam) tool provides acceptance testing for Accelerator Management in cloud data centers.

---

This project is part of [OCPTV](https://github.com/opencomputeproject/ocp-diag-core) and exists under the same [MIT License Agreement](https://github.com/opencomputeproject/ocp-diag-ctam/LICENSE).

## 🚀 Getting Started

To help users quickly understand and navigate through the CTAM repository, the following documents provide detailed guidance:

1. **CTAM Onboarding Document**
	- This document serves as a guide for users to set up and get started with the CTAM tool.
	- [CTAM Onboarding Document](<CTAM_REPO_PATH>/ocp-diag-ctam/docs/CTAM - OnBoarding Document.docx)

2. **CTAM Detailed Documentation**
    - Refer for detailed documentation setup [Sphinx Documentation](#sphinx-documentation)
    - Once setup is done, [View Documentation](<CTAM_REPO_PATH>/ocp-diag-ctam/docs/build/html/index.html)
    - This is the complete technical documentation for CTAM. It contains architecture details, test scenarios, and more.
    - Use the search bar for finding the detailed documentation of CTAM testcases.

3. **CTAM for Internal Testing & Validation**
    - This helps users to repurpose the CTAM Framework to run additional scenarios which are not a part of the compliance specification.
	- [CTAM Internal Testing Feature](<CTAM_REPO_PATH>/ocp-diag-ctam/docs/CTAM Internal Testing Feature.docx)



## 🛠️ Installation
### **Prerequisites**
```
Before you begin, ensure you have met the following requirements:

    - Python 3.10 or higher is installed
    - Python virtualenv and pip is installed
    - Install some key libraries:
         sudo apt-get install python3-tk sshpass jq
    - Docker is installed (Skip unless you want to create a binary). Please refer to docker.md file for docker set-up instructions.    

```
### 📂 Setup

1. Clone the repo,

    ```https://github.com/opencomputeproject/ocp-diag-ctam```

### 🔧 Setting up the workspace

1. Sample workspace files are present inside `json_spec` directory. Modify these file as per your infra details.

2. `input` dir inside `json_spec` is organized by `spec_version` folders (e.g., spec_1.0, spec_1.1).
Test case specific JSON files (e.g., FirmwareInventory.json, UpdateService.json) required for executing CTAM test cases are also contained in this folder.
Within each `spec_version` folder, a `workspace` folder is provided containing sample input files.  

3. Create a workspace directory and copy the configuration files from `json_spec/input/spec_<version>/workspace` directory into `workspace` dir.

   -  `.netrc` - contains bmc ipaddress, username and password
   -  `dut_config.json` - contains various params for running the test cases
   -  `package_info.json` - contains details about the firmware 
   - `redfish_uri_config.json` - redfish config file
   - `test_runner.json` - config file for test run, can be overridden by cli flags
   - `redfish_response_messages.json` - config file for redfish response messages (default will be picked from json_spec/input).
  

### 🚩 Flag description

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
|`--spec`|                            |   |    Specify the version to run the test case with
|`--test_help`|                       |boolean|   Shows detailed help for a specific test case and exit
|`-c` or `--consolidate`|             |   |       Shows consolidated test results from multiple test runs into a single final report.

### Setup
1. Optional: create python [virtual environment](https://docs.python.org/3/library/venv.html) and activate.
    ```
    python -m venv venv
    source ./venv/bin/activate
    ```
2. Install dependencies
    ```
    python -m pip install -r pip-requirements.txt
    ```
3. For full documentation, from `/docs` directory, run
    ```
    ./make html
    ``````
    Open `docs/build/html/index.html` for full documentation including architecture and test case details

### 💻 Running the tool locally
1. To run suite,
    ```
    cd ctam
    python ctam.py -w ..\example_workspace
    ```
    
2. To list all test cases 
    ```
    cd ctam
    python ctam.py -l
    ```
3. To run a specific test case 
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -t <test case id>
    ```
  
4. To run test cases of a specifc test group
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -g <test group name>
    ```
5. To run test cases with sequence
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -test_seq <test case name or id> <test case name or id>
    ```

6. To run groups with sequence
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -group_seq <group name or id> <group name or id>
    ```

7. To get the full detailed help for a specific test case 
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -t <test case id> --test_help
    ``` 

8. To get consolidated test results from multiple test runs into a single final report
(See: [Why Consolidation is Needed](#why-consolidation-is-needed)) 
    ```   
    cd ctam
    python ctam.py -w ..\example_workspace -c <path_to_report_dir1> <path_to_report_dir2> ...
    ```
9. Choose test cases to run by using tags and specifying the tags to include/exclude in test_runner.json 

10. Choose test sequence in test_runner.json if you want to run it from test runner config.

11. All test executions can be run with or without specifying a spec version.  
See: [Behaviour Based on Input Source](#behaviour-based-on-input-source)

> **Spec Version Selection:**  
> Refer to **[Spec Version Handling](#spec-version-handling)** for details on how versions are resolved during test execution.


### Sphinx-Documentation

To create documentation for CTAM using Sphinx, follow these steps:

1. Navigate to the `docs` directory:
    
    `cd docs`
    
2. Build the HTML documentation:

    `make html`
    
3. Open `docs/build/html/index.html` to view the generated documentation.

4. If you’ve made modifications to your code and need to reconstruct the documentation HTML, run:
    - To clear build files, run:

        ``` make clean html ``` 
    
    - Build the HTML documentation:
        
        ```make html```
    
    It will recreate the documentation including changes you’ve made.


### 📦 Binary

1. One file Binary executable can be created using Makefile, to create binary run following command. This will create binary and sample workspace dir inside the dist folder. 
    
    `make build_image`

2. You can run the binary the same way running the python file. Just that now python file replaced by binary executalbe. Sample command to list all test cases. 

    Note: Please move your workspace directory inside dist directory before running the binary.

    `cd dist  && ./ctam -l`

3. To clear build files, run:

    ```make clean```


## 📑 Log Files created
Logs will be created under `example_workspace\TestRuns`

1. OCPTV Log file - All logs in OCPTV defined logging format. 
2. Test_Score_<>.json - All test cases result + Final score. 
3. Test_Report_<>.log - Tabulated report of test run
4. Test_Info_<>.json - Optional log file used by test interfaces (for debug)
5. RedfishCommandDetails/RedfishCommandDetails_<Test_ID>_ <Test_Name>_<>.json - Redfish Commands used & return values (for debug)
6. RedfishInteropValidator/<Test_ID>_ <Test_Name>/ConfigFile_<>.ini - Configuration file auto-generated for Redfish Interop Validator run.
7. RedfishInteropValidator/<Test_ID>_ <Test_Name>/InteropHtmlLog_<>.html - HTML formatted output log from Redfish Interop Validator for detailed review.
8. RedfishInteropValidator/<Test_ID>_ <Test_Name>/InteropLog_<>.txt - Text log output from Redfish Interop Validator containing command traces and results.
9. TestReport_consolidated_<>.log - Tabulated consolidated report combining results from multiple test runs. 
10. TestScore_consolidated_<>.json - merged list of test results from multiple independent test runs, presented in a unified JSON structure.
11. TestScore_Summary_<>.json - High-level summary of results, grouped by domain and compliance level,showing final outcome and scoring overview.


## 🕹️ Test Runner Knobs
Test runner knobs can be modified in `test_runner.json` to enable different logging mode.

| Variable           | Type    | Definition |
| :---               | :---    | :---       |
| `debug_mode`               | boolean  | For debug logs
| `console_mode`               | boolean  | For console logs
| `progress_bar`               | boolean  | For for progress bar indicator

## 🏷️ Tags
### 1. Group Tag

    - We can give tags at group level also.
    - If we provide any tag to a particular group, then all the test case under that group will be considered as the same tag.
    - If we run according to group tag, then all the test case will run under the group irrespective of the test case tag. 

### 2. Test Case Tags

    - We can assign different tags to different test cases.
    - If we run according to test case tag, then all the test cases which assigned with that tag would run irrespective of group tags.

    **Note: - Tags = Group Tags Union Test Case Tags
              group tags = ["G1"] and test case tags = ["L1"], so the final tags will be ["G1", "L1"]**

## 🔀 Local Port Forwarding

* Local port forwarding allows you to forward a port on the local (ssh client) machine to a port on the remote (ssh server) machine, which is then forwarded to a port on the destination machine.

* ### How it works
  * Local port forwarding creates a tunnel from a local port on your machine to a specified port on a remote server. When you access the local port, the traffic is securely forwarded to the remote server's port through the SSH connection.

  * For tunneling we need to give these parameters in dut_config.json file
    * SSHTunnel 
    * SSHTunnelRemoteIPAddress
    * SSHTunnelPortList
    * SSHTunnelProtocol
    * SSHTunnelRemotePort (Use 443 as remote port address for redfish tunneling)
    
  * The `sshtunnel` library in Python is a handy tool for creating SSH tunnels, allowing you to programmatically set up and manage SSH    port forwarding. It can be used to establish both local and remote port forwarding

## Why Consolidation is Needed

In many testing environments, it may not be possible or practical to execute all test cases in a single continuous run. This can happen due to:

- System resource limitations
- Hardware availability and scheduling constraints
- Incremental feature enablement across firmware versions
- The need to validate different functional components independently

As a result, test cases may be executed in multiple independent runs, each generating its own output report.

The **consolidation feature** enables merging the results of these separate test runs into one unified final report. This provides:

1. A combined and comprehensive view of overall system behavior  
2. A single summary score and pass/fail result  
3. Consistent reporting even when execution is distributed across multiple sessions

This ensures that analysis, scoring, and final compliance evaluation remain **complete, consistent, and streamlined**, regardless of how the tests were executed.  

## Spec Version Handling

This framework supports execution of test cases against multiple specification versions. A specification version may be provided explicitly by the user or resolved automatically based on configuration. If no version is specified, the framework defaults to the latest available supported version.

### Version Resolution Priority

The version used for test execution is determined in the following order of precedence:

| Priority (Highest to Lowest) | Source                          | Description                                                                            |
|-----------------------------|----------------------------------|----------------------------------------------------------------------------------------|
| 1 (Highest)                 | Command-Line Argument (`--spec`) | Explicit version supplied during test invocation overrides all other sources.          |
| 2                           | `test_runner.json` Configuration | Applied only when no command-line version is provided.                                 |
| 3 (Default)                 | Latest Available Version         | Used when neither CLI nor configuration specifies a version.                           |

### Version Compatibility Validation

Each test case may optionally define a `spec_versions` attribute to indicate supported specification versions. This attribute may take one of the following forms:

1. **Relational Expression**  
   Examples: `>= 1.0`, `< 1.1`, `== 1.0`, `> 1.0`, `<= 1.1`
2. **Explicit List of Versions**  
   Example: `["1.1", "1.0"]`
3. **None**  
   Indicates the test case is compatible with all specification versions.

### Validation Logic

When a version is selected (via CLI or configuration):

- The selected version is validated against the `spec_versions` attribute of each test case.
- If the version satisfies the constraint defined by `spec_versions`, the test case is executed.
- If the version does not satisfy the constraint, the test case is **skipped**.

### Behavior Based on Input Source

1. **No Version Specified**  
   The framework automatically selects the latest available supported version.

2. **Version Specified via Command-Line Argument (`--spec`)**  
   The version supplied via CLI takes highest precedence. It is validated against `spec_versions`.  
   - If valid → test runs  
   - If invalid → test is skipped

3. **Version Specified in `test_runner.json`**  
   Used only when no CLI version is provided, validated the same way.

#### Command-Line Example
```
cd ctam
python ctam.py -w ..\example_workspace -t <test_case_id> --spec <version>
```

### Summary

This implementation provides:

- Controlled and deterministic version selection
- Flexible compatibility via relational or list-based version constraints
- Clear and predictable execution behavior  
    
## 📖 Developer notes
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

## 🔮 Upcoming changes

    - More test cases
    - Logging improvements
    - Ability to set test sequence
    - PLDM validator, and auto creation of PLDM bundles with error injection.

### 📬 Contact

Feel free to start a new [discussion](https://github.com/opencomputeproject/ocp-diag-ctam/discussions), or otherwise post an [issue/request](https://github.com/opencomputeproject/ocp-diag-ctam/issues).

An email contact is also available at: ocp-test-validation@OCP-All.groups.io

