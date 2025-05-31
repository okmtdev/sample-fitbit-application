import httpx
from typing import Any, Dict, Optional

from utils.logger import logger
from errors import APIError, APIUnauthorizedError, APIForbiddenError, APIRequestSetupError, APIHttpError, APICommunicationError
from constants import API_BASE_URL


class ApiClient:
    """
    汎用的な非同期APIクライアント。
    HTTPリクエストの送信、認証ヘッダーの付与、エラーハンドリングを行う。
    """
    def __init__(self, access_token: str, base_url: str = API_BASE_URL, http_client: Optional[httpx.AsyncClient] = None):
        if not access_token:
            logger.error("Access token is missing for ApiClient initialization.")
            raise APIRequestSetupError("Access token is required for ApiClient.")

        self.access_token = access_token
        self.base_url = base_url
        self._http_client = http_client if http_client else httpx.AsyncClient()
        self._should_close_client = http_client is None
        self._default_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        logger.debug(f"ApiClient initialized for base_url: {self.base_url}")

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = self._default_headers.copy()
        if custom_headers:
            headers.update(custom_headers)

        logger.debug(f"Sending {method} request to {url} with params: {params}, data: {json_data}")

        try:
            response = await self._http_client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data
            )
            response.raise_for_status()

            if response.status_code == 204:
                logger.debug(f"Request to {url} returned 204 No Content.")
                return None

            if 'application/json' in response.headers.get('Content-Type', ''):
                if response.content: # レスポンスボディが空でないことを確認
                    return response.json()
                else:
                    logger.debug(f"Request to {url} returned JSON content type but empty body.")
                    return None 
            else:
                logger.debug(f"Request to {url} returned non-JSON content type: {response.headers.get('Content-Type')}. Returning raw text.")
                return response.text

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            response_text = e.response.text
            logger.warning(
                f"API HTTP Error: Status {status_code} for {method} {url}. Response: {response_text}",
            )
            if status_code == 401:
                raise APIUnauthorizedError(response_text=response_text)
            elif status_code == 403:
                raise APIForbiddenError(response_text=response_text)
            else:
                raise APIHttpError(status_code=status_code, response_text=response_text)
        except httpx.RequestError as e:
            logger.error(f"API Request (Communication) Error for {method} {url}: {e}", exc_info=True)
            raise APICommunicationError(f"Failed to connect to API: {type(e).__name__}", underlying_exception=e)
        except Exception as e: # JSONDecodeErrorなどもここに該当する可能性
            logger.exception(f"An unexpected error occurred during API request to {url}: {e}")
            # APIErrorにラップして、エラーの発生源がAPIClientであることを示す
            raise APIError(f"An unexpected error occurred in APIClient: {type(e).__name__} - {e}")


    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("GET", endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("POST", endpoint, json_data=json_data, **kwargs)

    async def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("PUT", endpoint, json_data=json_data, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> Any:
        return await self.request("DELETE", endpoint, **kwargs)

    async def close(self):
        if self._http_client and self._should_close_client:
            await self._http_client.aclose()
            logger.debug("Internal httpx.AsyncClient closed.")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
