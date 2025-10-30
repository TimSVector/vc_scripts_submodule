#
# The MIT License
#
# Copyright 2024 Vector Informatik, GmbH.
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

import os
from datetime import datetime
try:
    from html import escape
except ImportError:
    # html not standard module in Python 2.
    from cgi import escape
import sys
# Later version of VectorCAST have renamed to Unit Test API
# Try loading the newer (renamed) version first and fall back
# to the older.
try:
    from vector.apps.DataAPI.unit_test_api import UnitTestApi
    from vector.apps.DataAPI.unit_test_models import TestCase
except:
    from vector.apps.DataAPI.api import Api as UnitTestApi
    from vector.apps.DataAPI.models import TestCase

try:
    from vector.apps.DataAPI.vcproject_api import VCProjectApi
except:
    pass

from vector.apps.DataAPI.cover_api import CoverApi
try:
    from vector.apps.ReportBuilder.custom_report import fmt_percent
except:
    def fmt_percent(x,y):
        if y == 0.0:
            return "0"
        else:
            return str(int(round(100.0 * float(x) / float(y))))
                   
from operator import attrgetter
from vector.enums import COVERAGE_TYPE_TYPE_T
from vector.enums import ENVIRONMENT_STATUS_TYPE_T
from vcast_utils import dump, getVectorCASTEncoding
import hashlib 

def dummy(*args, **kwargs):
    return None

##########################################################################
# This class generates the XML (JUnit based) report for the overall
# (Emma based) report for Coverage
#
class BaseGenerateXml(object):
    def __init__(self, cover_report_name, verbose, use_ci):
        self.cover_report_name = cover_report_name
        self.verbose = verbose
        self.using_cover = False

        # get the VC langaguge and encoding
        self.encFmt = getVectorCASTEncoding()
        if use_ci:
            self.use_ci = " --ci "
        else:
            self.use_ci = ""
            
#
# BaseGenerateXml - calculate coverage value
#
    def calc_cov_values(self, x, y):
        column = ''
        if y == 0:
            column = None
        else:
            column = '%s%% (%d / %d)' % (fmt_percent(x, y), x, y)
        return column

    def convertExecStatus(self, status):
        convertDict = { 'EXEC_SUCCESS_PASS':['Testcase passed','passed'],
                        'EXEC_SUCCESS_FAIL':['Testcase failed','failed'],
                        'EXEC_SUCCESS_NONE':['No expected results','run'],
                        'EXEC_EXECUTION_FAILED':['Testcase failed to run to completion (possible testcase timeout)','failed'],
                        'EXEC_ABORTED':['User aborted testcase','cancelled'],
                        'EXEC_TIMEOUT_EXCEEDED':['Testcase timeout','failed'],
                        'EXEC_VXWORKS_LOAD_ERROR':['VxWorks load error','notrun'],
                        'EXEC_USER_CODE_COMPILE_FAILED':['User code failed to compile','notrun'],
                        'EXEC_COMPOUND_ONLY':['Compound only test case','notrun'],
                        'EXEC_STRICT_IMPORT_FAILED':['Strict Testcase Import Failure','failed'],
                        'EXEC_MACRO_NOT_FOUND':['Macro not found','notrun'],
                        'EXEC_SYMBOL_OR_MACRO_NOT_FOUND':['Symbol or macro not found','notrun'],
                        'EXEC_SYMBOL_OR_MACRO_TYPE_MISMATCH':['Symbol or macro type mismatch','notrun'],
                        'EXEC_MAX_VARY_EXCEEDED':['Maximum varied parameters exceeded','notrun'],
                        'EXEC_COMPOUND_WITH_NO_SLOTS':['Compound with no slot','notrun'],
                        'EXEC_COMPOUND_WITH_ZERO_ITERATIONS':['Compound with zero slot','notrun'],
                        'EXEC_STRING_LENGTH_EXCEEDED':['Maximum string length exceeded','notrun'],
                        'EXEC_FILE_COUNT_EXCEEDED':['Maximum file count exceeded','notrun'],
                        'EXEC_EMPTY_TESTCASE':['Empty testcase','notrun'],
                        'EXEC_NO_EXPECTED_RETURN':['No expected return value','failed'],
                        'EXEC_NO_EXPECTED_VALUES':['No expected values','failed'],
                        'EXEC_CSV_MAP':['CSV Map','notrun'],
                        'EXEC_DRIVER_DATA_COMPILE_FAILED':['Driver data failed to compile','notrun'],
                        'EXEC_RECURSIVE_COMPOUND':['Recursive Compound Test','failed'],
                        'EXEC_SPECIALIZED_COMPOUND_CONTAINING_COMMON':['Specialized compound containing non-specialized testcases','failed'],
                        'EXEC_COMMON_COMPOUND_CONTAINING_SPECIALIZED':['Non-specialized compound containing specialized testcases','failed'],
                        'EXEC_HIDING_EXPECTED_RESULTS':['Hiding expected results','run'],
                        'INVALID_TEST_CASE':['Invalid Test Case','failed']
        }

        try:
            s = convertDict[str(status)]
        except:
            s = convertDict[status]
        return s 
        
    def has_any_coverage(self,unit_or_func):
        if unit_or_func.coverdb.has_covered_function_calls or \
           unit_or_func.coverdb.has_covered_functions      or \
           unit_or_func.coverdb.has_covered_mcdc_branches  or \
           unit_or_func.coverdb.has_covered_mcdc_pairs     or \
           unit_or_func.coverdb.has_covered_statements     or \
           unit_or_func.coverdb.has_covered_branches:
            return True
        else:
            return False

