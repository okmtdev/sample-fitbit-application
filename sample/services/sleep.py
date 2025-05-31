import httpx
import logging
from typing import Optional, Dict, Any
from utils.api import make_api_request
from errors import APIError, APIUnauthorizedError, APIForbiddenError

# ロガーの設定 (アプリケーションのどこかで一度設定する)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Sleep:
    API_VERSION = "1.2"

    async def get_by_date(self, api_client: httpx.AsyncClient, access_token: str, date: str) -> Optional[Dict[str, Any]]:
        """指定された日付の睡眠データを取得する。"""
        logger.info(f"--- Fetching sleep data for date: {date} ---")
        endpoint = f"/{self.API_VERSION}/user/-/sleep/date/{date}.json"

        try:
            # 分離された make_api_request 関数を呼び出す
            # (api_client_utils.make_api_request またはインポートした名前で)
            sleep_data = await make_api_request(api_client, access_token, endpoint)
            if sleep_data:
                logger.info(f"Successfully fetched sleep data for {date}.")
            else:
                logger.info(f"No sleep data content returned for {date} (e.g., 204 No Content).")
            return sleep_data
        except APIUnauthorizedError:
            # アクセストークンが無効である可能性が高い。
            # リフレッシュ処理は上位の認証機構で行われる想定。
            # ここでエラーが発生した場合、リフレッシュ後も認証できないことを示す。
            logger.error(
                f"Authorization error while fetching sleep data for {date}. "
                "Access token might be invalid, expired, or lack necessary scopes."
            )
            return None # 元のコードの挙動に合わせてNoneを返すか、エラーを再raiseするかは設計次第
        except APIForbiddenError:
            logger.error(
                f"Forbidden error while fetching sleep data for {date}. "
                "The token may not have the required permissions."
            )
            return None
        except APIError as e: # make_api_request が送出する可能性のある他のカスタムAPIエラー
            logger.error(f"API error while fetching sleep data for {date}: {e}")
            return None
        except Exception as e: # 予期しないその他のエラー
            logger.exception(f"An unexpected error occurred while fetching sleep data for {date}: {e}")
            return None
