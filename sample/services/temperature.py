from utils.logger import logger
from typing import Dict, Any
from errors import APIError  # errors.py が存在すると仮定
from utils.api import ApiClient # utils/api.py が存在すると仮定

class Temperature:
    def __init__(self, client: ApiClient):
        if not isinstance(client, ApiClient):
            raise TypeError("client must be an instance of ApiClient")
        self.client = client
        self.API_VERSION = "1"  # Temperature API version is 1

    async def get_skin_temp_by_date(self, date: str) -> Dict[str, Any] | None:
        """指定された日付の皮膚温度データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/temp/skin/date/{date}.json"
        try:
            temp_data = await self.client.get(endpoint)
            if temp_data:
                logger.info(f"Successfully fetched skin temperature data for {date}.")
            else:
                logger.info(f"No skin temperature data content returned for {date}.")
            return temp_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching skin temperature data for {date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching skin temperature data for {date}: {e}")
            return None

    async def get_skin_temp_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any] | None:
        """指定された期間の皮膚温度データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/temp/skin/date/{start_date}/{end_date}.json"
        try:
            temp_data = await self.client.get(endpoint)
            if temp_data:
                logger.info(f"Successfully fetched skin temperature data for range {start_date} to {end_date}.")
            else:
                logger.info(f"No skin temperature data content returned for range {start_date} to {end_date}.")
            return temp_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching skin temperature data for range {start_date} to {end_date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching skin temperature data for range {start_date} to {end_date}: {e}")
            return None

    async def get_core_temp_by_date(self, date: str) -> Dict[str, Any] | None:
        """指定された日付の体幹温度データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/temp/core/date/{date}.json"
        try:
            temp_data = await self.client.get(endpoint)
            if temp_data:
                logger.info(f"Successfully fetched core temperature data for {date}.")
            else:
                logger.info(f"No core temperature data content returned for {date}.")
            return temp_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching core temperature data for {date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching core temperature data for {date}: {e}")
            return None