#
# BaseGenerateXml - create coverage data object for given metrics entry
# for coverage report
#
    def add_coverage(self, is_unit, unit_or_func, metrics, cov_type):
        cov_type_str = str(cov_type)

        entry = {}
        entry["statement"] = None
        entry["branch"] = None
        entry["mcdc"] = None
        entry["basispath"] = None
        entry["function"] = None
        entry["functioncall"] = None

        if self.has_function_coverage:
            if is_unit:
                (total_funcs, funcs_covered) = unit_or_func.cover_data.functions_covered
                entry["function"] = self.calc_cov_values(funcs_covered, total_funcs)
            elif unit_or_func.cover_data.coverdb.has_covered_functions:
                try:
                    if unit_or_func.has_covered_objects:
                        entry["function"] = '100% (1 / 1)'
                    else:
                        entry["function"] = '0% (0 / 1)'
                except:
                    if self.has_any_coverage(unit_or_func):
                        entry["function"] = '100% (1 / 1)'
                    else:
                        entry["function"] = '0% (0 / 1)'

        if self.has_call_coverage:
            entry["functioncall"] = self.calc_cov_values(metrics.max_covered_function_calls, metrics.function_calls)
            
        if self.verbose:
            print("Coverage Type:", cov_type)

        if 'NONE' in cov_type_str:
            return entry

        if "MCDC" in cov_type_str:
            entry["mcdc"] = self.calc_cov_values(metrics.max_covered_mcdc_branches, metrics.mcdc_branches)
            if not self.simplified_mcdc:
                entry["mcdc"] = self.calc_cov_values(metrics.max_covered_mcdc_pairs, metrics.mcdc_pairs)
            entry["branch"] = self.calc_cov_values(metrics.max_covered_mcdc_branches, metrics.mcdc_branches)
        if "BASIS_PATH" in cov_type_str:
            (cov,total) = unit_or_func.basis_paths_coverage
            entry["basis_path"] = self.calc_cov_values(cov, total)
        if "STATEMENT" in cov_type_str:
            entry["statement"] = self.calc_cov_values(metrics.max_covered_statements, metrics.statements)
        if "BRANCH" in cov_type_str:
            entry["branch"] = self.calc_cov_values(metrics.max_covered_branches, metrics.branches)
        if "FUNCTION_FUNCTION_CALL" in cov_type_str:
            entry["functioncall"] = self.calc_cov_values(metrics.max_covered_function_calls, metrics.function_calls)
            entry["function"] = self.calc_cov_values(metrics.max_covered_functions, metrics.functions)

        return entry

#
# Internal - calculate 'grand total' coverage values for coverage report
#
    def grand_total_coverage(self, cov_type):

        cov_type_str = str(cov_type)

        entry = {}
        entry["statement"] = None
        entry["branch"] = None
        entry["mcdc"] = None
        entry["basispath"] = None
        entry["function"] = None
        entry["functioncall"] = None
        
        if self.has_function_coverage:
            entry["function"] = self.calc_cov_values(self.grand_total_max_covered_functions, self.grand_total_max_coverable_functions)
        if self.has_call_coverage:
            entry["functioncall"] = self.calc_cov_values(self.grand_total_max_covered_function_calls, self.grand_total_function_calls)           
        if cov_type == None:
            return entry
        if "MCDC" in cov_type_str:
            entry["mcdc"] = self.calc_cov_values(self.grand_total_max_mcdc_covered_branches, self.grand_total_mcdc_branches)
            if not self.simplified_mcdc:
                entry["mcdc"] = self.calc_cov_values(self.grand_total_max_covered_mcdc_pairs, self.grand_total_mcdc_pairs)
            entry["branch"] = self.calc_cov_values(self.grand_total_max_mcdc_covered_branches, self.grand_total_mcdc_branches)
        if "BASIS_PATH" in cov_type_str:
            entry["basis_path"] = self.calc_cov_values(self.grand_total_cov_basis_path, self.grand_total_total_basis_path)
        if "STATEMENT" in cov_type_str:
            entry["statement"] = self.calc_cov_values(self.grand_total_max_covered_statements, self.grand_total_statements)
        if "BRANCH" in cov_type_str:
            entry["branch"] = self.calc_cov_values(self.grand_total_max_covered_branches, self.grand_total_branches)
        if "FUNCTION_FUNCTION_CALL" in cov_type_str:
            entry["functioncall"] = self.calc_cov_values(self.grand_total_max_covered_function_calls, self.grand_total_function_calls)

        return entry

#
# Internal - generate the formatted timestamp to write to the coverage file
#
    def get_timestamp(self):
        dt = datetime.now()
        hour = dt.hour
        if hour > 12:
            hour -= 12
        return dt.strftime('%d %b %Y  @HR@:%M:%S %p').upper().replace('@HR@', str(hour))

#
# BaseGenerateXml - start writing to the coverage file
#
    def start_cov_file(self):
        if self.verbose:
            print("  Writing coverage xml file:        {}".format(self.cover_report_name))
        self.fh = open(self.cover_report_name, "wb")
        data = "<!-- VectorCAST/Jenkins Integration, Generated {} -->\n".format(self.get_timestamp())
        data += "<report>\n"
        data += "  <version value=\"3\"/>\n"
        self.fh.write(data.encode(self.encFmt,"replace"))

#
# BaseGenerateXml - write the end of the coverage file and close it
#
    def end_cov_file(self):
        self.fh.write('</report>')
        self.fh.close()
