from utils.logger import logger
from typing import Dict, Any, List, Optional # Optional を追加
from errors import APIError # errors.py があると仮定
from utils.api import ApiClient # utils/api.py があると仮定

class Activity:
    def __init__(self, client: ApiClient):
        if not isinstance(client, ApiClient):
            raise TypeError("client must be an instance of ApiClient")
        self.client = client
        self.API_VERSION = "1"  # Activity APIのバージョン

    async def get_summary_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """
        特定の日付のアクティビティサマリーを取得します。
        歩数、カロリー、距離などを含みます。

        :param date: 取得する日付 (YYYY-MM-DD形式)
        :return: アクティビティサマリーデータ、またはエラー時はNone
        """
        endpoint = f"/{self.API_VERSION}/user/-/activities/date/{date}.json"
        try:
            activity_data = await self.client.get(endpoint)
            if activity_data:
                logger.info(f"Successfully fetched activity summary for {date}.")
            else:
                # 204 No Content や空のレスポンスの場合
                logger.info(f"No activity summary content returned for {date} (e.g., 204 No Content or empty response).")
            return activity_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching activity summary for {date}: {e}")
            return None
        except Exception as e:
            # APIError以外の予期せぬエラーをキャッチ
            logger.exception(f"An unexpected non-API error occurred while fetching activity summary for {date}: {e}")
            return None

    async def get_time_series(
        self, resource_path: str, base_date: str, period: str
    ) -> Optional[Dict[str, Any]]:
        """
        特定のリソースの時系列データを期間で取得します。
        例: steps, calories, distance

        :param resource_path: 取得するリソース ('steps', 'calories', 'distance'など)
        :param base_date: 基準日 (YYYY-MM-DD形式または'today')
        :param period: 期間 ('1d', '7d', '30d', '1w', '1m', '3m', '6m', '1y')
        :return: 時系列データ、またはエラー時はNone
        """
        # 有効なリソースパス (Fitbit APIドキュメント参照)
        valid_resources = [
            "calories", "steps", "distance", "floors", "elevation",
            "minutesSedentary", "minutesLightlyActive",
            "minutesFairlyActive", "minutesVeryActive", "activityCalories"
        ]
        if resource_path not in valid_resources:
            logger.error(f"Invalid resource_path for time series: {resource_path}. Supported: {valid_resources}")
            return None

        endpoint = f"/{self.API_VERSION}/user/-/activities/{resource_path}/date/{base_date}/{period}.json"
        try:
            series_data = await self.client.get(endpoint)
            if series_data:
                logger.info(f"Successfully fetched {resource_path} time series for {base_date}/{period}.")
            else:
                logger.info(f"No {resource_path} time series content returned for {base_date}/{period}.")
            return series_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching {resource_path} time series for {base_date}/{period}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching {resource_path} time series for {base_date}/{period}: {e}")
            return None

    async def get_time_series_by_date_range(
        self, resource_path: str, start_date: str, end_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        特定のリソースの時系列データを日付範囲で取得します。

        :param resource_path: 取得するリソース ('steps', 'calories', 'distance'など)
        :param start_date: 開始日 (YYYY-MM-DD形式)
        :param end_date: 終了日 (YYYY-MM-DD形式)
        :return: 時系列データ、またはエラー時はNone
        """
        valid_resources = [
            "calories", "steps", "distance", "floors", "elevation",
            "minutesSedentary", "minutesLightlyActive",
            "minutesFairlyActive", "minutesVeryActive", "activityCalories"
        ]
        if resource_path not in valid_resources:
            logger.error(f"Invalid resource_path for time series by date range: {resource_path}. Supported: {valid_resources}")
            return None

        endpoint = f"/{self.API_VERSION}/user/-/activities/{resource_path}/date/{start_date}/{end_date}.json"
        try:
            series_data = await self.client.get(endpoint)
            if series_data:
                logger.info(f"Successfully fetched {resource_path} time series for range {start_date} to {end_date}.")
            else:
                logger.info(f"No {resource_path} time series content returned for range {start_date} to {end_date}.")
            return series_data
        except APIError as e:
            logger.error(f"An API error occurred while fetching {resource_path} time series for range {start_date} to {end_date}: {e}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-API error occurred while fetching {resource_path} time series for range {start_date} to {end_date}: {e}")
            return None
