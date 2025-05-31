import httpx
import logging
from typing import Any, Dict, Optional
from errors import APIError, APIUnauthorizedError, APIForbiddenError, APIRequestSetupError, APIHttpError, APICommunicationError


logger = logging.getLogger(__name__)

# APIのベースURL (設定ファイルや環境変数からの読み込みを検討)
FITBIT_API_BASE_URL = "https://api.fitbit.com"


async def make_api_request(
    client: httpx.AsyncClient,
    access_token: str,
    endpoint: str,
    base_url: str = FITBIT_API_BASE_URL, # デフォルトのベースURLを使用
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None
) -> Any: # より具体的な型 (e.g., Dict[str, Any]) が望ましい
    """Fitbit API (または他のAPI) にリクエストを送信する汎用関数。"""
    if not client or not access_token:
        logger.error("API client or access token is missing for API request.")
        raise APIRequestSetupError("API client or access token is missing.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = f"{base_url}{endpoint}"
    logger.debug(f"Sending {method} request to {url} with params: {params}, data: {json_data}")

    try:
        response = await client.request(method, url, headers=headers, params=params, json=json_data)
        response.raise_for_status()  # HTTP 4xx/5xx 時に httpx.HTTPStatusError を送出
        if response.status_code == 204: # No Content の場合
            return None
        return response.json()
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        response_text = e.response.text
        logger.warning(
            f"API HTTP Error: Status {status_code} for {method} {url}. Response: {response_text}",
            # exc_info=True # デバッグ時や詳細ログが必要な場合に有効化
        )
        if status_code == 401:
            # コメントにある通り、リフレッシュ試行が既に行われている前提であれば、
            # ここでの401は解決困難な認証エラーを示唆する。
            raise APIUnauthorizedError(response_text=response_text)
        elif status_code == 403:
            raise APIForbiddenError(response_text=response_text)
        else:
            raise APIHttpError(status_code=status_code, response_text=response_text)
    except httpx.RequestError as e:
        logger.error(f"API Request (Communication) Error for {method} {url}: {e}", exc_info=True)
        raise APICommunicationError(f"Failed to connect to API: {e}")
    except Exception as e: # 予期せぬエラー
        logger.exception(f"An unexpected error occurred during API request to {url}: {e}")
        raise APIError(f"An unexpected error occurred: {e}")