#
# BaseGenerateXml the XML Modified 'Emma' coverage data
#
    def hasEitherFunctionCoverages(self, srcFile):


        cntFunCov = 0
        cntFuncCallCov = 0

        try:
            cov_types = srcFile.coverage_types
        except:
            cov_types = [srcFile.coverage_type]

        for cov_type in cov_types:
            if "FUNCTION_FUNCTION_CALL" in str(cov_type):
                cntFunCov      += 1
                cntFuncCallCov += 1
            elif "FUNCTION_CALL" in  str(cov_type):
                cntFuncCallCov += 1
            elif "FUNCTION_COVERAGE" in  str(cov_type):
                cntFunCov      += 1

        return (cntFunCov > 0), (cntFuncCallCov > 0)

    def hasAnyCov(self, srcFile):

        try:
            metrics = srcFile.metrics
        except:
            metrics = srcFile.cover_metrics

        if metrics is None:
            return False

        try:
            covTotals = (
                metrics.branches +
                metrics.function_calls +
                metrics.functions +
                metrics.mcdc_branches +
                metrics.mcdc_pairs +
                metrics.statements )
        except:
            covTotals = (
                metrics.branches +
                metrics.function_calls +
                metrics.mcdc_branches +
                metrics.mcdc_pairs +
                metrics.statements )

        return covTotals > 0

#
# BaseGenerateXml the XML Modified 'Emma' coverage data
#
    def _generate_cover(self, cov_type):
        self.num_functions = 0

        self.simplified_mcdc = self.api.environment.get_option("VCAST_SIMPLIFIED_CONDITION_COVERAGE")
        self.our_units = []
        self.has_call_coverage = False
        self.has_function_coverage = False
        self.grand_total_complexity = 0

        self.grand_total_max_covered_branches = 0
        self.grand_total_branches = 0
        self.grand_total_max_covered_statements = 0
        self.grand_total_statements = 0
        self.grand_total_max_mcdc_covered_branches = 0
        self.grand_total_mcdc_branches = 0
        self.grand_total_max_covered_mcdc_pairs = 0
        self.grand_total_mcdc_pairs = 0
        self.grand_total_max_covered_function_calls = 0
        self.grand_total_function_calls = 0
        self.grand_total_max_covered_functions = 0
        self.grand_total_max_coverable_functions = 0
        self.grand_total_total_basis_path = 0
        self.grand_total_cov_basis_path = 0

        overallCoverageTypes = set()

        for srcFile in self.units:
            if not srcFile.unit_of_interest:
                if srcFile.coverage_type == COVERAGE_TYPE_TYPE_T.NONE:
                    continue
            if self.using_cover and not srcFile.is_instrumented:
                continue

            if not self.hasAnyCov(srcFile):
                continue

            hasFuncCov, hasFuncCallCov = self.hasEitherFunctionCoverages(srcFile)
            self.has_function_coverage = hasFuncCov
            self.has_call_coverage = hasFuncCallCov

            if hasFuncCov:
                self.toplevel_has_function_coverage =  True
            if hasFuncCallCov:
                self.toplevel_has_call_coverage =  True

            try:
                metrics = srcFile.metrics
            except:
                metrics = srcFile.cover_metrics

            try:
                cov_type = srcFile.coverage_types
                overallCoverageTypes.update(srcFile.coverage_types)
            except:
                cov_type = srcFile.coverage_type
                overallCoverageTypes.update({srcFile.coverage_type})

            entry = {}
            entry["unit"] = srcFile
            entry["functions"] = []
            entry["complexity"] = 0
            entry["coverage"] = self.add_coverage(True, srcFile, metrics, cov_type)
            functions_added = False
            funcs_with_cover_data = []
            for func in srcFile.functions:
                if self.hasAnyCov(func):
                    functions_added = True
                    funcs_with_cover_data.append(func)

            if isinstance(self.api, CoverApi):
                sorted_funcs = sorted(funcs_with_cover_data,key=attrgetter('cover_data.index'))
            else:
                try:
                    sorted_funcs = sorted(funcs_with_cover_data,key=attrgetter('cover_data.id'))
                except:
                    sorted_funcs = sorted(funcs_with_cover_data,key=attrgetter('instrumented_functions.index'))

            sorted_funcs.sort(key=lambda x: (x.name))

            for func in sorted_funcs:
                try:
                    cover_function = func.cover_data.metrics
                except:
                    cover_function = func.metrics
                functions_added = True
                try:
                    complexity = func.complexity
                except:
                    complexity = func.metrics.complexity

                if complexity >= 0:
                    entry["complexity"] += complexity
                    self.grand_total_complexity += complexity
                func_entry = {}
                func_entry["func"] = func
                func_entry["complexity"] = complexity
                func_entry["coverage"] = self.add_coverage(False, func, cover_function, cov_type)
                self.num_functions += 1
                entry["functions"].append(func_entry)
            if functions_added:
                self.our_units.append(entry)

            self.grand_total_max_covered_branches += metrics.max_covered_branches + metrics.max_covered_mcdc_branches
            self.grand_total_branches += metrics.branches + metrics.mcdc_branches
            self.grand_total_max_covered_statements += metrics.max_covered_statements
            self.grand_total_statements += metrics.statements
            self.grand_total_max_mcdc_covered_branches += metrics.max_covered_mcdc_branches
            self.grand_total_mcdc_branches += metrics.mcdc_branches
            self.grand_total_max_covered_mcdc_pairs += metrics.max_covered_mcdc_pairs
            self.grand_total_mcdc_pairs += metrics.mcdc_pairs
            self.grand_total_max_covered_function_calls += metrics.max_covered_function_calls
            self.grand_total_function_calls += metrics.function_calls

            try:
                if self.has_function_coverage:
                    self.grand_total_max_covered_functions += metrics.covered_functions
                    self.grand_total_max_coverable_functions += metrics.functions
            except:
                pass

            if "BASIS_PATH" in str(cov_type):
                (cov, total) = srcFile.basis_paths_coverage
                self.grand_total_total_basis_path += total
                self.grand_total_cov_basis_path += cov


        self.coverage = self.grand_total_coverage(overallCoverageTypes)
        self.num_units = len(self.our_units)

