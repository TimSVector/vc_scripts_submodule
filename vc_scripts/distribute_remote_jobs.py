from vector.apps.DataAPI.vcproject_api import VCProjectApi 
import sys
import argparse
import os
import subprocess
import copy_build_dir
import incremental_build_report_aggregator 
import extract_build_dir
import merge_vcr

VCD = os.environ['VECTORCAST_DIR']

class DistributeRemoteJobs (object):
    def __init__(self):

        parser = argparse.ArgumentParser() 
        
        # running from manage        
        parser.add_argument('--project', '-p',     help='VectorCAST Project Project Name', default=None)
        parser.add_argument('--ci',                help='Use VectorCAST CI licenses', action="store_true", default=False)
        parser.add_argument('--incremental',       help='Using build-execute incremental (CBT)', action="store_true", default=False)
        parser.add_argument('--setup',             help='Commands to prepare the enviornment', dest="setupCmds",default="")
        parser.add_argument('--import-result',     help='Result file (.vcr) to use for CBT', dest="resultsFile",default=None)
        parser.add_argument('--update-result',     help='After execution is complete, update results file', dest="updateResultsFile",action="store_true", default=False)
        parser.add_argument('--dryrun',            help='Dry Run without build/execute', action="store_true", default=False)
        parser.add_argument('--verbose',           help='Verbose output', action="store_true", default=False)
        args = parser.parse_args()

        #save the argements to send to remote job
        self.remote_args = sys.argv[1:]

        self.dryrun = args.dryrun
        self.ci = args.ci
        
        self.setupCmds = args.setupCmds.split("\n")

        try:
            self.manageProject = os.environ['VCV_ENVIRONMENT_FILE']
        except:
            self.manageProject = args.project

        if self.manageProject is None:
            print ("\n** Use either --project [Manage Project Name] or enviroment variable VCV_ENVIRONMENT_FILE to specify the manage project name")
            sys.exit()
            
        elif not os.path.isfile(self.manageProject) and not os.path.isfile(self.manageProject + ".vcm"):
            raise IOError(self.manageProject + ' does not exist')
        else:
            self.mpName = self.manageProject.replace(".vcm","")
            self.mpDir = os.path.abspath(self.manageProject).rsplit(".",1)[0]
            os.environ['VCAST_MANAGE_PROJECT_DIRECTORY'] = self.mpDir
            
        if args.incremental:
            self.incremental = "--incremental"
        else:
            self.incremental = ""
           
        self.verbose = args.verbose
        self.resultsFile = args.resultsFile
               
        if self.resultsFile != None and not os.path.isfile(self.resultsFile):
            raise IOError(self.resultsFile + ' does not exist')
            
        try:
            ## gitlab specific
            self.workspace_dir = os.environ['CI_PROJECT_DIR'].replace("\\","/") + "/"
        except:
            self.workspace_dir = os.getcwd().replace("\\","/") + "/"
            
    def execManageCommand(self,command, clicast_args = None):
        if command.startswith("--"):
            exec_cmd = VCD + "/manage --project " + self.manageProject + " " + command
            
        if self.verbose or self.dryrun:
            print("RUN>> " + exec_cmd)
        
        if not self.dryrun:
            subp = subprocess.Popen(exec_cmd, shell=True)
            subp.wait()
            
    def run(self):
        
        print("RUN_LOCAL SETUP >> ", "\n".join(self.setupCmds))
        
        # not sure how to do this with kubernetes
        
        with VCProjectApi(self.manageProject) as api:
            env_list = api.Environment.filter(is_active__equals=True)
        
        for env in env_list:
            comp_name = env.compiler.name
            ts_name   = env.testsuite.name
            env_name  = env.name
            
            print("Remote Execute:",comp_name,ts_name,env_name)
            print("   REMOTE COPY      >> vc_scripts/*")
            
            if self.resultsFile:
                print("   REMOTE COPY      >>", self.resultsFile)

            print("   RUN_REMOTE       >> Get repo")
            print("   RUN_REMOTE SETUP >> ", "\n".join(self.setupCmds))
            print("   RUN_REMOTE       >> vpython vc_scripts/single_job_execute.py ", " ".join(self.remote_args),"--compiler ", comp_name, "--testsuite ", ts_name, "--environment ", env_name)
            print("   RUN_REMOTE       >> Copy-back *.tar, *.html, *.log\n")
        
        
        incremental_build_report_aggregator.parse_html_files(self.mpName)
        cover_db = os.path.join(self.mpDir,"build/vcast_data/cover.db")
        if os.path.isfile(cover_db):
            os.remove (cover_db)
            
        extract_build_dir.run()
        
        self.execManageCommand("--refresh")
        
        origVcrFile = self.mpName+"_results_orig.vcr"
        newVcrFile = self.resultsFile

        if self.resultsFile and self.updateResultsFile:
            if os.path.isfile(newVcrFile):
                shutil.copy(newVcrFile, origVcrFile)
                os.remove(self.resultsFile)
                
            self.execManageCommand("--export-result " + self.resultsFile)
            
            
            merge_vcr.run(origVcrFile, newVcrFile, verbose=self.verbose)
            

if __name__ == '__main__':
        
    rj = DistributeRemoteJobs()
    rj.run()
    
