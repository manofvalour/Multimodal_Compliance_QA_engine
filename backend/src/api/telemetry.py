## Azure opentelemetry integration
import os
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

## crete a dedicated logger
logger=logging.getLogger('brand-guardian-telemetry')

def setup_telemetry():
    """
    Initializes Azure Monitor OpenTelemetry
    Tracks: HTTP requests, database queries, errors, performace metrics
    sends this data to azure monitor

    It auto captures every API request
    No need to manually log each endpoint
    """

    ## retrieve connection string
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    ## CHECK if configured
    if not connection_string:
        logger.warning("No Instrumetation key found.Telemetry is DISABLED.")
        return 
    
    ## configure the aure monitor
    try:
        configure_azure_monitor(
            connection_string=connection_string,
            logger_name = 'brand-guardian-tracer',
        )

        logger.info("Azure Monitor Tracking Enabled and Connector")
    
    except Exception as e:
        logger.error(f"Failed to initialize Azure Monitor: {e}")
        


