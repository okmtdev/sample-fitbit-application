
class ConfigError(Exception):
    pass

class InternalError(Exception):
    pass

class APIError(Exception):
    """API関連の操作で発生するエラーのベースクラス。"""
    pass

class APIRequestSetupError(APIError):
    """APIリクエストの準備段階でのエラー（例：トークン不足）。"""
    pass

class APIHttpError(APIError):
    """APIがHTTPエラーステータスコードを返した場合のエラー。"""
    def __init__(self, status_code: int, response_text: str = None, message: str = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message or f"API request failed with status {status_code}. Response: {response_text}")

class APIUnauthorizedError(APIHttpError):
    """401 Unauthorized エラー。"""
    def __init__(self, response_text: str = None):
        super().__init__(401, response_text, "Authentication failed. Access token may be invalid or expired, or scopes may be insufficient.")

class APIForbiddenError(APIHttpError):
    """403 Forbidden エラー。"""
    def __init__(self, response_text: str = None):
        super().__init__(403, response_text, "Access forbidden. Ensure the token has the necessary scopes.")

class APICommunicationError(APIError):
    """ネットワークエラーなど、APIとの通信自体に問題が発生した場合のエラー。"""
    pass
