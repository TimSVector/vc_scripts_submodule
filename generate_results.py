#
# The MIT License
#
# Copyright 2020 Vector Informatik, GmbH.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import argparse
import shutil
import re
import glob
import subprocess
import time
import traceback

import getjobs

from managewait import ManageWait
try:
    from vector.apps.ReportBuilder.custom_report import CustomReport
    try:
        from vector.apps.DataAPI.unit_test_api import UnitTestApi
    except:
        from vector.apps.DataAPI.api import Api as UnitTestApi
except:
    pass
from vector.enums import ENVIRONMENT_STATUS_TYPE_T

#global variables
global verbose
global print_exc
global wait_time
global wait_loops
wait_time = 30
wait_loops = 1

verbose = False
print_exc = True
enabledEnvironmentArray = []

def getEnabledEnvironments(MPname):
    output = getjobs.printEnvironmentInfo(MPname, False)

    for line in output.split("\n"):
        if line.strip():
            # type being system or unit test
            compiler, testsuite, environment = line.split()
            enabledEnvironmentArray.append([compiler, testsuite, environment])
                       
def environmentEnabled(comp,ts,env):
    for c,t,e in enabledEnvironmentArray:
        if comp == c and ts == t and env == e:
            return True
    print(comp + "/" + ts + "/" + env + ": Disabled")
    return False 

def runManageWithWait(command_line, silent=False):
    global verbose
    global wait_time
    global wait_loops

    manageWait = ManageWait(verbose, command_line, wait_time, wait_loops)
    return manageWait.exec_manage(silent)

# Determine if this version of VectorCAST supports new-style reporting/Data API
def checkUseNewReportsAndAPI():
    if os.environ.get("VCAST_REPORT_ENGINE", "") == "LEGACY":
        # Using legacy reporting with new reports - fall back to parsing html report
        if verbose:
            print("VectorCAST/Execution ignoring LEGACY VCAST_REPORT_ENGINE.")

    # Look for existence of file that only exists in distribution with the new reports
    check_file = os.path.join(os.environ.get('VECTORCAST_DIR'),
                             "python",
                             "vector",
                             "apps",
                             "ReportBuilder",
                             "reports",
                             "full_report.pyc")
    if os.path.isfile(check_file):
        if verbose:
            print("Using VectorCAST with new style reporting. Use Data API for Jenkins reports.")
        return True
    else:
        if verbose:
            print("Using VectorCAST without new style reporting. Use VectorCAST reports for Jenkins reports.")
        return False

# Read the Manage project file to determine its version
# File has already been checked for existence
def readManageVersion(ManageFile):
    version = 14
    if os.path.isfile(ManageFile + ".vcm"):
        ManageFile = ManageFile + '.vcm'
    with open(ManageFile, 'r') as projFile:
        for line in projFile:
            if 'version' in line and 'project' in line:
                version = int(re.findall(r'\d+', line)[0])
                break
    if verbose:
        print("Version of Manage project file = %d" % version)
        print("(Levels change in version 17 (*maybe) and above)")
    return version

# Call manage to get the mapping of Envs to Directory etc.
def getManageEnvs(FullManageProjectName, use_ci = ""):
    manageEnvs = {}

    cmd_prefix = os.environ.get('VECTORCAST_DIR') + os.sep
    callStr = cmd_prefix + "manage --project " + FullManageProjectName + use_ci + " --build-directory-name"
    out_mgt = runManageWithWait(callStr, silent=True)
    if verbose:
        print(out_mgt)
        
    for line in out_mgt.split('\n'):
        if "Compiler:" in line:
            compiler = line.split(":",1)[-1].strip()
        elif "Testsuite ID:" in line:
            pass
        elif "TestSuite:" in line:
            testsuite = line.split(":",1)[-1].strip()
        elif "Environment:" in line:
            env_name = line.split(":",1)[-1].strip()
        elif "Build Directory:" in line:
            build_dir = line.split(":",1)[-1].strip()
            #rare case where there's a problem with the environment
            if build_dir == "":
                continue
            if not environmentEnabled(compiler,testsuite,env_name):
                continue
            build_dir_number = build_dir.split("/")[-1]
            level = compiler + "/" + testsuite + "/" + env_name # env_name.upper()
            entry = {}
            entry["env"] = env_name #env_name.upper()
            entry["compiler"] = compiler
            entry["testsuite"] = testsuite
            entry["build_dir"] = build_dir
            entry["build_dir_number"] = build_dir_number
            manageEnvs[level] = entry
            
            if verbose:
                print(entry)
                
        elif "Log Directory:" in line:
            pass
        elif "Control Status:" in line:
            pass

    return manageEnvs

