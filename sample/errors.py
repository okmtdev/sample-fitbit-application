
class ConfigError(Exception):
    pass

class InternalError(Exception):
    pass

class APIError(Exception):
    """API関連エラーの基底クラス。"""
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.message = message # message属性を明示的に保持

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"

class APIRequestSetupError(APIError):
    """APIリクエスト設定時のエラー。"""
    def __init__(self, message: str = "API request setup error"):
        super().__init__(message)

class APICommunicationError(APIError):
    """APIとの通信エラー。"""
    def __init__(self, message: str = "API communication error", underlying_exception: Exception | None = None):
        full_message = f"{message}: {underlying_exception}" if underlying_exception else message
        super().__init__(full_message)
        self.underlying_exception = underlying_exception


class APIHttpError(APIError):
    """APIからのHTTPエラーレスポンス。"""
    def __init__(self, status_code: int, response_text: str | None = None, message: str = "API HTTP error"):
        super().__init__(f"{message}: Status {status_code}, Response: {response_text or 'N/A'}", status_code, response_text)

class APIUnauthorizedError(APIHttpError):
    """APIからの401 Unauthorizedエラー。"""
    def __init__(self, response_text: str | None = None, message: str = "API Unauthorized (401)"):
        super().__init__(401, response_text, message)

class APIForbiddenError(APIHttpError):
    """APIからの403 Forbiddenエラー。"""
    def __init__(self, response_text: str | None = None, message: str = "API Forbidden (403)"):
        super().__init__(403, response_text, message)