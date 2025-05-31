from utils.logger import logger
from typing import Dict, Any, Optional
from errors import APIError # errors.py が存在すると仮定
from utils.api import ApiClient # utils/api.py が存在すると仮定

class HeartRate:
    def __init__(self, client: ApiClient):
        if not isinstance(client, ApiClient):
            raise TypeError("client must be an instance of ApiClient")
        self.client = client
        self.API_VERSION = "1"  # Heart Rate APIs version is 1

    # --- Heart Rate Variability (HRV) ---
    async def get_hrv_by_date(self, date: str) -> Dict[str, Any] | None:
        """指定された日付の心拍変動(HRV)データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/hrv/date/{date}.json"
        try:
            hrv_data = await self.client.get(endpoint)
            if hrv_data:
                logger.info(f"Successfully fetched HRV data for {date}.")
            else:
                logger.info(f"No HRV data content returned for {date}.")
            return hrv_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching HRV data for {date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching HRV data for {date}: {e}")
            return None

    async def get_hrv_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any] | None:
        """指定された期間の心拍変動(HRV)データを取得します。"""
        endpoint = f"/{self.API_VERSION}/user/-/hrv/date/{start_date}/{end_date}.json"
        try:
            hrv_data = await self.client.get(endpoint)
            if hrv_data:
                logger.info(f"Successfully fetched HRV data for range {start_date} to {end_date}.")
            else:
                logger.info(f"No HRV data content returned for range {start_date} to {end_date}.")
            return hrv_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching HRV data for range {start_date} to {end_date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching HRV data for range {start_date} to {end_date}: {e}")
            return None

    # --- Heart Rate Time Series ---
    async def get_heart_rate_intraday_by_date(
        self,
        date: str,
        detail_level: str = "1sec", # "1sec" or "1min"
        start_time: Optional[str] = None, # HH:mm
        end_time: Optional[str] = None # HH:mm
    ) -> Dict[str, Any] | None:
        """指定された日付の日中心拍数時系列データを取得します。"""
        if start_time and end_time:
            endpoint = f"/{self.API_VERSION}/user/-/activities/heart/date/{date}/1d/{detail_level}/time/{start_time}/{end_time}.json"
            log_suffix = f"for {date}, detail: {detail_level}, time: {start_time}-{end_time}"
        else:
            endpoint = f"/{self.API_VERSION}/user/-/activities/heart/date/{date}/1d/{detail_level}.json"
            log_suffix = f"for {date}, detail: {detail_level}"
        try:
            hr_data = await self.client.get(endpoint)
            if hr_data:
                logger.info(f"Successfully fetched intraday heart rate data {log_suffix}.")
            else:
                logger.info(f"No intraday heart rate data content returned {log_suffix}.")
            return hr_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching intraday heart rate data {log_suffix}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching intraday heart rate data {log_suffix}: {e}")
            return None

    async def get_heart_rate_by_date_range(
        self,
        base_date: str,
        end_date: str
    ) -> Dict[str, Any] | None:
        """
        指定された期間 (base_date から end_date まで) の日毎の心拍数サマリーデータを取得します。
        期間は最大30日間です。
        """
        endpoint = f"/{self.API_VERSION}/user/-/activities/heart/date/{base_date}/{end_date}.json"
        log_suffix = f"for range {base_date} to {end_date}"
        try:
            hr_data = await self.client.get(endpoint)
            if hr_data:
                logger.info(f"Successfully fetched heart rate data {log_suffix}.")
            else:
                logger.info(f"No heart rate data content returned {log_suffix}.")
            return hr_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching heart rate data {log_suffix}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching heart rate data {log_suffix}: {e}")
            return None
