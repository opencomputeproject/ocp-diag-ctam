===========================
Getting Started
===========================

Welcome to the **Compliance Tool for Accelerator Management (CTAM)**  documentation!
This section walks you through the key stages of using CTAM effectively:

**1. Understanding Compliance Scenarios**
-----------------------------------------

CTAM defines a suite of test cases covering a range of compliance areas. To explore the available scenarios

Run below commandline to generate the list of all testcases with their IDs and other attributes:

.. code-block:: bash

    python ctam.py -l

Each test case is designed to validate specific behaviors or system responses. Use the **search bar** in the top left to search for testcases by their testIDs.

**2. Running Compliance Tests**
-------------------------------

To execute a test case:

.. code-block:: bash

    python ctam.py -w <workspace_dir> -t <test_case_id or test_case_name>


*### **Explanation:**

- **`<workspace_dir>`**: The path to your workspace directory.
- **`<test_case_id>`**: The ID of the specific test case to run.
- **`<test_case_name>`**: The name of the specific test case to run.

The output logs are saved in the **`TestRuns`** folder inside the workspace directory.


**3. Interpreting Test Results**
---------------------------------

After executing your test(s), CTAM generates a structured **Test Report** with multiple tables to help you grade the compliance results.

Here's a breakdown of each:

- **Domain-wise Test Report**

  This table provides a summary of test execution grouped by feature domains (e.g., Telemetry, FW Update, RAS, Health_check).  
  It shows:

  - Number of test cases executed and passed per domain  
  - Weight and score contribution. Note that the weights are assigned based on the compliance level of the each testcase.
  - Grade and execution time

Note that the compliance levels can be changed in the `weighted_score` inside the `test_runner.json` file whose default value is shown below:

.. code-block:: json

    "weighted_score": {
        "L0": 100, "L1": 50, "L2": 20, "L3": 0
    }

- **Compliance Level Weighted Report**

  Shows how test cases are distributed and scored across compliance levels (L0-L3).
  Note that the overall grade will remain the same as that of the Domain-wise Test Report.

- **Compliance Level Normalized Weighted Report**

  This provides a normalized view, adjusting for the relative weight of each compliance level.  
  It helps limit the influence of higher compliance level test cases in the final compliance score/grade.

Note that the compliance levels can be changed in the `normalized_score` inside the `test_runner.json` file whose default value is shown below:

.. code-block:: json

    "normalized_score": {
        "L0": 50, "L1": 35, "L2": 15, "L3": 0
    }

For example, if there are 5 L0 test cases then the above weight distribution will lead to each L0 test case having a weight of 10 (ie. 50/5).

- **Simple Uniform Grading Report**

  A quick summary of how many tests passed out of the total available, and associated pass percentage.

- **Test Result Table**

  Lists all individual test cases executed:

  - Test ID and Name  
  - Execution time  
  - Weight, Score, Result (PASS/FAIL)

  The last row of the Test Result Table provides a quick summary of the total execution time, cumulative test score, and the overall compliance percentage:

  - **Total Execution Time** → Total time taken to execute all test cases  
  - **Total TestCase Weight** → Combined weight of all test cases  
  - **Total Test Score** → Total score achieved from passed tests  
  - **Overall Test Result (%)** → Final compliance percentage (e.g., `85.71%`)

If you encounter FAIL(s) proceed to next section to debug the issue.


**4. Debugging Failures**
-------------------------
CTAM generates detailed logs to help you identify the issue. The logs are structured as follows:

- **`Command_Line_Logs`**, **`OCPTV_CTAM_LOGS`**, **`TestScore.json`**, **`RedfishCommandDetails`** are available inside the **CTAM_LOGS_<timestamp>** folder located under the **`TestRuns`** directory in your workspace.
- **`Command_Line_Logs`** provides a comprehensive log of all actions taken during the test run, including any errors encountered.
- **`TestScore.json`** contains detailed outcome summaries (`pass/fail`, Compliance Score, duration, FailureReason, TotalScore).
- **`OCPTV_CTAM_LOGS`** capture step-by-step test actions. Useful for understanding exactly what the test attempted and whether each step succeeded.
- **`RedfishCommandDetails`** contains the Redfish command details and the response received from the server.


**When a Test Fails :**

1. **Check the Command Line Logs**

   - Open the ``Command_Line_Logs`` file.
   - Look for the line containing ``"status": "FAIL"`` — this indicates a failure in the test case.
   - The line will also include a **FailureReason** and **TestCaseID** to help you identify the specific test that failed.

2. **Go to ``OCPTV_CTAM_LOGS```**

   - Open the log file matching the failed test.
   - Look for log entries containing ``"severity": "ERROR"`` or ``"severity": "FATAL"`` — these indicate the **exact point of failure**
   - Focus on the corresponding step number and description to understand **which part of the test logic failed** 
   - This helps identify the **exact failure point** and speeds up root cause analysis.

3. **Inspect ``RedfishCommandDetails``**

   - Locate the Redfish command log related to the test under ``RedfishCommandDetails`` folder.
   - Check the following:
   
     - **URI used**
     - **HTTP method** (GET/POST, etc.)
     - **Server response/status code**
   
This is useful for debugging whether the API failed due to a server-side error, incorrect URI, or permission issue.

4. **Check Dependencies in the Test Documentation**

   - Every test case description includes a **Dependency** section.
   - If the failure is related to a missing or incorrect dependency:

     - Search for the **Test ID** in the CTAM documentation **search bar**.
     - Open the TestCase page and review the **Dependency** section.
     - It will point to specific JSON files based on the Dependencies used in the testcase(e.g., ``<redfish_uri_config.json>``, ``dut_info.json``, etc.)


**5. Running Advanced Regression Suites**
-----------------------------------------

To run a batch of tests as a regression suite:

1. Define the suite in the `test_runner.json` file with a list of test case IDs.
2. Set the desired suite name in the `"active_test_suite"` field.  e.g., "active_test_suite": ["suite_1", "suite_2",..., "suite_n"]

Example:  Inside `test_runner.json`

.. code-block:: json
  
    {
        "..." : "",
        "active_test_suite": ["regression_test_suite_0", "regression_test_suite_1"],
        "regression_test_suite_0": ["F0", "F1", "..."],
        "regression_test_suite_1": ["F0", "F1", "F64", "T0", "..."],
        "..." : "",
    }


CTAM will execute all test cases listed in the active suite from `test_runner.json`.


**Using PROF (Pause Regression On Failure)**

You can use a special keyword called ``PROF`` to stop the test suite if the previous test fails.

For example: Inside `test_runner.json`

.. code-block:: json

    "...": "",
    "active_test_suite": ["regression_test_suite_0"],
    "regression_test_suite_0": ["F0", "PROF", "F1", "T0", "T2"],
    "...": "",

In this example,adding ``PROF`` ensures that ``F1`` and following testcases will only execute if ``F0`` passes.

This behavior helps maintain the integrity of dependent test cases and avoids unnecessary execution when prerequisites are not met.

------------------------------

✅ All set! You can now begin running and exploring CTAM compliance tests with confidence.