#
# BaseGenerateXml - Generate the XML Modified 'Emma' coverage data
#
class GenerateManageXml (BaseGenerateXml):
    def __init__(self, cover_report_name, verbose, manage_path, use_ci):
        super(GenerateManageXml, self).__init__(cover_report_name, verbose, use_ci)
        self.using_cover = True
        from vector.apps.DataAPI.manage_api import VCProjectApi

        self.api = VCProjectApi(manage_path)

    def write_coverage_data(self): 
        data = "  <combined-coverage type=\"complexity, %%\" value=\"0%% ({} / 0)\"/>\n".format(self.grand_total_complexity)
        if self.coverage["statement"]: 
            data +=  "  <combined-coverage type=\"statement, %%\" value=\"{}\"/>\n".format(self.coverage["statement"])
        if self.coverage["branch"]:
            data += "  <combined-coverage type=\"branch, %%\" value=\"{}\"/>\n".format(self.coverage["branch"])
        if self.coverage["mcdc"]:
            data += "  <combined-coverage type=\"mcdc, %%\" value=\"{}\"/>\n".format(self.coverage["mcdc"])
        if self.coverage["basispath"]:
            data +=        "  <combined-coverage type=\"basispath, %%\" value=\"{}\"/>\n".format(self.coverage["basispath"])
        if self.coverage["function"]:
            data +=        "  <combined-coverage type=\"function, %%\" value=\"{}\"/>\n".format(self.coverage["function"])
        if self.coverage["functioncall"]:
            data +=        "  <combined-coverage type=\"functioncall, %%\" value=\"{}\"/>\n".format(self.coverage["functioncall"])
        self.fh.write(data.encode(self.encFmt, "replace"))

    def __del__(self):
        try:
            self.api.close()
        except:
            pass

# GenerateManageXml

    def generate_cover(self):
        self.units = self.api.project.cover_api.File.all()
        self._generate_cover(None)
        self.start_cov_file()
        self.write_coverage_data()
        self.end_cov_file()
        self.api.close()
        
##########################################################################
# This class generates the XML (Junit based) report for dynamic tests and
# the XML (Emma based) report for Coverage results
#
# In both cases these are for a single environment
#
class GenerateXml(BaseGenerateXml):

    def __init__(self, FullManageProjectName, build_dir, env, compiler, testsuite, cover_report_name, jenkins_name, unit_report_name, jenkins_link, jobNameDotted, verbose = False, cbtDict= None, use_ci = False):
        super(GenerateXml, self).__init__(cover_report_name, verbose, use_ci)

        self.FullManageProjectName = FullManageProjectName
        
        ## use hash code instead of final directory name as regression scripts can have overlapping final directory names
        build_dir = build_dir.replace("\\","/")
        if build_dir.endswith("/."):
            build_dir = build_dir.replace("/.","")
        build_dir_4hash = build_dir.upper()
        build_dir_4hash = "/".join(build_dir_4hash.split("/")[-2:])

        # Unicode-objects must be encoded before hashing in Python 3
        if sys.version_info[0] >= 3:
            build_dir_4hash = build_dir_4hash.encode(self.encFmt)

        self.hashCode = hashlib.md5(build_dir_4hash).hexdigest()

        if verbose:
            print ("HashCode: " + self.hashCode + "for build dir: " + build_dir)

        self.build_dir = build_dir
        self.env = env
        self.compiler = compiler
        self.testsuite = testsuite
        self.cover_report_name = cover_report_name
        self.jenkins_name = jenkins_name
        self.unit_report_name = unit_report_name
        self.jenkins_link = jenkins_link
        self.jobNameDotted = jobNameDotted
        self.using_cover = False
        cov_path = os.path.join(build_dir,env + '.vcp')
        unit_path = os.path.join(build_dir,env + '.vce')
        self.failed_count = 0
        self.passed_count = 0
        self.useStartLine = False
        self.noResults = False
        self.report_failed_only = False
        self.cbtDict = None
        
        if os.path.exists(cov_path) and os.path.exists(cov_path[:-4]):
            self.using_cover = True
            try:
                self.api = CoverApi(cov_path)
            except:
                self.api = None
                return
            
        elif os.path.exists(unit_path) and os.path.exists(unit_path[:-4]):
            self.using_cover = False
            try:
                self.api = UnitTestApi(unit_path)
            except:
                self.api = None

                return
                
            if self.api.environment.status != ENVIRONMENT_STATUS_TYPE_T.NORMAL:
                self.api.close()
                self.api = None
                return
            
        else:
            self.api = None
            if verbose:
                print("Error: Could not determine project type for {}/{}".format(build_dir, env))
                print("       {}/{}/{}".format(compiler, testsuite, env))
            return

        self.api.commit = dummy
        self.failed_count = 0
        self.passed_count = 0

#
# GenerateXml - add any compound tests to the unit report
#
    def add_compound_tests(self):
        for tc in self.api.TestCase.all():
            if tc.kind == TestCase.KINDS['compound']:
                if not tc.for_compound_only:
                    self.write_testcase(tc, "<<COMPOUND>>", "<<COMPOUND>>")

#
# GenerateXml - add any intialisation tests to the unit report
#
    def add_init_tests(self):
        for tc in self.api.TestCase.all():
            if tc.kind == TestCase.KINDS['init']:
                if not tc.for_compound_only:
                    self.write_testcase(tc, "<<INIT>>", "<<INIT>>")

