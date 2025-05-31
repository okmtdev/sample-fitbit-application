import httpx
import datetime
from utils.api import ApiClient
import asyncio
import time
import base64
import config
from settings import Settings
import tokens
import constants
from errors import InternalError
from services.sleep import Sleep
from constants import API_BASE_URL, API_TOKEN_URL


conf = config.Config()


class Client():
    def __init__(self, settings):
        self.client_id = settings.client_id
        self.client_secret = settings.client_secret
        self.refresh_token = settings.refresh_token
        self.scopes = settings.scopes
        self.API_BASE_URL = API_BASE_URL
        self.API_TOKEN_URL = API_TOKEN_URL
        self.tokens = tokens.Tokens()


    # ------------------------------------------------------------------------------
    # トークン管理関数 (変更なし)
    # ------------------------------------------------------------------------------
    def save_tokens(self, token_data):
        """トークン情報をファイルに保存する"""
        # expires_in から expires_at (Unixタイムスタンプ) を計算
        # 60秒のマージンを持たせる
        if 'expires_in' in token_data: # リフレッシュ時はexpires_inが返る
            token_data['expires_at'] = time.time() + token_data['expires_in'] - 60
        # もし token_data に expires_in がなく、expires_at が直接セットされていればそれを使う
        # (手動設定や以前の保存形式への配慮だが、通常はリフレッシュで上書きされる)

        # 既存のトークン情報とマージする形で保存 (特にrefresh_tokenは更新されない場合もあるため)
        existing = self.load_tokens() or {}
        updated = {**existing, **token_data} # 新しい情報で上書き

        self.tokens.set("access_token", updated["access_token"])
        self.tokens.set("expires_at", updated["expires_at"])
        self.tokens.set("expires_is", updated["expires_is"])
        self.tokens.set("scope", updated["scope"])
        self.tokens.set("token_type", updated["token_type"])
        self.tokens.set("user_id", updated["user_id"])

        Settings().update_refresh_token(updated["refresh_token"])
        self.refresh_token = updated["refresh_token"]
        print(f"トークン情報を更新しました。")

    def load_tokens(self):
        return {
            "access_token": self.tokens.get("access_token"),
            "expires_at": self.tokens.get("expires_at"),
            "expires_is": self.tokens.get("expires_is"),
            "scope": self.tokens.get("scope"),
            "token_type": self.tokens.get("token_type"),
            "user_id": self.tokens.get("user_id")
        }

    # ------------------------------------------------------------------------------
    # OAuth 2.0 認証フロー (リフレッシュ処理のみに注力)
    # ------------------------------------------------------------------------------
    async def refresh_access_token(self, client: httpx.AsyncClient, existing_refresh_token: str):
        """リフレッシュトークンを使って新しいアクセストークンを取得する"""
        if not existing_refresh_token:
            print("エラー: リフレッシュトークンが提供されていません。処理を中断します。")
            return None

        print("アクセストークンをリフレッシュしています...")
        auth_header_raw = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(auth_header_raw.encode()).decode()

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": existing_refresh_token
        }
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = await client.post(self.API_TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            new_token_data = response.json()

            if "access_token" in new_token_data and "refresh_token" in new_token_data:
                # 新しいアクセストークンと、新しいリフレッシュトークンを保存
                self.save_tokens(new_token_data)
                print("アクセストークンが正常にリフレッシュされました。")
                return new_token_data
            elif "access_token" in new_token_data: # リフレッシュトークンは更新されない場合もある
                print("警告: 新しいリフレッシュトークンは発行されませんでした。既存のリフレッシュトークンを引き続き使用します。")
                # current_tokens = load_tokens() # 保存されている古いリフレッシュトークンを維持するため
                self.save_tokens({
                    "access_token": new_token_data["access_token"],
                    "expires_in": new_token_data.get("expires_in"), # expires_in も取得
                    # "refresh_token": current_tokens.get("refresh_token") if current_tokens else existing_refresh_token, # 念のため
                    "scope": new_token_data.get("scope"),
                    "user_id": new_token_data.get("user_id"),
                    "token_type": new_token_data.get("token_type")
                })
                return self.load_tokens() # 保存された最新情報を返す
            else:
                print(f"エラー: トークンのリフレッシュに失敗しました。レスポンスに必須トークンが含まれていません: {new_token_data}")
                return None

        except httpx.HTTPStatusError as e:
            print(f"トークンリフレッシュエラー (ステータスコード: {e.response.status_code}): {e.response.text}")
            if e.response.status_code in [400, 401]: # 不正なリフレッシュトークンなど
                print(f"エラー: 提供されたリフレッシュトークンが無効である可能性があります。")
            return None
        except Exception as e:
            print(f"トークンリフレッシュ中に予期せぬエラーが発生しました: {e}")
            return None

    # ------------------------------------------------------------------------------
    # APIリクエスト処理 (変更)
    # ------------------------------------------------------------------------------
    async def get_authenticated_session(self):
        """
        保存されたトークンをロードし、必要であればリフレッシュして、
        認証済みの httpx.AsyncClient とアクセストークンを返す。
        リフレッシュトークンがない、またはリフレッシュに失敗した場合は None を返す。
        """
        tokens = self.load_tokens()

        if not tokens or 'refresh_token' not in tokens or not tokens['refresh_token']:
            print("""
            {
              "refresh_token": "あなたのリフレッシュトークン",
              "access_token": "(あれば)",
              "expires_at": 0 // (access_tokenの有効期限Unixタイムスタンプ、あれば)
            }
            """)
            return None, None

        current_time = time.time()
        access_token = tokens.get('access_token')
        expires_at = tokens.get('expires_at', 0) # expires_at がなければ期限切れとみなす

        async with httpx.AsyncClient() as client:
            if not access_token or current_time >= expires_at:
                if access_token: # 期限切れの場合
                     print("アクセストークンの有効期限が切れています。リフレッシュを試みます。")
                else: # アクセストークン自体がない場合
                     print("アクセストークンが見つかりません。リフレッシュトークンを使って取得します。")

                refreshed_tokens = await self.refresh_access_token(client, tokens['refresh_token'])
                if not refreshed_tokens:
                    print("トークンのリフレッシュに失敗しました。処理を中断します。")
                    return None, None
                access_token = refreshed_tokens.get('access_token')
                if not access_token: # リフレッシュ後もアクセストークンがなければエラー
                    print("エラー: リフレッシュ後もアクセストークンを取得できませんでした。")
                    return None, None
            else:
                print("既存のアクセストークンは有効です。")

            return client, access_token


    # ------------------------------------------------------------------------------
    # メイン処理 (変更)
    # ------------------------------------------------------------------------------
    async def save(self):
        if self.client_id == None or self.client_secret == None:
            print("エラー: プログラム内の 'CLIENT_ID' と 'CLIENT_SECRET' をご自身のものに置き換えてください。")
            return

        # get_authenticated_session は client と access_token をタプルで返すのでアンパックする
        # httpx.AsyncClient はこの関数内で `async with` を使っているので、メイン側で別途管理する必要はない。
        # ただし、複数のAPIコールで同じclientインスタンスを使いまわしたい場合は、
        # get_authenticated_session の構造を変えるか、メイン側でclientを管理する必要がある。
        # 今回はAPIコールごとにclientが生成されるが、トークンはファイルベースで共有される。
        # -> より効率的にするため、clientも一度だけ取得するように修正する。

        async with httpx.AsyncClient() as client_session:
            tokens = self.load_tokens()
            current_time = time.time()
            access_token = tokens.get('access_token')
            expires_at = tokens.get('expires_at', 0)

            if not access_token or current_time >= expires_at:
                if access_token:
                    print("アクセストークンの有効期限が切れています。リフレッシュを試みます。")
                else:
                    print("アクセストークンが見つかりません。リフレッシュトークンを使って取得します。")

                refreshed_tokens_data = await self.refresh_access_token(client_session, settings.refresh_token)
                if not refreshed_tokens_data or 'access_token' not in refreshed_tokens_data:
                    print("トークンのリフレッシュまたはアクセストークンの取得に失敗しました。処理を中断します。")
                    return
                access_token = refreshed_tokens_data['access_token']
            else:
                print("既存のアクセストークンは有効です。")

            if not access_token:
                print("有効なアクセストークンを取得できませんでした。プログラムを終了します。")
                return

            # データ取得対象の日付
            target_date = datetime.date.today().strftime("%Y-%m-%d")

            print(f"\nFitbitデータ取得プログラム ({target_date} のデータ)")
            print("==============================================")

            # 睡眠データの取得
            api_client_instance = ApiClient(access_token=access_token, http_client=client_session)
            sleep = Sleep(client=api_client_instance)
            sleep_data = await sleep.get_by_date(target_date)
            if sleep_data:
                print("睡眠データ取得成功:")
                if sleep_data.get("summary"):
                    print(f"  総睡眠時間 (分): {sleep_data['summary'].get('totalMinutesAsleep')}, "
                          + f"深い眠り（分）: {sleep_data['summary'].get('stages').get('deep')}, "
                          + f"浅い眠り（分）: {sleep_data['summary'].get('stages').get('light')}, "
                          + f"レム睡眠（分）: {sleep_data['summary'].get('stages').get('rem')}, "
                          + f"覚醒状態（分）: {sleep_data['summary'].get('stages').get('wake')}")
                if sleep_data.get("sleep"):
                    for i, record in enumerate(sleep_data["sleep"]):
                        print(f"  睡眠レコード {i+1}: 開始時刻: {record.get('startTime')}, 睡眠効率: {record.get('efficiency')}%") # minutesAsleep/timeInBed
                        for j, log in enumerate(record["levels"]["data"]):
                            print(f"    ログ {j+1}: 時刻: {log.get('dateTime')}, 種類: {log.get('level')}, 時間（秒）: {log.get('seconds')}")

        print("\n==============================================")
        print("処理完了")


if __name__ == "__main__":
    try:
        settings = Settings()
        client = Client(settings)
        asyncio.run(client.save())
    except KeyboardInterrupt as ki:
        raise InternalError(ki)
