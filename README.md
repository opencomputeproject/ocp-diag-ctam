# CTAM Compliance Tool for Accelerator Management

This tool provides acceptance testing for Accelerator Management in cloud data centers.

## Getting Started

1. Optional:  create python virtual environment
2. Run 
      python -m pip install -r pip-requirements.txt
3. For full documentation, from /docs directory, run 
      ./make html
      Open docs/build/html/index.html for full documentation including architecture and test case details
4. To run suite,
      cd ctam
      python ctam.py -w ..\example_workspace
      Logs will be created under example_workspace\TestRuns
5. To list all test cases 
      cd ctam
      python ctam.py -l
6. To run a specific test case 
      cd ctam
      python ctam.py -w ..\example_workspace -t <test case id>
      Logs will be created under example_workspace\TestRuns
7. To run test cases of a specifc test group
      cd ctam
      python ctam.py -w ..\example_workspace -g <test group name>
      Logs will be created under example_workspace\TestRuns
8. Choose test cases to run by using tags and specifying the tags to include/exclude in test_runner.json 



## VS Code

  VS Code is not required for development, however it does have workspace configurations to assist in development.
  In lieu of VS Code usage, the following items should be configured for other editors or the developer should perform
  steps manually to ensure the consistency of the code base.

  To use VS Code, open the ctam.code-workspace

  1. automatic file formatting using python black formatter on file save.
     a. "--line-length", "120"
  2. Indent set to 4 spaces
  3. Auto docstring configured for sphinx, type 3 double quotes below python class or function and the documentation header is automatically stubbed out.
  4. Automatic mypy checking of code
  5. spell checking
  6. useful git extensions
  7. Useful debugger configurations defined in launch.json,   extensible
  8. Useful Code snippets to jump start new test development
     a. Snippets for interfaces, test groups and test cases simplify new tests.
     b. easy replace of TODO in the snippet creates runnable test case quickly.

## Upcoming changes 

1. More test cases 
2. Logging improvements
3. Ability to set test sequence
4. PLDM validator, and auto creation of PLDM bundles with error injection.