#
# GenerateXml - Find the test case file
#
    def generate_unit(self):
         
        if isinstance(self.api, CoverApi):

            try:
                from vector.apps.DataAPI.vcproject_api import VCProjectApi
                self.start_system_test_file()
                api = VCProjectApi(self.FullManageProjectName)
                
                for env in api.Environment.all():
                    if env.compiler.name == self.compiler and env.testsuite.name == self.testsuite and env.name == self.env and env.system_tests:
                        for st in env.system_tests:
                            pass_fail_rerun = ""
                            if st.run_needed and st.type == 2: #SystemTestType.MANUAL:
                                pass_fail_rerun =  ": Manual system tests can't be run in Jenkins"
                            elif st.run_needed:
                                pass_fail_rerun =  ": Needs to be executed"
                            elif st.passed:
                                pass_fail_rerun =  ": Passed"
                            else:
                                pass_fail_rerun =  ": Failed"
                                
                            level = env.compiler.name + "/" + env.testsuite.name + "/" + env.name
                            if self.verbose:
                                print (level, st.name, pass_fail_rerun)
                            self.write_testcase(st, level, st.name)
                from generate_qa_results_xml import saveQATestStatus
                saveQATestStatus(self.FullManageProjectName)

                api.close()

            except ImportError as e:
                from generate_qa_results_xml import genQATestResults
                pc,fc = genQATestResults(self.FullManageProjectName, self.compiler+ "/" + self.testsuite, self.env, True, self.encFmt)
                self.failed_count += fc
                self.passed_count += pc
                return

        else:

            try:
                self.start_unit_test_file()
                self.add_compound_tests()
                self.add_init_tests()
                for unit in self.api.Unit.all():
                    if unit.is_uut:
                        for func in unit.functions:
                            if not func.is_non_testable_stub:
                                for tc in func.testcases:
                                    if not self.isTcPlaceHolder(tc):
                                        if not tc.for_compound_only or tc.testcase_status == "TCR_STRICT_IMPORT_FAILED":
                                            self.write_testcase(tc, tc.function.unit.name, tc.function.display_name, unit = unit)

            except AttributeError as e:
                import traceback
                traceback.print_exc()

        self.end_test_results_file()

#
# GenerateXml - write the end of the jUnit XML file and close it
#
    def isTcPlaceHolder(self, tc):
        placeHolder = False
        try:
            vctMap = tc.is_vct_map
        except:
            vctMap = False
        try:
            vcCodedTestMap = tc.is_coded_tests_map
        except:
            vcCodedTestMap = False
        try:
            if tc and len(tc.variant_logic) > 0 and tc.execution_status == 'EXEC_VARIANT_LOGIC_FALSE':
                vcVariantTestSkipped = True
            else:
                vcVariantTestSkipped = False
        except:
            vcVariantTestSkipped = False

        # Placeholder "testcases" that need to be ignored
        if tc.is_csv_map or vctMap or vcCodedTestMap or vcVariantTestSkipped:
            placeHolder = True

        return placeHolder

#
# Internal - start the JUnit XML file
#
    def start_system_test_file(self):
        if self.verbose:
            print("  Writing testcase xml file:        {}".format(self.unit_report_name))

        self.fh = open(self.unit_report_name, "wb")
        errors = 0
        failed = 0
        success = 0                                            
        
        from vector.apps.DataAPI.vcproject_api import VCProjectApi 
        api = VCProjectApi(self.FullManageProjectName)
        
        for env in api.Environment.all():
            if env.compiler.name == self.compiler and env.testsuite.name == self.testsuite and env.name == self.env and env.system_tests:
                for st in env.system_tests:
                    if st.passed == st.total:
                        success += 1
                        self.passed_count += 1
                    else:
                        failed += 1
                        errors += 1  
                        self.failed_count += 1
        api.close()            

        data =  "<?xml version=\"1.0\" encoding=\{}\"?>\n".format(self.encFmt)         
        data += "<testsuites>\n"
        data += "    <testsuite errors=\"{}\" tests=\"{}\" failures=\"{}\" name=\"{}\" id=\"1\">\n".format(errors, success+failed+errors, failed, escape(self.env, quote=False))
        
        self.fh.write(data.encode(self.encFmt, "replace"))
                
    def start_unit_test_file(self):
        if self.verbose:
            print("  Writing testcase xml file:        {}".format(self.unit_report_name))

        self.fh = open(self.unit_report_name, "wb")
        errors = 0
        failed = 0
        success = 0                                            
        
        for tc in self.api.TestCase.all():        
            if (not tc.for_compound_only or tc.testcase_status == "TCR_STRICT_IMPORT_FAILED") and not self.isTcPlaceHolder(tc):
                if not tc.passed:
                    self.failed_count += 1
                    failed += 1
                    if tc.execution_status != "EXEC_SUCCESS_FAIL ":
                        errors += 1
                else:
                    success += 1
                    self.passed_count += 1
                    
        data = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        data += "<testsuites>\n"
        data += "    <testsuite errors=\"{}\" tests=\"{}\" failures=\"{}\" name=\"{}\" id=\"1\">\n".format(
            errors,
            success+failed+errors, 
            failed, 
            escape(self.env, quote=False)
        )
        
        self.fh.write(data.encode(self.encFmt, "replace"))

