import os
from dotenv import load_dotenv
import httpx
import asyncio
import logging

import json # For pretty printing in main_test

load_dotenv()
BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY")

# Configure logger - INFO level will be less verbose than DEBUG
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Set to logging.WARNING to be even quieter

# Define terminal states that stop polling
TERMINAL_SNAPSHOT_STATUSES = ["completed", "success", "failed", "error", "private"]
# Define states that indicate the process is ongoing
RUNNING_SNAPSHOT_STATUSES = ["running", "pending", "pending_acceptance"]


async def _poll_for_pitchbook_snapshot(
    client: httpx.AsyncClient,
    snapshot_id: str,
    initial_retry_delay_ms: int = 1000,
    max_retries: int = 3,
    max_delay_ms: int = 5000
) -> dict:
    """Polls Bright Data API for snapshot completion."""
    current_retry_delay_ms = initial_retry_delay_ms
    retries_left = max_retries
    snapshot_data = {} # Initialize to an empty dict

    headers = {"Authorization": f"Bearer {BRIGHTDATA_API_KEY}"}

    for attempt in range(max_retries + 1): # Loop for retries + initial attempt
        logger.debug(f"Polling attempt {attempt + 1}/{max_retries + 1} for snapshot {snapshot_id}. Delay: {current_retry_delay_ms if attempt > 0 else 0}ms.")
        try:
            response = await client.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                headers=headers,
                timeout=10.0,
            )

            if response.status_code == 202: # Still processing
                snapshot_data = {"status": "pending_acceptance"} # Internal status
            else:
                response.raise_for_status() # Raises for 4xx/5xx client/server errors
                snapshot_data = response.json()

            status = snapshot_data.get("status", "").lower() # Get status, default to empty string, convert to lower

            if status in TERMINAL_SNAPSHOT_STATUSES:
                if status in ["failed", "error"]:
                    logger.error(f"Snapshot {snapshot_id} failed with status '{status}'. Data: {snapshot_data}")
                elif status == "private":
                    logger.warning(f"Snapshot {snapshot_id} is '{status}'. Data may be limited. Data: {snapshot_data}")
                else: # completed, success
                    logger.info(f"Snapshot {snapshot_id} completed with status '{status}'.")
                return snapshot_data # Return data for all terminal states

            if status not in RUNNING_SNAPSHOT_STATUSES:
                logger.warning(f"Snapshot {snapshot_id} has unknown status: '{status}'. Data: {snapshot_data}")
                # Treat unknown status as potentially retryable for now, or could be terminal

            if attempt >= max_retries: # Check if it was the last attempt
                break # Exit loop if max retries reached

            logger.debug(f"Snapshot {snapshot_id} status '{status}'. Retrying...")
            await asyncio.sleep(current_retry_delay_ms / 1000)
            current_retry_delay_ms = min(int(current_retry_delay_ms * 1.5), max_delay_ms)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error polling snapshot {snapshot_id}: {e.response.status_code} - {e.response.text}")
            if e.response.status_code in [401, 403, 404] or attempt >= max_retries:
                raise Exception(f"Non-retryable or max retries HTTP error for snapshot {snapshot_id}. Response: {e.response.text}") from e
            await asyncio.sleep(current_retry_delay_ms / 1000)
            current_retry_delay_ms = min(int(current_retry_delay_ms * 1.5), max_delay_ms)
        except httpx.RequestError as e:
            logger.error(f"Request error polling snapshot {snapshot_id}: {e}")
            if attempt >= max_retries:
                raise Exception(f"Max retries on request error for snapshot {snapshot_id}") from e
            await asyncio.sleep(current_retry_delay_ms / 1000)
            current_retry_delay_ms = min(int(current_retry_delay_ms * 1.5), max_delay_ms)
        except Exception as e: # Catch any other unexpected error
            logger.error(f"Unexpected error polling snapshot {snapshot_id}: {e}")
            raise # Re-raise unexpected errors immediately

    logger.error(f"Maximum retries exceeded for snapshot {snapshot_id}. Last status: {snapshot_data.get('status', 'Unknown')}")
    raise Exception(f"Maximum retries exceeded for snapshot {snapshot_id}. Last data: {snapshot_data}")


async def get_pitchbook_data(urls: list[str]) -> dict:
    if not BRIGHTDATA_API_KEY:
        logger.error("BRIGHTDATA_API_KEY not found.")
        raise ValueError("BRIGHTDATA_API_KEY is not set.")

    trigger_url = "https://api.brightdata.com/datasets/v3/trigger"
    headers = {
        "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
        "Content-Type": "application/json",
    }
    # Ensure your dataset_id is correct for PitchBook
    params = {"dataset_id": "gd_m4ijiqfp2n9oe3oluj", "include_errors": "true"}
    payload_data = [{"url": u} for u in urls]

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Triggering PitchBook data collection for: {urls}")
            trigger_response = await client.post(
                trigger_url, headers=headers, params=params, json=payload_data, timeout=30.0
            )
            # Check for successful trigger (200, 201, 202 are generally OK)
            if not (200 <= trigger_response.status_code < 300):
                logger.error(f"Trigger request failed: {trigger_response.status_code} - {trigger_response.text}")
                trigger_response.raise_for_status()

            initial_data = trigger_response.json()
            snapshot_id = initial_data.get("snapshot_id")

            if not snapshot_id:
                logger.error(f"No snapshot_id in trigger response: {initial_data}")
                raise Exception("No snapshot_id returned from trigger API")
            
            logger.info(f"Triggered collection. Snapshot ID: {snapshot_id}")
            return await _poll_for_pitchbook_snapshot(client, snapshot_id)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_pitchbook_data: {e.response.status_code} - {e.response.text}")
            raise


pitchbook_tool = StructuredTool.from_function(
    name="get_pitchbook_data",
    description="Triggers and retrieves PitchBook data for a list of company URLs. Returns the snapshot data which includes a 'status' field ('completed', 'private', 'failed', etc.).",
    func=get_pitchbook_data, # For synchronous LangChain execution (if needed)
    coroutine=get_pitchbook_data, # For asynchronous LangChain execution
)

# Test block
async def main_test():
    logger.info("--- Testing get_pitchbook_data function ---")
    example_urls = [
        "https://pitchbook.com/profiles/company/114790-51", # Klue (known to be Private)
        # "https://pitchbook.com/profiles/company/50348-82", # Microsoft (example of a public one, if accessible)
    ]
    if not example_urls:
        logger.warning("example_urls is empty. Please provide URLs to test.")
        return

    try:
        result = await get_pitchbook_data(example_urls)
        logger.info("--- Test Result ---")
        logger.info(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"--- Test Failed --- \nError: {e}")
        # import traceback # Uncomment for full traceback during debugging
        # traceback.print_exc()
    finally:
        logger.info("--- End of Test ---")

if __name__ == "__main__":
    # To see DEBUG logs from polling, change basicConfig level to logging.DEBUG
    # logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main_test())