def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)
        
def genDataApiReports(FullManageProjectName, entry, use_ci, xml_data_dir):

    global print_exc
    
    xml_file = ""

    try:
        from generate_xml import GenerateXml

        # Compiler/TestSuite
        env = entry["env"]
        level = entry["compiler"] + "_" + entry["testsuite"]
        
        jobNameDotted = '.'.join([entry["compiler"], entry["testsuite"], entry["env"]])
        jenkins_name = level + "_" + env
        jenkins_link = env + "_" + level
        xmlUnitReportName = os.path.join(xml_data_dir, "junit", "test_results_" + level + "_" + env + ".xml")
        xmlCoverReportName = os.path.join(xml_data_dir,"cobertura","coverage_results_" + level + "_" + env + ".xml")

        xml_file = GenerateXml(FullManageProjectName,
                               entry["build_dir"],
                               entry["env"],entry["compiler"],entry["testsuite"],
                               xmlCoverReportName,
                               jenkins_name,
                               xmlUnitReportName,
                               jenkins_link,
                               jobNameDotted, 
                               verbose,
                               use_ci)
                           
        if xml_file.api != None:
            if verbose:
                print("  Generate Jenkins testcase report: {}".format(xmlUnitReportName))
            xml_file.generate_unit()

    
    except Exception as e:
        print("ERROR: failed to generate XML reports using vpython and the Data API for ", entry["compiler"] + "_" + entry["testsuite"] + "_" + entry["env"], "in directory", entry["build_dir"])
        if True:
            traceback.print_exc()
    
    try:       
        failed_count = xml_file.failed_count
        passed_count = xml_file.passed_count
        del xml_file 
        return failed_count, passed_count
    except:
        traceback.print_exc()
        return 0, 0

def generateCoverReport(path, env, level ):

    from vector.apps.ReportBuilder.custom_report import CustomReport
    from vector.apps.DataAPI.cover_api import CoverApi

    try:
        api=CoverApi(path)
    except: 
        print("CR:    Skipping environment: "+ env)
        print("CR:       *" + env + " DataAPI is invalid")
        return 
        
    try:
        if api.environment.status != ENVIRONMENT_STATUS_TYPE_T.NORMAL:
            print("CR:    Skipping environment: "+ env)
            print("CR:       *" + env + " status is not NORMAL")
            return
    except:
        pass        
        
    report_name = "html_reports/" + level + "_" + env + ".html"

    try:
        CustomReport.report_from_api(api, report_type="Demo", formats=["HTML"], output_file=report_name, sections=["CUSTOM_HEADER", "REPORT_TITLE", "TABLE_OF_CONTENTS", "CONFIG_DATA", "METRICS", "MCDC_TABLES",  "AGGREGATE_COVERAGE", "CUSTOM_FOOTER"])

    except Exception as e:
        print("CR:    *Problem generating custom report for " + env + ": ")
        if print_exc:
            traceback.print_exc()

def generateUTReport(path, env, level): 
    global verbose

    def _dummy(*args, **kwargs):
        return True

    try:
        api=UnitTestApi(path)
    except: 
        print("UTR:   Skipping environment: "+ env)    
        print("UTR:       *" + env + "'s DataAPI is invalid")
        return 
        
    if api.environment.status != ENVIRONMENT_STATUS_TYPE_T.NORMAL:
        print("UTR:    Skipping environment: "+ env)    
        print("UTR:       *" + env + " status is not NORMAL")
        return
        
    report_name = "html_reports/" + level + "_" + env + ".html"
    try:
        api.commit = _dummy
        api.report(report_type="FULL_REPORT", formats=["HTML"], output_file=report_name)
    except Exception as e:
        print("UTR:    *Problem generating custom report for " + env + ".")
        if print_exc:
            traceback.print_exc()