#
# GenerateXml - write a testcase to the jUnit XML file
#
    def write_testcase(self, tc, unit_name, func_name, st_is_monitored = False, unit = None):

        fpath = ""
        startLine = ""
        unitName = ""

        unitName = unit_name

        if self.noResults:
            return

        if self.report_failed_only and not self.testcase_failed(tc):
            return

        if unit:
            try:
                filePath = unit.sourcefile.normalized_path(normcase=False)
            except:
                filePath = unit.sourcefile.normalized_path

            try:
                prj_dir = os.environ['WORKSPACE'].replace("\\","/") + "/"
            except:
                prj_dir = os.getcwd().replace("\\","/") + "/"

            try:
                fpath = os.path.relpath(filePath,prj_dir).replace("\\","/")
            except:
                fpath = filePath.replace("\\","/")

            if self.useStartLine:
                try:
                    startLine = str(tc.function.start_line)
                except:
                    try:
                        startLine = list(tc.cover_data.covered_statements)[0].start_line
                    except:
                        startLine = "0"
                        print("failed to access any start_line ", self.env, func_name, tc.name)
            else:
                startLine = "0"

            unitName = unit.name

        isSystemTest = False
        
        try:
            from vector.apps.DataAPI.manage_models import SystemTest
            if (isinstance(tc, SystemTest)):
                isSystemTest = True
        except:
            pass

        start_tdo = datetime.now()
        end_tdo   = None

        # don't do CBT analysis on migrated cover environments
        if isSystemTest and not st_is_monitored:
            tcSkipped = False

        # If cbtDict is None, no build log was passed in...don't mark anything as skipped
        elif self.cbtDict == None:
            tcSkipped = False

        # else there is something check , if the length of cbtDict is greater than zero
        elif len(self.cbtDict) > 0:
            tcSkipped, start_tdo, end_tdo = self.was_test_case_skipped(tc,"/".join([unit_name, func_name, tc.name]),isSystemTest)

        # finally - there was nothing to check
        else:
            tcSkipped = False

        if end_tdo:
            deltaTimeStr = str((end_tdo - start_tdo).total_seconds())
        else:
            deltaTimeStr = "0.0"

        unit_name = escape(unit_name, quote=False)
        func_name = escape(func_name, quote=True)
        tc_name = escape(tc.name, quote=False)
        compiler = escape(self.compiler, quote=False).replace(".","")
        testsuite = escape(self.testsuite, quote=False).replace(".","")
        envName = escape(self.env, quote=False).replace(".","")

        classname = compiler + "." + testsuite + "." + envName
        extra_message = ""
        status = ""
        control_flow_fail = False
        exception_fail = False
        signal_fail = False

        if isSystemTest:
            if fpath == "":
                fpath = tc_name
                
            tc_name_full =  classname + "." + tc_name
            exp_total = tc.total
            exp_pass = tc.passed
            extra_message = "System Test Build Status: " + tc.build_status + ". System Test: " + tc.name + ". "
            if tc.run_needed and tc.type == 2: #SystemTestType.MANUAL:
                status = "notrun"
                extra_message += "Manual system tests can't be run in CI tools"
                tc.passed = 1
            elif tc.run_needed:
                status = "notrun"
                extra_message += "Needs to be executed"
                tc.passed = 1
            elif tc.passed > 0 and tc.passed == tc.total:
                status = "passed"
                extra_message += "Passed"
            else:
                status = "failed"
                extra_message += "Failed {} / {} ".format(tc.passed, tc.total)
                tc.passed = 0

        else:
            tc_name_full =  unit_name + "." + func_name + "." + tc_name
            summary = tc.history.summary
            exp_total = summary.expected_total
            exp_pass = exp_total - summary.expected_fail
            
            if summary.control_flow_fail > 0:
                control_flow_fail = True
            
            if summary.unexpected_exceptions > 0:
                exception_fail = True
            
            if summary.signals > 0:
                signal_fail = True
            
            exp_pass += summary.control_flow_total - summary.control_flow_fail
            exp_total += summary.control_flow_total + summary.signals + summary.unexpected_exceptions

            if tc.testcase_status == "TCR_STRICT_IMPORT_FAILED":
                status = "failed"
                extra_message = "Strict Test Import Failure."
            # Failure takes priority
            elif tc.status != "TC_EXECUTION_NONE":
                extra_message, status = self.convertExecStatus(tc.execution_status)
            else:
                status = "notrun"
                extra_message = "Test was not executed"
                
        extra_message = escape(extra_message, quote=False)
        extra_message = extra_message.replace("\"","")
        extra_message = extra_message.replace("\n","&#xA;")
        extra_message = extra_message.replace("\r","")

        if tc.passed == None:
            status = "skipped"
            extraStatus = "<skipped/>"

        elif not tc.passed:
            whyFail = ""
            expectedResultsFailure = ""
            
            if exception_fail:
                whyFail += "Unexpected exception failure. "
                
            if signal_fail:
                whyFail += "Signal failure. "
                
            if control_flow_fail:
                whyFail += "Control flow failure. "
                expectedResultsFailure = "Control flow values" 
                
            if tc.history.summary.expected_total:
                whyFail += "Expected values failure. "
                if len(expectedResultsFailure) > 0:
                    expectedResultsFailure += " and "
                expectedResultsFailure += "Expected values totals"

            if tcSkipped:
                status = "skipped"
                extraStatus = "<failure type=\"failure\" message=\"{}. {}{}: {}/{}\"/>".format(extra_message, whyFail, expectedResultsFailure, exp_pass, exp_total)
            else:
                extraStatus = "<failure type=\"failure\" message=\"{}. {}{}: {}/{}\"/>".format(extra_message, whyFail, expectedResultsFailure, exp_pass, exp_total)

        elif tcSkipped:
            extraStatus = "<skipped/>"
        else:
            extraStatus = ""


        testcaseString ='        <testcase name="%s" classname="%s" time="%s" file="%s" status="%s"%s'
        if extraStatus != "":
            extraXmlTag = ">\n            " + extraStatus + "\n        </testcase>\n"
        else:
            extraXmlTag = "/>\n" 
            
        data = testcaseString % (tc_name_full, classname, deltaTimeStr, fpath, status, extraXmlTag)  

        self.fh.write(data.encode(self.encFmt, "replace"))   
            
