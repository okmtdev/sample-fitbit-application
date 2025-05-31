import os
from dotenv import load_dotenv

load_dotenv(verbose=True)


# ここは個人ごとのデータから取得するようにする
class Settings:
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    scopes = ["sleep", "activity", "bloodpressure"]
