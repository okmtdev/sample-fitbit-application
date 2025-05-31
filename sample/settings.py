import os
from dotenv import load_dotenv

load_dotenv(verbose=True)


# ここは個人ごとのデータから取得するようにする
class Settings:
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    scopes = ["sleep", "activity", "bloodpressure"]

    def update_refresh_token(self, new_token: str, env_file_path: str = ".env") -> bool:
        lines = []
        try:
            with open(env_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"エラー: .env ファイルが見つかりません ({env_file_path})")
            return False
        except IOError as e:
            print(f"エラー: ファイルの読み込みに失敗しました ({env_file_path}): {e}")
            return False

        updated_lines = []
        token_found = False

        for line in lines:
            # 元の行の改行コードを保持するために、stripせずにキーをチェック
            # キーと値は最初の '=' で分割されると仮定
            parts = line.split("=", 1)
            current_key = ""
            if len(parts) > 0:
                current_key = parts[0].strip() # キーの前後の空白を除去

            if current_key == "REFRESH_TOKEN":
                updated_lines.append(f'REFRESH_TOKEN="{new_token}"\n')
                token_found = True
            else:
                updated_lines.append(line) # 元の行をそのまま追加

        if not token_found:
            print(f"エラー: REFRESH_TOKEN がファイル内に見つかりませんでした ({env_file_path})。更新は行われませんでした。")
            return False

        try:
            with open(env_file_path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
            print(f"REFRESH_TOKEN が正常に更新されました ({env_file_path})。")
            return True
        except IOError as e:
            print(f"エラー: ファイルへの書き込みに失敗しました ({env_file_path}): {e}")
            return False
