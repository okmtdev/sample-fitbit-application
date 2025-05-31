import httpx
import datetime
import asyncio
import time
import base64
import config
from settings import Settings
import tokens
import constant
from errors import InternalError


conf = config.Config()
const = constant.Constant()


class Client():
    def __init__(self, settings):
        self.client_id = settings.client_id
        self.client_secret = settings.client_secret
        self.refresh_token = settings.refresh_token
        self.scopes = settings.scopes
        self.API_BASE_URL = const.API_BASE_URL
        self.API_TOKEN_URL = const.API_TOKEN_URL
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

        #with open(self.TOKEN_FILE, 'w') as f:
        #    json.dump(updated_tokens, f, indent=2) # indentを追加して見やすく
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


    async def make_api_request(self, client: httpx.AsyncClient, access_token: str, endpoint: str):
        """Fitbit APIにリクエストを送信する (リフレッシュ試行は get_authenticated_session に移管)"""
        if not client or not access_token:
            print("APIリクエストに必要なクライアントまたはアクセストークンがありません。")
            return None

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        try:
            response = await client.get(f"{self.API_BASE_URL}{endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # 401エラーは get_authenticated_session で事前にリフレッシュ試行済みなので、
            # ここで再度401が出た場合はリフレッシュしても解決しない問題の可能性が高い
            print(f"APIリクエストエラー (ステータスコード: {e.response.status_code}): {e.response.text}")
            if e.response.status_code == 401:
                print("認証エラーが発生しました。アクセストークンが無効か、スコープが不足している可能性があります。")
            elif e.response.status_code == 403:
                 print("アクセスが拒否されました。必要なスコープがトークンに付与されているか確認してください。")
            return None
        except httpx.RequestError as e:
            print(f"リクエストエラー: {e}")
            return None

    # ------------------------------------------------------------------------------
    # データ取得関数 (API呼び出し部分の引数変更に対応)
    # ------------------------------------------------------------------------------
    async def get_sleep_data(self, api_client: httpx.AsyncClient, access_token: str, date_str: str):
        print(f"\n--- {date_str} の睡眠データを取得中 ---")
        endpoint = f"/1.2/user/-/sleep/date/{date_str}.json"
        return await self.make_api_request(api_client, access_token, endpoint)

    async def get_blood_pressure_data(self, api_client: httpx.AsyncClient, access_token: str, date_str: str):
        print(f"\n--- {date_str} の血圧データを取得中 ---")
        print("注意: 血圧APIはアクセスが制限されており、データ取得に失敗する可能性があります。")
        endpoint = f"/1/user/-/bp/date/{date_str}.json"
        return await self.make_api_request(api_client, access_token, endpoint)

    async def get_activity_summary_data(self, api_client: httpx.AsyncClient, access_token: str, date_str: str):
        print(f"\n--- {date_str} の活動概要データを取得中 (歩行データなど) ---")
        endpoint = f"/1/user/-/activities/date/{date_str}.json"
        return await self.make_api_request(api_client, access_token, endpoint)

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
            target_date_str = datetime.date.today().strftime("%Y-%m-%d")

            print(f"\nFitbitデータ取得プログラム ({target_date_str} のデータ)")
            print("==============================================")

            # 睡眠データの取得
            sleep_data = await self.get_sleep_data(client_session, access_token, target_date_str)
            if sleep_data:
                print("睡眠データ取得成功:")
                if sleep_data.get("summary"):
                    print(f"  総睡眠時間 (分): {sleep_data['summary'].get('totalMinutesAsleep')}")
                if sleep_data.get("sleep"):
                    for i, log in enumerate(sleep_data["sleep"]):
                        print(f"  睡眠ログ {i+1}: 開始時刻: {log.get('startTime')}, 効率: {log.get('efficiency')}%")

            # 血圧データの取得
            blood_pressure_data = await self.get_blood_pressure_data(client_session, access_token, target_date_str)
            if blood_pressure_data:
                print("血圧データ取得成功:")
                if blood_pressure_data.get("bp"):
                    for i, record in enumerate(blood_pressure_data["bp"]):
                        print(f"  血圧記録 {i+1}: 時刻: {record.get('time')}, 最高: {record.get('systolic')}, 最低: {record.get('diastolic')}")
                else:
                    print("  血圧データは記録されていませんでした。")
            else:
                print("  血圧データの取得に失敗したか、アクセスが許可されていません。")


            # 歩行データ (活動概要から取得)
            activity_summary = await self.get_activity_summary_data(client_session, access_token, target_date_str)
            if activity_summary:
                print("活動概要データ取得成功:")
                if activity_summary.get("summary"):
                    steps = activity_summary["summary"].get("steps")
                    calories_out = activity_summary["summary"].get("caloriesOut")
                    print(f"  歩数: {steps}")
                    print(f"  消費カロリー: {calories_out}")
                else:
                    print("  活動概要のサマリーが見つかりませんでした。")

        print("\n==============================================")
        print("処理完了")


if __name__ == "__main__":
    try:
        settings = Settings()
        client = Client(settings)
        asyncio.run(client.save())
    except KeyboardInterrupt as ki:
        raise InternalError(ki)
