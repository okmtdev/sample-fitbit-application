
class Tokens:
    access_token = ""
    expires_at = 0
    expires_is = 0
    scope = []
    token_type = "Bearer"
    user_id = ""

    def get(self, key: str) -> str:
        getattr(self, key)

    def set(self, key: str, value: str):
        setattr(self, key, value)
