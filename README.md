# Compliance Tool for Accelerator Management

The [**OCP Test & Validation Initiative**](https://github.com/opencomputeproject/ocp-diag-core) is a collaboration between datacenter hyperscalers having the goal of standardizing aspects of the hardware validation/diagnosis space, along with providing necessary tooling to enable both diagnostic developers and executors to leverage these interfaces.

Specifically, the [ocp-diag-ctam](https://github.com/opencomputeproject/ocp-diag-ctam) tool provides acceptance testing for Accelerator Management in cloud data centers.

---

This project is part of [OCPTV](https://github.com/opencomputeproject/ocp-diag-core) and exists under the same [MIT License Agreement](https://github.com/opencomputeproject/ocp-diag-ctam/LICENSE).

## Getting Started

1. Optional: create python [virtual environment](https://docs.python.org/3/library/venv.html) and activate.
    ```
    python -m venv venv
    source ./venv/bin/activate
    ```
2. Run 
    ```
    python -m pip install -r pip-requirements.txt
    ```
3. For full documentation, from `/docs` directory, run
    ```
    ./make html
    ``````
    Open `docs/build/html/index.html` for full documentation including architecture and test case details
4. To run suite,
    ```
    cd ctam
    python ctam.py -w ..\example_workspace
    ```
    Logs will be created under `example_workspace\TestRuns`
5. To list all test cases 
    ```
    cd ctam
    python ctam.py -l
    ```
6. To run a specific test case 
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -t <test case id>
    ```
    Logs will be created under `example_workspace\TestRuns`
7. To run test cases of a specifc test group
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -g <test group name>
    ```
    Logs will be created under `example_workspace\TestRuns`
8. To run test cases with sequence
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -test_seq <test case name or id> <test case name or id>
    ```
    Logs will be created under `example_workspace\TestRuns`
9. To run groups with sequence
    ```
    cd ctam
    python ctam.py -w ..\example_workspace -group_seq <group name or id> <group name or id>
    ```
    Logs will be created under `example_workspace\TestRuns`
10. Choose test cases to run by using tags and specifying the tags to include/exclude in test_runner.json 
11. Choose test sequence in test_runner.json if you want to run it from test runner config.


## Log Files created

1. OCPTV Log file - All logs in OCPTV defined logging format. 
2. Test_Score_<>.json - All test cases result + Final score. 
3. Test_Report_<>.log - Tabulated report of test run
4. Test_Info_<>.json - Optional log file used by test interfaces (for debug)
5. RedfishCommandDetails/RedfishCommandDetails_<Test_ID>_ <Test_Name>_<>.json - Redfish Commands used & return values (for debug)

## Test Runner Knobs

1. debug_mode - True/False (for debug logs)
2. console_log - True/False (for console logs)
3. progress_bar - True/False (for progress bar idicator)

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