def generateIndividualReports(entry, envName):
    global verbose

    env = entry["env"]
    build_dir = entry["build_dir"]
    level = entry["compiler"] + "_" + entry["testsuite"]

    if envName == None or envName == env:
        cov_path = os.path.join(build_dir,env + '.vcp')
        unit_path = os.path.join(build_dir,env + '.vce')

        if os.path.exists(cov_path):
            generateCoverReport(cov_path, env, level)

        elif os.path.exists(unit_path):
            generateUTReport(unit_path , env, level)


def useNewAPI(FullManageProjectName, manageEnvs, level, envName, use_ci, xml_data_dir = "xml_data"):
    failed_count = 0 
    passed_count = 0 

    for currentEnv in manageEnvs:

        if envName == None:
            fc, pc = genDataApiReports(FullManageProjectName, manageEnvs[currentEnv], use_ci, xml_data_dir)
            failed_count += fc
            passed_count += pc
            
            generateIndividualReports(manageEnvs[currentEnv], envName)
            
        elif manageEnvs[currentEnv]["env"].upper() == envName.upper(): 
            env_level = manageEnvs[currentEnv]["compiler"] + "/" + manageEnvs[currentEnv]["testsuite"]
            
            if env_level.upper() == level.upper():
                fc, pc = genDataApiReports(FullManageProjectName, manageEnvs[currentEnv], use_ci, xml_data_dir)
                failed_count += fc
                passed_count += pc
                generateIndividualReports(manageEnvs[currentEnv], envName)
        
    f = open("unit_test_fail_count.txt","w")
    f.write(str(failed_count))
    f.close()
    
    return failed_count, passed_count


