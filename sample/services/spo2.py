from utils.logger import logger
from typing import Dict, Any
from errors import APIError # errors.py が存在すると仮定
from utils.api import ApiClient # utils/api.py が存在すると仮定

class Spo2:
    def __init__(self, client: ApiClient):
        if not isinstance(client, ApiClient):
            raise TypeError("client must be an instance of ApiClient")
        self.client = client
        self.API_VERSION = "1"  # SpO2 API version is 1

    async def get_by_date(self, date: str) -> Dict[str, Any] | None:
        """指定された日付のSpO2データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/spo2/date/{date}.json"
        try:
            spo2_data = await self.client.get(endpoint)
            if spo2_data:
                logger.info(f"Successfully fetched SpO2 data for {date}.")
            else:
                logger.info(f"No SpO2 data content returned for {date}.")
            return spo2_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching SpO2 data for {date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching SpO2 data for {date}: {e}")
            return None

    async def get_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any] | None:
        """指定された期間のSpO2データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/spo2/date/{start_date}/{end_date}.json"
        try:
            spo2_data = await self.client.get(endpoint)
            if spo2_data:
                logger.info(f"Successfully fetched SpO2 data for range {start_date} to {end_date}.")
            else:
                logger.info(f"No SpO2 data content returned for range {start_date} to {end_date}.")
            return spo2_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching SpO2 data for range {start_date} to {end_date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching SpO2 data for range {start_date} to {end_date}: {e}")
            return None
