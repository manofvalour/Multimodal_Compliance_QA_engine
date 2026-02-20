import json
import os
import logging
import re
from typing import Any, Dict, List

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


## import state schema
from backend.src.graph.state import VideoAuditState, ComplianceIssue

## import service
from backend.src.services.video_indexer import VideoIndexerService

## configute the logger
logger= logging.getlogger("brand-gurdian")
logging.basicConfig(level=logging.INFO)

## NODE 1: Indexer
## function responsible for converting video to text
def video_indexer_node(state: VideoAuditState)-> Dict[str, Any]:
    """
    This downloads the youtube video from the url
    and upload to azure video indexer, then
    extracts the insights"""

    video_url = state.get('video_url')
    video_id_input = state.get('video_id', 'video_demo')

    logger.info(f"--- [Node:Indexer] Processing: {video_url}")

    local_filename = 'temp_audit_video.mp4'

    try:
        vi_servie = VideoIndexerService()
        ##download the video and save to local storage
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            local_path = vi_service.downloa_youtube(video_url, output_path=local_filename)
        else:
            raise Exception("Unsupported video source. Only YouTube videos are supported.")
        
        ## uploading the videio to azure video indexer and extract insights
        azure_video_id = vi_service.upload_to_azure_video_indexer(local_path, video_id_input)
        logger.info(f"Video uploaded to Azure Video Indexer with ID: {azure_video_id}")

        ##cleanup
        if os.path.exists(local_path):
            os.remove(local_path)

        # wait for processing
        raw_insights = vi_service.wait_for_processing(azure_video_id)
        
        # extract the relevant information from the insight generated
        clean_data = vi_service.extract_data(raw_insights)
        logger.info((f"--- [NODE: Indexer] Extraction completed for video: {video_url}---"))

        return clean_data
    
    except Exception as e:
        logger.error(f"Video Indext Failed: {e}")
        return {
            "errors": [str(e)],
            "final_status": "FAIL",
            "transcript" : "",
            "ocr_text" : [],
        }
    
## Node 2 : Compliance Auditor Node
def audio_content_node(state: VideoAuditState)-> Dict[str, Any]:
    """
    This node takes the transcript and ocr text extracted from the video
    and analyze them to identify potential compliance issues.
    """

    logger.info("----[NODE: Auditior] quering the nowledge base and LLM")
    transcript = state.get("transcript", "")

    if not transcript:
        logger.warning("No transcript available for analysis.")
        return {
            "final_status": "FAIL",
            "final_report": "aUDIT SKIPPED BECAUSE VIDEO PROCESSING FAILED (no transcript available for analysis)"
        }
    
    # initialize clients
    llm = AzureChatOpenAI(
        azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature = 0.0
    )

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
    )

    vector_store = AzureSearch(
        azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key = os.getenv("AZURE_SEARCH_API_KEY"),
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embeding_function = embeddings.embed_query
    )

    ## RAG Retrieval
    ocr_text = state.get("ocr_text", [])
    query_text = f"{transcript} {''.join(ocr_text)}"
    docs = vector_store.similarity_search(query_text, k=3)
    retrieved_rules = "\n\n".join([doc.page_content for doc in docs])
    ##

    system_prompt = f"""
        You are a senior brand compliance auditor.
        OFFICIAL REGULATORY RULES:
        {retrieved_rules}
        1. Analyze the Transript and OCT text below.__doc__
        2. Identify Any violations of the rules.__doc__
        3. Return Strictly JSON  in the following format:
            {{
        "compiance_results":[
        {{
            "category": "Claim Validation",
            "severity": "CRITICAL",
            "description" : "Explanation of the violation.."Exception
        }}
    ],
    "status": "FAIL",
    "final_report": "Summary of findings..."
     }}

     If no violations are found, set "status" to "PASS" and "compliance results" to [].

     """
    
    user_message = f"""
        VIDEO_META_DATA : {state.get('video_metadata', {})}
        TRANSCRIPT : {transcript}
        ON_SCREEN TEXT (OCR) : {ocr_text}
        """
    
    try:
        response = llm.invoke([
            SystemMessage(content = system_prompt),
            HumanMessage(content=user_message)
        ])

        content = response.content
        if "```" in content:
            content = re.search(r"```(?:json)?(.?)```", content, re.DOTALL).group(1)
        audit_data = json.loads(content.strip())
        return {
            "compliance_results" : audit_data.get("compliance_results",[]),
            "final_status" : audit_data.get("status","FAIL"),
            "final_report" : audit_data.get("final_report", "No report generated")
        }
    
    except Exception as e:
        logger.error(f"system Error in Auditor Node : {str(str(e))}")
        #lgging the raw error
        logger.error(f"Raw LLM response: {response.ontent if 'respnse' in locals() else 'None'}")
        return {
            "errors" : [str(e)],
            "final_status": "FAIL"
        }