#
# Internal - no support for skipped test cases yet
#
    def was_test_case_skipped(self, tc, searchName, isSystemTest):
        return False                     
        try:
            if isSystemTest:
                compoundTests, initTests,  simpleTestcases = self.cbtDict[self.hashCode]
                # use tc.name because system tests aren't for a specific unit/function
                if tc.name in simpleTestcases.keys():
                    return [False, simpleTestcases[tc.name][0], simpleTestcases[tc.name][1]]
                else:
                    self.__print_test_case_was_skipped(searchName, tc.passed)
                    return [True, None, None]
            else:
                #Failed import TCs don't get any indication in the build.log
                if tc.testcase_status == "TCR_STRICT_IMPORT_FAILED":
                    return [False, None, None]

                compoundTests, initTests,  simpleTestcases = self.cbtDict[self.hashCode]

                #Recursive Compound don't get any named indication in the build.log
                if tc.kind == TestCase.KINDS['compound'] and (tc.testcase_status == "TCR_RECURSIVE_COMPOUND" or searchName in compoundTests.keys()):
                    return [False, compoundTests[searchName][0], compoundTests[searchName][1]]
                elif tc.kind == TestCase.KINDS['init'] and searchName in initTests.keys():
                    return [False, initTests[searchName][0], initTests[searchName][1]]
                elif searchName in simpleTestcases.keys() or tc.testcase_status == "TCR_NO_EXPECTED_VALUES":
                    #print ("found" , self.hashCode, searchName, str( simpleTestcases[searchName][1] - simpleTestcases[searchName][0]))
                    return [False, simpleTestcases[searchName][0], simpleTestcases[searchName][1]]
                else:
                    self.__print_test_case_was_skipped(searchName, tc.passed)
                    return [True, None, None]
        except KeyError:
            self.__print_test_case_was_skipped(tc.name, tc.passed)
            return [True, None, None]
        except Exception as e:
            parse_traceback.parse(traceback.format_exc(), self.print_exc, self.compiler,  self.testsuite,  self.env,  self.build_dir)
            if self.print_exc:
                print ("CBT Dictionary:" + self.cbtDict, width = 132)
                pprint(self.cbtDict, width = 132)
                
#
# Internal - write the end of the jUnit XML file and close it
#
    def end_test_results_file(self):
        self.fh.write("   </testsuite>\n".encode(self.encFmt, "replace"))
        self.fh.write("</testsuites>\n".encode(self.encFmt, "replace")) 
        self.fh.close()

#
# Internal - write the start of the coverage file for and environment
#
    def start_cov_file_environment(self):
        self.start_cov_file()
        data = ""
        data += "  <stats>\n"
        data += "    <environments value=\"1\"/>\n"
        data += "    <units value=\"{}\"/>\n".format(self.num_units)
        data += "    <subprograms value=\"{}\"/>\n".format(self.num_functions)
        data += "  </stats>\n"
        data += "  <data>\n"
        data += "    <all name=\"all environments\">\n"
        if self.coverage["statement"]:
            data += "      <coverage type=\"statement, %%\" value=\"{}\"/>\n".format(self.coverage["statement"])
        if self.coverage["branch"]:
            data += "      <coverage type=\"branch, %%\" value=\"{}\"/>\n".format(self.coverage["branch"])
        if self.coverage["mcdc"]:
            data += "      <coverage type=\"mcdc, %%\" value=\"{}\"/>\n".format(self.coverage["mcdc"])
        if self.coverage["basispath"]:
            data += "      <coverage type=\"basispath, %%\" value=\"{}\"/>\n".format(self.coverage["basispath"])
        if self.coverage["function"]:
            data += "      <coverage type=\"function, %%\" value=\"{}\"/>\n".format(self.coverage["function"])
        if self.coverage["functioncall"]:
            data += "      <coverage type=\"functioncall, %%\" value=\"{}\"/>\n".format(self.coverage["functioncall"])
        data += "      <coverage type=\"complexity, %%\" value=\"0%% ({} / 0)\"/>\n".format(self.grand_total_complexiy)
        data += "\n"

        data += "      <environment name=\"{}\">\n".format(escape(self.jenkins_name, quote=False))
        if self.coverage["statement"]:
            data += "        <coverage type=\"statement, %%\" value=\"{}\"/>\n".format(self.coverage["statement"])
        if self.coverage["branch"]:
            data += "        <coverage type=\"branch, %%\" value=\"{}\"/>\n".format(self.coverage["branch"])
        if self.coverage["mcdc"]:
            data += "        <coverage type=\"mcdc, %%\" value=\"{}\"/>\n".format(self.coverage["mcdc"])
        if self.coverage["basispath"]:
            data += "        <coverage type=\"basispath, %%\" value=\"{}\"/>\n".format(self.coverage["basispath"])
        if self.coverage["function"]:
            data += "        <coverage type=\"function, %%\" value=\"{}\"/>\n".format(self.coverage["function"])
        if self.coverage["functioncall"]:
            data += "        <coverage type=\"functioncall, %%\" value=\"{}\"/>\n".format(self.coverage["functioncall"])
        data += "        <coverage type=\"complexity, %%\" value=\"0%% ({} / 0)\"/>\n".format(self.grand_total_complexity)
        self.fh.write(data.encode(self.encFmt, "replace"))

#
# Internal - write the end of the coverage file and close it
#
    def end_cov_file_environment(self):
        self.fh.write('      </environment>\n'.encode(self.encFmt, "replace"))
        self.fh.write('    </all>\n'.encode(self.encFmt, "replace"))
        self.fh.write('  </data>\n'.encode(self.encFmt, "replace"))
        self.end_cov_file()

