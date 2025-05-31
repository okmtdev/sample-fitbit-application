import httpx
import datetime
from utils.api import ApiClient
import asyncio
import time
import base64
import config
from settings import Settings
import tokens
from errors import InternalError
from services.sleep import Sleep
from services.heart_rate import HeartRate
from services.spo2 import Spo2
from services.temperature import Temperature
from services.activity import Activity
from constants import API_BASE_URL, API_TOKEN_URL
import datetime


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
    # 保存処理
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

            # 今日
            #target_date = datetime.date.today().strftime("%Y-%m-%d")
            # 昨日
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            target_date = yesterday.strftime("%Y-%m-%d")


            print(f"\nFitbitデータ取得プログラム ({target_date} のデータ)")
            print("==============================================")

            # --- 睡眠データの取得と表示 ---
            api_client_instance = ApiClient(access_token=access_token, http_client=client_session)
            sleep = Sleep(client=api_client_instance)
            sleep_data = await sleep.get_by_date(target_date)
            if sleep_data["sleep"]:
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
            else:
                print("睡眠データ無し")

            # --- 体温データの取得と表示 ---
            print("\n--- 体温データ ---")
            temperature_client = Temperature(client=api_client_instance) # ApiClientインスタンスを渡す

            # 皮膚温度 (単日)
            skin_temp_single_date_data = await temperature_client.get_skin_temp_by_date(target_date)
            print(skin_temp_single_date_data)
            if skin_temp_single_date_data and skin_temp_single_date_data.get("tempSkin"):
                print(f"\n皮膚温度 ({target_date}):")
                for record in skin_temp_single_date_data["tempSkin"]:
                    print(f"  記録ID: {record.get('logId')}, 日時: {record.get('dateTime')}, "
                        + f"値: {record.get('value').get('value')}°C (基準からの偏差), "
                        + f"夜間平均: {record.get('value').get('nightlyMean')}") # nightlyMean はない場合がある

            # 皮膚温度 (期間) - 例: target_date から3日前までのデータを取得
            start_date_temp = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=2)).strftime("%Y-%m-%d") # 3日間 (当日含む)
            end_date_temp = target_date

            skin_temp_range_data = await temperature_client.get_skin_temp_by_date_range(start_date_temp, end_date_temp)
            print(skin_temp_range_data)
            if skin_temp_range_data and skin_temp_range_data.get("tempSkin"):
                print(f"\n皮膚温度 ({start_date_temp} - {end_date_temp}):")
                for record in skin_temp_range_data["tempSkin"]:
                    print(f"  記録ID: {record.get('logId')}, 日時: {record.get('dateTime')}, "
                        + f"値: {record.get('value').get('value')}°C (基準からの偏差), "
                        + f"夜間平均: {record.get('value').get('nightlyMean')}") # nightlyMean はない場合がある

            # 体幹温度 (単日) - 注意: このAPIは一部のデバイス/ユーザーでのみ利用可能です。
            core_temp_data = await temperature_client.get_core_temp_by_date(target_date)
            print(core_temp_data)
            if core_temp_data and core_temp_data.get("tempCore"):
                print(f"\n体幹温度 ({target_date}):")
                for record in core_temp_data["tempCore"]:
                    print(f"  記録ID: {record.get('logId')}, 日時: {record.get('dateTime')}, "
                        + f"値: {record.get('value')}°C, 集計期間(分): {record.get('logType')}") # logTypeは集計期間を示唆

            # --- SpO2 データの取得と表示 ---
            print("\n--- SpO2データ ---")
            spo2_client = Spo2(client=api_client_instance)

            # SpO2 (単日)
            spo2_single_date_data = await spo2_client.get_by_date(target_date)
            if spo2_single_date_data and spo2_single_date_data.get("value"):
                print(f"\nSpO2 ({target_date}):")
                print(f"  平均: {spo2_single_date_data['value'].get('avg')}%, "
                    + f"最小: {spo2_single_date_data['value'].get('min')}%, "
                    + f"最大: {spo2_single_date_data['value'].get('max')}%")
            elif spo2_single_date_data: # データはあるが 'value' キーがない場合 (e.g., 204 No Content)
                print(f"\nSpO2 ({target_date}): データがありませんでした。")


            # SpO2 (期間) - 例: target_date から3日前までのデータを取得
            start_date_spo2 = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
            end_date_spo2 = target_date

            spo2_range_data = await spo2_client.get_by_date_range(start_date_spo2, end_date_spo2)
            if spo2_range_data: # レスポンスのキーが "spo2" で、その中にリストが入る
                print(f"\nSpO2 ({start_date_spo2} - {end_date_spo2}):")
                for day_data in spo2_range_data:
                    if day_data.get("value"):
                        print(f"  日付: {day_data.get('dateTime')}, "
                            + f"平均: {day_data['value'].get('avg')}%, "
                            + f"最小: {day_data['value'].get('min')}%, "
                            + f"最大: {day_data['value'].get('max')}%")
                    else:
                        print(f"  日付: {day_data.get('dateTime')}, データがありませんでした。")


            # --- 心拍数データの取得と表示 ---
            print("\n--- 心拍数データ ---")
            heart_rate_client = HeartRate(client=api_client_instance)

            # 心拍変動 (HRV) (単日)
            hrv_single_date_data = await heart_rate_client.get_hrv_by_date(target_date)
            if hrv_single_date_data and hrv_single_date_data.get("hrv"):
                print(f"\n心拍変動 (HRV) ({target_date}):")
                for record in hrv_single_date_data["hrv"]:
                    if record.get("value") and record["value"].get("dailyRmssd") is not None:
                        print(f"  RMSSD: {record['value']['dailyRmssd']}, "
                            + f"低周波 (LF): {record['value'].get('deepRmssd')}") # deepRmssd は睡眠中のHRVの指標
                    else:
                        print(f"  HRVデータ詳細なし: {record}")


            # 心拍変動 (HRV) (期間)
            start_date_hrv = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=6)).strftime("%Y-%m-%d") # 7日間
            end_date_hrv = target_date
            hrv_range_data = await heart_rate_client.get_hrv_by_date_range(start_date_hrv, end_date_hrv)
            if hrv_range_data and hrv_range_data.get("hrv"):
                print(f"\n心拍変動 (HRV) ({start_date_hrv} - {end_date_hrv}):")
                for record in hrv_range_data["hrv"]:
                    if record.get("value") and record["value"].get("dailyRmssd") is not None:
                        print(f"  日付: {record.get('dateTime')}, RMSSD: {record['value']['dailyRmssd']}, "
                            + f"低周波 (LF): {record['value'].get('deepRmssd')}")
                    else:
                        print(f"  日付: {record.get('dateTime')}, HRVデータ詳細なし")


            # 心拍数時系列 (Intraday) - 1分間の詳細レベルで取得
            hr_intraday_data = await heart_rate_client.get_heart_rate_intraday_by_date(target_date, detail_level="1min")
            if hr_intraday_data and hr_intraday_data.get("activities-heart-intraday"):
                print(f"\n日中心拍数 ({target_date}, 1分間隔):")
                print(f"  データセット数: {len(hr_intraday_data['activities-heart-intraday'].get('dataset', []))}")
                # 詳細なデータ表示は長くなるため、一部のみ、または集計値の表示を推奨
                for entry in hr_intraday_data["activities-heart-intraday"].get("dataset", [])[:5]: # 最初の5件
                    print(f"    時刻: {entry.get('time')}, 心拍数: {entry.get('value')}")


            # 心拍数時系列 (Date Range) - 日毎のサマリー
            # 例: target_date から過去7日間のデータを取得 (end_date が target_date となる)
            base_date_hr_range = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
            end_date_hr_range = target_date

            hr_date_range_data = await heart_rate_client.get_heart_rate_by_date_range(base_date_hr_range, end_date_hr_range)
            if hr_date_range_data and hr_date_range_data.get("activities-heart"):
                print(f"\n心拍数サマリー ({base_date_hr_range} - {end_date_hr_range}):")
                for day_summary in hr_date_range_data["activities-heart"]:
                    print(f"  日付: {day_summary.get('dateTime')}")
                    if day_summary.get("value") and day_summary["value"].get("heartRateZones"):
                        resting_hr = day_summary["value"].get('restingHeartRate', 'N/A')
                        print(f"    安静時心拍数: {resting_hr}")
                        print("    心拍ゾーン:")
                        for zone in day_summary["value"]["heartRateZones"]:
                            print(f"      {zone.get('name')}: "
                                + f"閾値 {zone.get('min')}-{zone.get('max')} bpm, "
                                + f"滞在時間 {zone.get('minutes')} 分, "
                                + f"消費カロリー {zone.get('caloriesOut')}")
                    else:
                        print("    心拍数データ詳細なし")

                    print("\n==============================================")
                    print("処理完了")


            activity = Activity(client=api_client_instance)
            target_date_summary = "2025-05-31" # 必要に応じて変更してください (存在するデータの日付)
            print(f"\n--- {target_date_summary}のアクティビティサマリー ---")
            daily_summary = await activity.get_summary_by_date(target_date_summary)

            if daily_summary and daily_summary.get("summary"):
                summary = daily_summary["summary"]
                steps = summary.get("steps", "N/A")
                calories_out = summary.get("caloriesOut", "N/A")

                total_distance = "N/A"
                if summary.get("distances"):
                    for dist_entry in summary["distances"]:
                        if dist_entry.get("activity") == "total": # "total" が総距離を示す
                            total_distance = dist_entry.get("distance", "N/A")
                            break
                        
                print(f"  歩数: {steps} 歩")
                print(f"  総消費カロリー: {calories_out} kcal")
                print(f"  総移動距離: {total_distance} km")
            elif daily_summary is None: # APIエラーまたはその他の予期せぬエラー
                 print(f"  {target_date_summary}のアクティビティサマリーの取得中にエラーが発生しました。詳細はログを確認してください。")
            else: # データが存在しない場合 (例: 204 No Content)
                print(f"  {target_date_summary}のアクティビティサマリーデータはありませんでした。")

            # --- B. 過去7日間の日毎の歩数と集計 ---
            print(f"\n--- 過去7日間の日毎の歩数 (今日基準) ---")
            # 'today' を基準日とし、'7d' (過去7日間) のデータを取得
            steps_7d_data = await activity.get_time_series(resource_path="steps", base_date="today", period="7d")

            if steps_7d_data and steps_7d_data.get("activities-steps"):
                entries = steps_7d_data["activities-steps"]
                if entries:
                    total_steps_7d = 0
                    print("  日毎の歩数:")
                    for entry in entries:
                        date = entry.get("dateTime")
                        value = int(entry.get("value", 0))
                        total_steps_7d += value
                        print(f"    {date}: {value} 歩")

                    avg_steps_7d = total_steps_7d / len(entries) if entries else 0
                    print(f"  過去7日間の合計歩数: {total_steps_7d} 歩")
                    print(f"  過去7日間の平均歩数: {avg_steps_7d:.0f} 歩/日")
                else:
                    print("  過去7日間の歩数データが空でした。")
            elif steps_7d_data is None:
                print(f"  過去7日間の歩数データの取得中にエラーが発生しました。詳細はログを確認してください。")
            else:
                print("  過去7日間の歩数データは取得できませんでした（データなしまたは空の応答）。")


            # --- C. 特定の期間 (例: 先週月曜日から日曜日) の総消費カロリー ---
            today = datetime.datetime.now()
            start_of_last_week = today - datetime.timedelta(days=today.weekday() + 7) # 先週の月曜日
            end_of_last_week = start_of_last_week + datetime.timedelta(days=6)         # 先週の日曜日

            start_date_calories = start_of_last_week.strftime("%Y-%m-%d")
            end_date_calories = end_of_last_week.strftime("%Y-%m-%d")

            print(f"\n--- {start_date_calories} から {end_date_calories} の消費カロリー ---")
            calories_last_week = await activity.get_time_series_by_date_range(
                resource_path="calories", start_date=start_date_calories, end_date=end_date_calories
            )

            if calories_last_week and calories_last_week.get("activities-calories"):
                entries = calories_last_week["activities-calories"]
                if entries:
                    total_calories_period = 0
                    print("  日毎の消費カロリー:")
                    for entry in entries:
                        date = entry.get("dateTime")
                        value = int(entry.get("value", 0))
                        total_calories_period += value
                        print(f"    {date}: {value} kcal")

                    avg_calories_period = total_calories_period / len(entries) if entries else 0
                    print(f"  期間中の合計消費カロリー: {total_calories_period} kcal")
                    print(f"  期間中の平均消費カロリー: {avg_calories_period:.0f} kcal/日")
                else:
                    print(f"  {start_date_calories} から {end_date_calories} のカロリーデータが空でした。")
            elif calories_last_week is None:
                print(f"  {start_date_calories} から {end_date_calories} のカロリーデータの取得中にエラーが発生しました。")
            else:
                print(f"  {start_date_calories} から {end_date_calories} のカロリーデータは取得できませんでした。")


            # --- D. 過去1ヶ月間の日毎の移動距離と集計 ---
            print(f"\n--- 過去1ヶ月間の日毎の移動距離 (今日基準, '1m'ピリオド使用) ---")
            distance_1m_data = await activity.get_time_series(resource_path="distance", base_date="today", period="1m")

            if distance_1m_data and distance_1m_data.get("activities-distance"):
                entries = distance_1m_data["activities-distance"]
                if entries:
                    total_distance_1m = 0.0
                    days_with_data = 0
                    print("  日毎の移動距離:")
                    for entry in entries:
                        date = entry.get("dateTime")
                        value_str = entry.get("value", "0")
                        try:
                            value = float(value_str)
                            print(f"    {date}: {value:.2f} km")
                            if value > 0: # 実際に移動があった日のみを集計対象とする場合
                                total_distance_1m += value
                                days_with_data += 1
                        except ValueError:
                            print(f"    {date}: データ形式エラー ({value_str})")

                    if days_with_data > 0:
                        avg_distance_1m = total_distance_1m / days_with_data
                        print(f"\n  過去1ヶ月間の合計移動距離 (記録日ベース): {total_distance_1m:.2f} km")
                        print(f"  過去1ヶ月間の平均移動距離 (記録日ベース): {avg_distance_1m:.2f} km/日")
                        print(f"  (記録があった日数: {days_with_data}日 / 全{len(entries)}日中)")
                    elif entries: # データはあるが全て0kmだった場合
                        print(f"\n  過去1ヶ月間の合計移動距離: 0.00 km")
                    else: # entries が空のケース (通常は上の条件で捕捉されるはず)
                        print("  過去1ヶ月間の移動距離データが空でした。")

                else: # "activities-distance" キーはあるが、その値 (リスト) が空の場合
                    print("  過去1ヶ月間の移動距離データが空でした。")
            elif distance_1m_data is None:
                print(f"  過去1ヶ月間の移動距離データの取得中にエラーが発生しました。")
            else:
                print("  過去1ヶ月間の移動距離データは取得できませんでした（データなしまたは空の応答）。")





if __name__ == "__main__":
    try:
        settings = Settings()
        client = Client(settings)
        asyncio.run(client.save())
    except KeyboardInterrupt as ki:
        raise InternalError(ki)
