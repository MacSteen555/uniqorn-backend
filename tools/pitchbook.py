import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx
from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Constants
BRIGHTDATA_BASE_URL = os.getenv("BRIGHTDATA_BASE_URL")
DATASET_ID = os.getenv("PITCHBOOK_DATASET_ID")
POLLING_TIMEOUT_SECONDS = 600  # 10 minute safety limit
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 10.0

@dataclass
class PitchBookError(Exception):
    """Base exception for PitchBook tool errors."""
    message: str
    details: Optional[Dict[str, Any]] = None

class AuthorizationError(PitchBookError):
    """Raised when API key is missing or invalid."""
    pass

class TriggerError(PitchBookError):
    """Raised when data collection fails to start."""
    pass

class PollingError(PitchBookError):
    """Raised when polling for results fails or times out."""
    pass

async def _poll_snapshot(
    client: httpx.AsyncClient, 
    snapshot_id: str, 
    api_key: str
) -> Dict[str, Any]:
    """
    Polls the snapshot status until completion or failure.
    Uses exponential backoff for checking status.
    """
    start_time = asyncio.get_running_loop().time()
    delay = INITIAL_RETRY_DELAY
    
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{BRIGHTDATA_BASE_URL}/snapshot/{snapshot_id}"

    logger.info(f"Polling snapshot {snapshot_id}...")

    while True:
        # Check timeout
        if asyncio.get_running_loop().time() - start_time > POLLING_TIMEOUT_SECONDS:
            raise PollingError(f"Polling timed out after {POLLING_TIMEOUT_SECONDS}s", {"snapshot_id": snapshot_id})

        try:
            response = await client.get(url, headers=headers)
            
            # 202 Accepted = Still working
            if response.status_code == 202:
                logger.debug(f"Snapshot {snapshot_id} pending...")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, MAX_RETRY_DELAY)
                continue

            # Check for other errors
            response.raise_for_status()
            
            data = response.json()
            status = data.get("status", "unknown").lower()

            # Terminal states
            if status in ["success", "completed"]:
                logger.info(f"Snapshot {snapshot_id} completed successfully.")
                return data
            
            if status in ["failed", "error", "private"]:
                raise PollingError(f"Snapshot finished with non-success status: {status}", data)
                
            # Unknown running state? Just wait.
            logger.warning(f"Unknown status '{status}', retrying...")
            await asyncio.sleep(delay)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                 raise AuthorizationError("Invalid API key during polling.") from e
            elif e.response.status_code == 404:
                 raise PollingError(f"Snapshot {snapshot_id} not found.") from e
            else:
                 logger.warning(f"HTTP error polling: {e}. Retrying.")
                 await asyncio.sleep(delay)
                 
        except httpx.RequestError as e:
             logger.warning(f"Network error polling: {e}. Retrying.")
             await asyncio.sleep(delay)

async def get_pitchbook_data(urls: List[str]) -> Dict[str, Any]:
    """
    Triggers PitchBook data collection for a list of URLs and waits for the result.
    
    Args:
        urls: List of PitchBook profile URLs to scrape.
        
    Returns:
        Dict containing the snapshot data.
        
    Raises:
        AuthorizationError: If API key is missing/invalid.
        TriggerError: If the job cannot be started.
        PollingError: If the job fails or times out.
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        raise AuthorizationError("Bright Data API key not found in environment.")

    if not urls:
        logger.warning("No URLs provided to get_pitchbook_data.")
        return {}

    trigger_url = f"{BRIGHTDATA_BASE_URL}/trigger"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    params = {"dataset_id": DATASET_ID, "include_errors": "true"}
    payload = [{"url": u} for u in urls]

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Trigger the collection
        try:
            logger.info(f"Triggering collection for {len(urls)} URLs...")
            response = await client.post(trigger_url, headers=headers, params=params, json=payload)
            
            if response.status_code in (401, 403):
                raise AuthorizationError("Invalid API key rejected by trigger endpoint.")
            
            response.raise_for_status()
            data = response.json()
            
            snapshot_id = data.get("snapshot_id")
            if not snapshot_id:
                raise TriggerError("API response missing 'snapshot_id'", details=data)
                
            logger.info(f"Job started. Snapshot ID: {snapshot_id}")

        except httpx.HTTPError as e:
            raise TriggerError(f"Failed to trigger data collection: {str(e)}") from e

        # 2. Poll for results
        return await _poll_snapshot(client, snapshot_id, api_key)

# Main execution block for testing
if __name__ == "__main__":
    async def main():
        print("--- Testing PitchBook Tool ---")
        test_urls = ["https://pitchbook.com/profiles/company/114790-51"]
        
        try:
            result = await get_pitchbook_data(test_urls)
            import json
            print(json.dumps(result, indent=2))
        except PitchBookError as e:
            print(f"❌ Error: {e}")
            if e.details:
                print(f"Details: {e.details}")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAborted by user.")