#
# Internal - write the units to the coverage file
#
    def write_cov_units(self):
        for unit in self.our_units:
            data = ""
            data += "        <unit name=\"{}\">\n".format(escape(unit["unit"].name, quote=False))
            if unit["coverage"]["statement"]:
                data += "          <coverage type=\"statement, %%\" value=\"{}\"/>\n".format(unit["coverage"]["statement"])
            if unit["coverage"]["branch"]:
                data += "          <coverage type=\"branch, %%\" value=\"{}\"/>\n".format(unit["coverage"]["branch"])
            if unit["coverage"]["mcdc"]:
                data += "          <coverage type=\"mcdc, %%\" value=\"{}\"/>\n".format(unit["coverage"]["mcdc"])
            if unit["coverage"]["basispath"]:
                data += "          <coverage type=\"basispath, %%\" value=\"{}\"/>\n".format(unit["coverage"]["basispath"])
            if unit["coverage"]["function"]:
                data += "          <coverage type=\"function, %%\" value=\"{}\"/>\n".format(unit["coverage"]["function"])
            if unit["coverage"]["functioncall"]:
                data += "          <coverage type=\"functioncall, %%\" value=\"{}\"/>\n".format(unit["coverage"]["functioncall"])
            data += "          <coverage type=\"complexity, %%\" value=\"0%% (%s / 0)\"/>\n".format(unit["complexity"])

            for func in unit["functions"]:
                if self.using_cover:
                    func_name = escape(func["func"].name, quote=True)
                    data += "          <subprogram name=\"{}\">\n".format(func_name)
                else:
                    func_name = escape(func["func"].display_name, quote=True)
                    data += "          <subprogram name=\"{}\">\n".format(func_name)
                if func["coverage"]["statement"]:
                    data += "            <coverage type=\"statement, %%\" value=\"{}\"/>\n".format(func["coverage"]["statement"])
                if func["coverage"]["branch"]:
                    data += "            <coverage type=\"branch, %%\" value=\"{}\"/>\n".format(func["coverage"]["branch"])
                if func["coverage"]["mcdc"]:
                    data += "            <coverage type=\"mcdc, %%\" value=\"{}\"/>\n".format(func["coverage"]["mcdc"])
                if func["coverage"]["basispath"]:
                    data += "            <coverage type=\"basispath, %%\" value=\"{}\"/>\n".format(func["coverage"]["basispath"])
                if func["coverage"]["function"]:
                    data += "            <coverage type=\"function, %%\" value=\"{}\"/>\n".format(func["coverage"]["function"])
                if func["coverage"]["functioncall"]:
                    data += "            <coverage type=\"functioncall, %%\" value=\"{}\"/>\n".format(func["coverage"]["functioncall"])
                data += "            <coverage type=\"complexity, %%\" value=\"0%% ({} / 0)\"/>\n".format(func["complexity"])

                data += "          </subprogram>\n"
            data += "        </unit>\n"     
            self.fh_write(data.encode(self.encFmt, "replace"))

#
# Generate the XML Modified 'Emma' coverage data
#
    def generate_cover(self):
        self.units = []
        if self.using_cover:
            self.units = self.api.File.all()
            self.units.sort(key=lambda x: (x.coverage_type, x.unit_index))
        else:
            self.units = self.api.Unit.all()
            
        # unbuilt (re: Error) Ada environments causing a crash
        try:
            cov_type = self.api.environment.coverage_type_text
        except Exception as e:
            print("Couldn't access coverage information...skipping.  Check console for environment build/execution errors")
            return
            
        self._generate_cover(cov_type)

        self.start_cov_file_environment()
        self.write_cov_units()
        self.end_cov_file_environment()

    def __print_test_case_was_skipped(self, searchName, passed):
        if self.verbose:
            print("skipping ", self.hashCode, searchName, passed)

def __generate_xml(xml_file, envPath, env, xmlCoverReportName, xmlTestingReportName, teePrint):
    if xml_file.api == None:
        teePrint.teePrint ("\nCannot find project file (.vcp or .vce): " + envPath + os.sep + env)

    elif isinstance(xml_file, CoverApi):
        xml_file.generate_cover()
        teePrint.teePrint ("\nvectorcast-coverage plugin for Jenkins compatible file generated: " + xmlCoverReportName)

    else:
        xml_file.generate_unit()
        teePrint.teePrint ("\nJunit plugin for Jenkins compatible file generated: " + xmlTestingReportName)

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('environment', help='VectorCAST environment name')
    parser.add_argument('-v', '--verbose', default=False, help='Enable verbose output', action="store_true")
    parser.add_argument('--ci', help='Use continuous integration licenses', action="store_true", default=False)
    args = parser.parse_args()

    envPath = os.path.dirname(os.path.abspath(args.environment))
    env = os.path.basename(args.environment)

    if env.endswith(".vcp"):
        env = env[:-4]

    if env.endswith(".vce"):
        env = env[:-4]

    jobNameDotted = env
    jenkins_name = env
    jenkins_link = env
    xmlCoverReportName = "coverage_results_" + env + ".xml"
    xmlTestingReportName = "test_results_" + env + ".xml"

    xml_file = GenerateXml(env,
                           envPath,
                           env, "", "", 
                           xmlCoverReportName,
                           jenkins_name,
                           xmlTestingReportName,
                           jenkins_link,
                           jobNameDotted, 
                           args.verbose, 
                           None,
                           args.ci)

    if xml_file.api == None:
        print ("\nCannot find project file (.vcp or .vce): " + envPath + os.sep + env)
        
    elif xml_file.using_cover:
        xml_file.generate_cover()
        print ("\nvectorcast-coverage plugin for Jenkins compatible file generated: " + xmlCoverReportName)

    else:
        xml_file.generate_unit()
        print ("\nJunit plugin for Jenkins compatible file generated: " + xmlTestingReportName)
