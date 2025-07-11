# General

Integration between VectorCAST and CI/CD tools

# Installation

This repository uses a git submodule so make sure when you clone this repository, clone with _--recurse-submodules_ option

# Summary

This integration allows the user to build, execute, generate reports, and generate metrics for 
[VectorCAST](http://vector.com/vectorcast) Projects in various CI/CD tools

Results can be published in the following formats
* Coverage results to **_GitLab_**, **_SonarQube_**: **_Cobertura_** (xml_data/cobertura) and **_Extended Cobertura_**
* Test Results
    * To **_GitLab_**: **_JUnit_** (xml_data/junit)
    * To **_SonarQube_**: **_CppUnit_** (xml_data/sonarqube)  
* Static Analysis to **_GitLab_**: **_CodeClimate_** (pclp/gl-code-quality-report.json)

:warning: Due to the limiations of Cobertura plugin, only Statement and Branch results are reported

# Calling Action

The python scrip `vcast_exec.py` is the main driver for build/execute VectorCAST Projects.  You can run environments in parallel by specifying `--jobs #`

The api for vcast_exec.py follows:

```
    usage: vcast_exec.py [-h] [--build-execute] [--build | --incremental] [--output_dir OUTPUT_DIR]
                         [--source_root SOURCE_ROOT] [--html_base_dir HTML_BASE_DIR]
                         [--cobertura] [--cobertura_extended] [--lcov] [--junit]
                         [--export_rgw] [--sonarqube] [--pclp_input PCLP_INPUT]
                         [--pclp_output_html PCLP_OUTPUT_HTML]
                         [--exit_with_failed_count [EXIT_WITH_FAILED_COUNT]] [--aggregate]
                         [--metrics] [--fullstatus] [--tcmr] [--jobs JOBS]
                         [--ci] [-l LEVEL] [-e ENVIRONMENT] [--gitlab | --azure]
                         [--print_exc] [--timing] [--verbose] [--version]
                         ManageProject

    positional arguments:
      ManageProject         VectorCAST Project Name

    optional arguments:
      -h, --help            show this help message and exit

    Script Actions:
      Options for the main tasks

      --build-execute       Builds and exeuctes the VectorCAST Project
      --build               Only builds the VectorCAST Project
      --incremental         Use Change Based Testing (Cannot be used with --build)

    Metrics Options:
      Options generating metrics

      --output_dir OUTPUT_DIR
                            Set the base directory of the xml_data directory. Default is the workspace directory
      --source_root SOURCE_ROOT
                            Set the absolute path for the source file in coverage reporting
      --html_base_dir HTML_BASE_DIR
                            Set the base directory of the html_reports directory. The default is the workspace directory
      --cobertura           Generate coverage results in Cobertura xml format
      --cobertura_extended  Generate coverage results in extended Cobertura xml format
      --lcov                Generate coverage results in an LCOV format
      --junit               Generate test results in Junit xml format
      --export_rgw          Export RGW data
      --sonarqube           Generate test results in SonarQube Generic test execution report format (CppUnit)
      --pclp_input PCLP_INPUT
                            Generate static analysis results from PC-lint Plus XML file to generic static
                            analysis format (codequality)
      --pclp_output_html PCLP_OUTPUT_HTML
                            Generate static analysis results from PC-lint Plus XML file to an HTML output
      --exit_with_failed_count [EXIT_WITH_FAILED_COUNT]
                            Returns failed test case count as script exit. Set a value to indicate a percentage
                            above which the job will be marked as failed

    Report Selection:
      VectorCAST Manage reports that can be generated

      --aggregate           Generate aggregate coverage report VectorCAST Project
      --metrics             Generate metrics reports for VectorCAST Project
      --fullstatus          Generate full status reports for VectorCAST Project
      --tcmr                Generate Test Cases Management Reports for each VectorCAST environment in project

    Build/Execution Options:
      Options that effect build/execute operation

      --jobs JOBS           Number of concurrent jobs (default = 1)
      --ci                  Use Continuous Integration Licenses
      -l LEVEL, --level LEVEL
                            Environment Name if only doing single environment. Should be in the form of compiler/testsuite
      -e ENVIRONMENT, --environment ENVIRONMENT
                            Environment Name if only doing single environment.
      --gitlab              Build using GitLab CI (default)
      --azure               Build using Azure DevOps

    Script Debug :
      Options used for debugging the script

      --print_exc           Prints exceptions
      --timing              Prints timing information for metrics generation
      -v, --verbose         Enable verbose output
      --version             Diplays the version of the script. 
```

# Change log
7/2025
* Updated to produce a version of the script (--version) based on push date and commit ID

5/2025
* Updated the index.html to include the proper CSS for PC Lint Plus
* Added support for manage.exe parallel build/executes
* Fixed issues with corner cases in scripts

3/2025
* Added support for generating test case management reports and storing them to management directory
* Updated the index.html to include those reports
* Added incremental_build_report_aggregator.py from the Jenkins plugin.  

11/2024
* Added option for source root to add an absolute path to the beginning of the relatives coverage paths
* Fixed a lcov coverage error when VC Project coverage is not in Source File Perspective mode

9/2024
* Initial submodule commit

# Licensing Information

The MIT License

Copyright 2024 Vector Informatik, GmbH.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

