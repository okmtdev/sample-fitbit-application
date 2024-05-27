
import httpx

def main():
    print("main")
    client = Client()
    print(client.get_sleep_log_list())

class Client():
    HOST = 'https://api.fitbit.com/'
    SLEEP_LOG_LIST_PATH = "/1.2/user/{}/sleep/list.json" # https://dev.fitbit.com/build/reference/web-api/sleep/get-sleep-log-list/
    user_id = 'C3HCMK'

    def bearer_header(self):
        return {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1BIRzUiLCJzdWIiOiJDM0hDTUsiLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJyc29jIHJlY2cgcnNldCByb3h5IHJwcm8gcm51dCByc2xlIHJjZiByYWN0IHJsb2MgcnJlcyByd2VpIHJociBydGVtIiwiZXhwIjoxNzE2NjI4MTMzLCJpYXQiOjE3MTY1OTkzMzN9.j9OZWRs0S84G1Pyzrir-pdfgxSIxGJs8i9IzgigzPAk"}

    def get_sleep_log_list(self):
        print("get_sleep_log_list")
        url = self.HOST + self.SLEEP_LOG_LIST_PATH.format(self.user_id)
        print(url)

        headers = self.bearer_header()

        res = httpx.get(url, headers=headers)
        return res

if __name__ == '__main__':
    main()