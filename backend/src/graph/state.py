import operator
from typing import Annotated, List, Dict, Optional, Any, TypedDict

## define schema for a simple compliance result
# how the error report will look like
class ComplianceIssue(TypedDict):
    category: str
    description: str # speciific detail of violation
    severity: str #Critical | warining
    timestamp: Optional[str]

## define the global state of the system
## the state that get passed arround in the agentic workflow
class VideoAuditState(TypedDict):
    """
    Define the data schema of langgraph execution content
    Main container: holds all the information about the audit
    that the agents will read and update during the execution
    """

    ## input parameters
    video_url: str
    video_id: str

    # ingestion and extraction data
    local_file_path: Optional[str]
    video_metadata: Dict[str, Any] # {"duration: 120, "format": "mp4", "resolution": "1920x1080"}
    transript: Optional[str] ## fully extracted speech-to-text
    ocr_text : List[str] # text extracted from video frames

    ## analysis output
    ## stores the list of violation found by the agentic system
    compliance_results: Annotated[List[ComplianceIssue], operator.add] #"List of compliance issues detected in the video"]

    # final deliverables
    final_status: str #Pass | Fail
    final_report: str # markdown format

    ## system observability
    # errors: API timeout, system level errors
    errors: Annotated[List[str], operator.add] # "List of errors encountered during processing"]
