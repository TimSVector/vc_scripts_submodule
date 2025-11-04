import requests
import xml.etree.ElementTree as ET

import os, sys
import json
from vcast_utils import checkVectorCASTVersion

if not checkVectorCASTVersion(20, quiet = False):
    if __name__ != "__main__":
        raise ImportError("Cannot generate metrics.  Please updated VectorCAST")
    else:
        print("Cannot generate metrics.  Please updated VectorCAST")
        sys.exit(0)

from generate_metrics_md import generate_metrics_md
from pprint import pprint
import cobertura
try:
    import generate_results
except:
    try:
        import importlib
        generate_results = importlib.import_module("generate-results")
    except:
        import imp
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vc_script = os.path.join(script_dir, "generate-results.py")
        generate_results = imp.load_source("generate_results", vc_script)

encFmt = getVectorCASTEncoding()


PASS = u"\u2705"   
FAIL = u"\u274C"   
PARTIAL = u"\U0001F7E1"

severityArray = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

LOW = 0
MEDIUM = 1
HIGH = 2
CRITICAL = 3


# Parse Cobertura XML
def parse_cobertura(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    annotations = []
    for cls in root.findall(".//class"):
        file_path = cls.attrib['filename']
        for line in cls.findall("lines/line"):
            num = int(line.attrib['number'])
            hits = int(line.attrib['hits'])
            branch = line.attrib.get('branch', 'false')
            condition_coverage  = line.attrib.get('condition-coverage', '')
            functioncall_coverage = line.attrib.get('functioncall-coverage', '')
            mcdcpair_coverage = line.attrib.get('mcdcpair-coverage', '')

            summary = ""
            severityCount = 0

            if hits == 0:
                summary = "|{}No coverage".format(FAIL)
                severityCount = CRITICAL
                
            else:
                summary = "|ST{}".format(FAIL)
                summary = PASS + " ST" 
                severityCount = LOW
                if branch == 'true':
                    if condition_coverage.startswith("100.0%"):
                        #summary += " | {} BR: {}".format (PASS,condition_coverage)
                        summary += "|BR{}".format(PASS)
                        severityCount -= 1
                    elif condition_coverage.startswith("0.0%"):
                        #summary += " | {} BR: {}".format (FAIL,condition_coverage)
                        summary += "|BR{}".format(FAIL)
                        severityCount += 1
                    else:
                        #summary += " | {} BR: {}".format (PARTIAL,condition_coverage)
                        summary += "|BR{}".format(PARTIAL)
                        severityCount += 1

                if functioncall_coverage.startswith("100.0%"):
                    #summary += " | {} FC".format (PASS)
                    summary += " |FCC{}".format (PASS)
                    severityCount -= 1
                elif functioncall_coverage != '':
                    #summary += " | {} FC".format (FAIL)
                    summary += " |FCC{}".format (FAIL)
                    severityCount += 1
                    
                if mcdcpair_coverage.startswith("100.0%"):
                    #summary += " | {} MCDC: {}".format (PASS, mcdcpair_coverage)
                    summary += " |MCDC{}".format (PASS)
                    severityCount -= 1
                elif mcdcpair_coverage.startswith("0.0%"):
                    #summary += " | {} MCDC: {}".format (FAIL, mcdcpair_coverage)
                    summary += " |MCDC{}".format (FAIL)
                    severityCount += 1
                elif mcdcpair_coverage != '':
                    #summary += " | {} MCDC: {}".format (PARTIAL, mcdcpair_coverage)
                    summary += " |MCDC{}".format (PARTIAL)
                    severityCount += 1
                    
            if severityCount > CRITICAL: severityCount = CRITICAL
            if severityCount < LOW: severityCount = LOW
            
            annotations.append({
                "title": "Coverage",
                "annotation_type": "COVERAGE",
                "summary": summary,
                "severity": severityArray[severityCount],
                "path": file_path,
                "line": num,
                "external_id": "{}#{}".format(file_path,num)
                }
            )
            
    return annotations

def get_summary_string(type_str, rate):
    
    if rate == -1:
        return None
    
    return {"title" : type_str, "type" : "PERCENTAGE", "value": round(rate * 100.0,  2)}
        
    
def get_summary_resuts(xml_path, minimum_passing_coverage, verbose):
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    line = root
        
    line_rate                  = float(line.attrib.get('line-rate', -1))
    statement_rate             = float(line.attrib.get('statement-rate', -1))
    branch_rate                = float(line.attrib.get('branch-rate', -1))
    mcdcpair_coverage_rate     = float(line.attrib.get('mcdcpair-coverage-rate',-1))
    functioncall_coverage_rate = float(line.attrib.get('functioncall-coverage-rate', -1))
    function_coverage_rate     = float(line.attrib.get('function-coverage', -1))
    timestamp                  = line.attrib['timestamp']
    version                    = line.attrib['version'].rsplit(" ", 1)[0]
    
    summary = ""
    
    data = []
    
    if statement_rate == -1:
        summary = "No coverage available"
        overall_coverage = "FAIL"
    else:
        if statement_rate >= minimum_passing_coverage:
            overall_coverage = "PASS"
        else:
            overall_coverage = "FAIL"
        
        # If you ever have more coverage types, you can refactor like this:

        metrics = [
            ("Statement",     statement_rate),
            ("Branch",        branch_rate),
            ("MCDC Pair",     mcdcpair_coverage_rate),
            ("Function Call", functioncall_coverage_rate),
            ("Function ",     function_coverage_rate),
        ]

        data = [
            v
            for _, v in ((n, get_summary_string(n, rate)) for n, rate in metrics)
            if v is not None
        ]
        
    return data, timestamp, version, overall_coverage
    
# Send annotations in batches of 100
def send_metrics_annoations(annotationData, workspace, repo_slug, commit_hash, email, token, verbose):

    print("Sending metrics annotations")

    # CONFIGURATION
    report_id = "metrics-report"

    url = "https://api.bitbucket.org/2.0/repositories/{}/{}/commit/{}/reports/{}/annotations".format(workspace, repo_slug, commit_hash, report_id)

    headers = {"Accept": "application/json", "Content-Type": "application/json"},

    annotations = []
    
    for fname, summary, serverity  in annotationData:
        annotations.append({
            "title": "Metrics Report",
            "annotation_type": "COVERAGE",
            "summary": summary,
            "severity": serverity,
            "path": fname,
            "external_id": "{}#{}".format(fname,"FILE_METRIC"),
            "line" : 0
            }
        )

    for i in range(0, len(annotations), 100):
        batch = annotations[i:i+100]     
                                          
        if verbose:  
            print(json.dumps(annotations[1:10]))

        resp = requests.post(
            url, 
            auth=(email, token), 
            json=batch, 
            headers= {"Accept": "application/json", "Content-Type": "application/json"}
        )
        
        if resp.status_code != 200 or verbose:
            print("Batch {} response: {} {}".format(i//100+1,resp.status_code, resp.text))

    print("Complete")

def send_metrics_md_report_in_bitbucket(
    summary, 
    annotationData, 
    workspace, 
    repo_slug, 
    commit_hash, 
    email, 
    token, 
    link, 
    verbose):
    
    print("Sending metrics data in Markdown format for commit {}".format(commit_hash))

    # CONFIGURATION
    report_id = "metrics-report"

    url = "https://api.bitbucket.org/2.0/repositories/{}/{}/commit/{}/reports/{}".format(workspace, repo_slug, commit_hash, report_id)

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    report_payload = {
        "title": "Metrics Report",
        "details": summary,
        "report_type": "TEST",
        "reporter": "VectorCAST",
        "logo_url" : "https://raw.githubusercontent.com/jenkinsci/vectorcast-execution-plugin/master/src/main/webapp/icons/vector_favicon.png",
        "link" : link
    }
    
    sendData = json.dumps(report_payload, ensure_ascii=False).encode(encFmt, "replace")
    
    print(json.dumps(report_payload, indent = 2))
    
    if verbose:
        print("report_payload")
        print(json.dumps(report_payload, ensure_ascii=False, indent=2))

    headers = {
        "Accept": "application/json", 
        "Content-Type": "application/json; charset=" + encFmt
    }

    resp = requests.put(
        url,
        auth=(email, token),
        data=sendData,
        headers=headers,
        timeout=30
    )

    if resp.status_code == 200:
        print("Metrics Reported Created")
    else:
        print("Metrics Reported Creation - FAILED")
        print("Metrics Report creation status:", resp.status_code)
        print("Response:", resp.text)

    send_metrics_annoations(annotationData, workspace, repo_slug, commit_hash, email, token, verbose)

def buildAndSendCoverage(mpName, filename, minimum_passing_coverage, verbose):

    workspace   = os.environ['BITBUCKET_WORKSPACE']
    repo_slug   = os.environ['BITBUCKET_REPO_SLUG']
    commit_hash = os.environ['BITBUCKET_COMMIT']
    bitbucket_api_token = os.environ['BITBUCKET_API_TOKEN']
    bitbucket_email = os.environ['BITBUCKET_EMAIL']

    annotations = parse_cobertura(filename)
    
    with open("coverage_results.json", "wb") as fd:
        fd.write(json.dumps(annotations, indent=2).encode(encFmt,'replace'))
      
    summary, annotation_data, link = generate_metrics_md(mpName)
    
    send_metrics_md_report_in_bitbucket(
        summary, annotation_data, 
        workspace, 
        repo_slug, 
        commit_hash, 
        bitbucket_email, 
        bitbucket_api_token, 
        link,
        verbose
    )

def cleanup(dirName, fname = ""):

    if fname == "":
        fname = "*.*"

    for file in glob.glob(os.path.join(dirName, fname)):
        try:
            os.remove(file);
        except:
            print("Error removing file after failed to remove directory: " +  file)

    try:
        shutil.rmtree(os.path.join(dirName))
    except:
        pass
        
def moveFiles(html_base_dir, verbose = False):
    try:
        basePath = os.environ['BITBUCKET_CLONE_DIR']
    except:
        print("$BITBUCKET_CLONE_DIR not set")
        basePath = "."

    html_dirs = [basePath, html_base_dir, "rebuild_reports"]
    
    for html_dir in html_dirs:
        for html in (
            glob.glob(os.path.join(html_dir, "*.html")) +
            glob.glob(os.path.join(html_dir, "*.css")) +
            glob.glob(os.path.join(html_dir, "*.png"))
        ):
            # compute relative path to repository root
            rel_path = os.path.relpath(html, start=basePath)
    
            # replicate that structure under reports/html/
            dest = os.path.join("reports/html", rel_path)
    
            os.makedirs(os.path.dirname(dest), exist_ok=True)
    
            try:
                if os.path.abspath(html) != os.path.abspath(dest):
                    shutil.copy2(html, dest)
                    if verbose: print("Saving file here: {}".format(dest))
            except Exception as e:
                print("Error copying {} --> {}\n{}".format(html, dest, e))

     
def run(fullMp, minimum_passing_coverage, useCi, html_base_dir, source_root, verbose):
    
    if not checkVectorCASTVersion(21):
        print("Cannot create Cobertura metrics to send to BitBucket. Please upgrade VectorCAST")
    else:
        import cobertura
        import send_cobertura_to_bitbucket

        cleanup("coverage")
        cleanup("test-results")
        cleanup("reports")

        if not os.path.isdir("coverage"):
            os.makedirs("coverage")
        if not os.path.isdir("test-results"):
            os.makedirs("test-results")
        if not os.path.isdir("reports/html"):
            os.makedirs("reports/html")

        print("Generating and sending extended cobertura metrics to BitBucket")
        cobertura.generateCoverageResults(
            fullMp,
            azure = False,
            xml_data_dir = "coverage",
            verbose = verbose,
            extended=True,
            source_root = source_root)

        print("Creating JUnit metrics to be read by BitBucket")
        failed_count, passed_count = generate_results.buildReports(
                FullManageProjectName = fullMp,
                level = None,
                envName = None,
                generate_individual_reports = False,
                timing = False,
                cbtDict = None,
                use_archive_extract = False,
                report_only_failures = False,
                no_full_report = False,
                use_ci = useCi,
                xml_data_dir = "test-results",
                useStartLine = False)

        name  = os.path.splitext(os.path.basename(fullMp))[0] + ".xml"
        fname = os.path.join("coverage","cobertura","coverage_results_" + name)

        if os.path.exists(fname):
            new_name = os.path.join("coverage","cobertura","cobertura.xml")
            os.rename(fname, new_name)
            fname = new_name

        print("\nProcessing {} and sending to BitBucket: ".format(fname))

        buildAndSendCoverage(
            fullMp,
            filename = fname,
            minimum_passing_coverage = minimum_passing_coverage,
            verbose = verbose
        )
        
        moveFiles(
            html_base_dir = html_base_dir,
            verbose = verbose
        )

    
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Send coverage information to BitBucket."
    )
    
    parser.add_argument(
        "vcProject",
        help="Path to the VectorCAST Project",
        default="cobertura.xml"
    )

    parser.add_argument(
        "--minimum_passing_coverage",
        type=float,
        help="Minimum overall coverage required to pass (default 80 percent)",
        default=80
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output for debugging or detailed reporting",
        default = False
    )

    parser.add_argument(
        "--ci",
        action="store_true",
        help="Use CI licenses",
        default = False
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output for debugging or detailed reporting"
    )
    
    
    parser.add_argument(
        "--html_base_dir", 
        help='Set the base directory of the html_reports directory. The default is the workspace directory', 
        default = "html_reports"
    )
    
    parser.add_argument(
        '--source_root', 
        help='Set the absolute path for the source file in coverage reporting', 
        default = ""
    )

    args = parser.parse_args()

    run(
        mpName = args.vcProject, 
        minimum_passing_coverage = args.minimum_passing_coverage, 
        useCi = args.ci,
        html_base_dir = args.html_base_dir,
        source_root = args.source_root,
        verbose = args.verbose
    )
    