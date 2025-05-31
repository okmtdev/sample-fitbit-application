from utils.logger import logger
from typing import Dict, Any
from errors import APIError

from utils.api import ApiClient
from utils.logger import logger


class Sleep:
    def __init__(self, client: ApiClient):
        if not isinstance(client, ApiClient):
            raise TypeError("client must be an instance of ApiClient")
        self.client = client
        self.API_VERSION = "1.2"

    async def get_by_date(self, date: str) -> Dict[str, Any] | None:
        endpoint = f"/{self.API_VERSION}/user/-/sleep/date/{date}.json"

        try:
            sleep_data = await self.client.get(endpoint)
            if sleep_data:
                logger.info(f"Successfully fetched sleep data for {date}.")
            else:
                logger.info(f"No sleep data content returned for {date} (e.g., 204 No Content or empty response).")
            return sleep_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching sleep data for {date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching sleep data for {date}: {e}")
            return None