# build the Test Case Management Report for Manage Project
# envName and level only supplied when doing reports for a sub-project
# of a multi-job
def buildReports(FullManageProjectName = None, level = None, envName = None, generate_individual_reports = True, 
        timing = False, cbtDict = None, use_archive_extract = False, 
        report_only_failures = False, no_full_report = False, use_ci = "", xml_data_dir = "xml_data", useStartLine = False):

    if timing:
        print("Start: " + str(time.time()))
        
    saved_level = level
    saved_envName = envName
    
    # make sure the project exists
    if not os.path.isfile(FullManageProjectName) and not os.path.isfile(FullManageProjectName + ".vcm"):
        raise IOError(FullManageProjectName + ' does not exist')
        return
        
    manageProjectName = os.path.splitext(os.path.basename(FullManageProjectName))[0]

    version = readManageVersion(FullManageProjectName)
    useNewReport = checkUseNewReportsAndAPI()
    manageEnvs = {}

    getEnabledEnvironments(FullManageProjectName)

    if timing:
        print("Version Check: " + str(time.time()))

    # cleaning up old builds
    for path in [os.path.join(xml_data_dir,"junit"),"html_reports"]:
        # if the path exists, try to delete it
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
            except:
                # if there was an error removing the directory...delete all the files
                print("Error removing directory: " + path)
                for file in glob.glob(path + "/*.*"):
                    try:
                        os.remove(file);
                    except:
                        print("Error removing file after failed to remove directory: " + path + "/" + file)
                pass
                
        # we should either have an empty directory or no directory
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except:
                print("Error creating directory: " + path)
            
    for file in glob.glob("*.csv"):
        try:
            os.remove(file);
            if verbose:
                print("Removing file: " + file)
        except Exception as e:
            print("Error removing " + file)
            print(e)
    
    
    ### Using new data API - 2019 and beyond
    
    failed_count = 0
    passed_count = 0
    if timing:
        print("Cleanup: " + str(time.time()))
    if useNewReport:

        try:
            shutil.rmtree("execution") 
        except:
            pass
        manageEnvs = getManageEnvs(FullManageProjectName, use_ci)
        if timing:
            print("Using DataAPI for reporting")
            print("Get Info: " + str(time.time()))
        fc, pc = useNewAPI(FullManageProjectName, manageEnvs, level, envName, use_ci = use_ci, xml_data_dir=xml_data_dir)
        failed_count += fc
        passed_count += pc
        if timing:
            print("XML and Individual reports: " + str(time.time()))

    ### NOT Using new data API        
    else:
        raise IOError('VectorCAST 2020 or later required')

    
    if timing:
        print("QA Results reports: " + str(time.time()))
            

    if timing:
        print("Complete: " + str(time.time()))
        
    return failed_count, passed_count
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('ManageProject', help='Manager Project Name')
    parser.add_argument('-v', '--verbose',   help='Enable verbose output', action="store_true")
    parser.add_argument('-l', '--level',   help='Environment Name if only doing single environment.  Should be in the form of level/env')
    parser.add_argument('-e', '--environment',   help='Environment Name if only doing single environment.  Should be in the form of level/env')
    parser.add_argument('-g', '--dont-generate-individual-reports',   help='Don\'t Generated Individual Reports (below 2019 - this just controls execution report generate, 2019 and later - no individual reports will be generated',  action="store_true")
    parser.add_argument('--wait_time',   help='Time (in seconds) to wait between execution attempts', type=int, default=30)
    parser.add_argument('--wait_loops',   help='Number of times to retry execution', type=int, default=1)
    parser.add_argument('--timing',   help='Display timing information for report generation', action="store_true")
    parser.add_argument('--junit',   help='Output test results in JUnit format', action="store_true")
    parser.add_argument('--cobertura',   help='Output coverage results in Cobertura format', action="store_true", default=False)
    parser.add_argument('--api',   help='Unused', type=int)
    parser.add_argument('--final',   help='Write Final JUnit Test Results file',  action="store_true")
    parser.add_argument('--gitlab',   help='Generate Cobertura in a format GitLab can use', action="store_true", default=True)
    parser.add_argument('--ci',                help='Use continuous integration licenses', action="store_true", default=False)
    parser.add_argument('--output_dir', help='Set the base directory of the xml_data directory. Default is the workspace directory', default = "xml_data")
    parser.add_argument('--azure',  help='Build using Azure DevOps', action="store_true", default = False)

    args = parser.parse_args()
    
    try:
        if "19.sp1" in open(os.path.join(os.environ['VECTORCAST_DIR'],"DATA/tools_version.txt").read()):
            # custom report patch for SP1 problem - should be fixed in future release      
            old_init = CustomReport._post_init
            def new_init(self):
                old_init(self)
                self.context['report']['use_all_testcases'] = True
            CustomReport._post_init = new_init
    except:
        pass
    
    if args.verbose:
        verbose = True
    wait_time = args.wait_time
    wait_loops = args.wait_loops

    if args.dont_generate_individual_reports:
        dont_generate_individual_reports = False
    else:
        dont_generate_individual_reports = True

    if args.timing:
        timing = True
    else:
        timing = False

    if args.junit:
        junit = True
    else:
        print ("Test results reporting has been migrated to JUnit.  If you are using older xUnit plugin with Single Jobs, please switch to using JUnit.  If you need assistance with that, contact support@us.vector.com")
        junit = True
        
    # Used for pre VC19
    os.environ['VCAST_RPTS_PRETTY_PRINT_HTML'] = 'FALSE'
    # Used for VC19 SP2 onwards
    os.environ['VCAST_RPTS_SELF_CONTAINED'] = 'FALSE'
    
    if args.ci:
        os.environ['VCAST_USE_CI_LICENSES'] = '1'
        use_ci = " --ci "
    else:
        use_ci = ""

    xml_data_dir = args.output_dir

    failed_count, passed_count = buildReports(args.ManageProject,args.level,args.environment,dont_generate_individual_reports, timing, use_ci, xml_data_dir)
    
    if args.cobertura:
        for file in glob.glob(os.path.join(xml_data_dir,"cobertura","coverage_results_*.*")):
            try:
                os.remove(file);
            except:
                print("Error removing file after failed to remove directory: " + path + "/" + file)
        import cobertura
        cobertura.gitlab = args.gitlab
        cobertura.generateCoverageResults(args.ManageProject, args.azure)
        
    sys.exit(failed_count)    