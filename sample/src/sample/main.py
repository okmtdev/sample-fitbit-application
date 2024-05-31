
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    client = Client()
    print(client.get_sleep_log_list().json())

class Client():
    HOST = 'https://api.fitbit.com/'
    SLEEP_LOG_LIST_PATH = "/1.2/user/{}/sleep/list.json" # https://dev.fitbit.com/build/reference/web-api/sleep/get-sleep-log-list/
    PROFILE_PATH = "/1/user/-/profile.json"
    user_id = '23PHG5'

    def bearer_header(self):
        return {"Authorization": "Bearer " + os.environ['bearer']}

    def get_sleep_log_list(self):
        url = self.HOST + self.PROFILE_PATH.format(self.user_id)

        headers = self.bearer_header()

        params = {'sort': 'desc', 'offset': 0, 'limit': 100}
        res = httpx.get(url, headers=headers, params=params)
        return res

if __name__ == '__main__':
    main()