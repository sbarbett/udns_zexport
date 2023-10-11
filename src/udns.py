import requests

class UltraApi:
    def __init__(self, username=None, password=None, token=None):
        self.username = username
        self.password = password
        self.token = token
        self.base_url = "https://api.ultradns.com"
        self.access_token = str()
        self.refresh_token = str()
        self._auth()

    def _auth(self):
        if self.token:
            print("Warning: Passing a Bearer token directly means it cannot be refreshed.")
            self.access_token = self.token
            self.refresh_token = None
        else:
            payload = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password
            }
            resp = requests.post(f"{self.base_url}/authorization/token", data=payload)
            resp.raise_for_status()
            self.access_token = resp.json().get('accessToken')
            self.refresh_token = resp.json().get('refreshToken')

    def _refresh(self):
        if self.refresh_token:
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            resp = requests.post(f"{self.base_url}/authorization/token", data=payload)
            resp.raise_for_status()
            self.access_token = resp.json().get('accessToken')
            self.refresh_token = resp.json().get('refreshToken')
        else:
            raise Exception("Error: Your token cannot be refreshed. Retry using a username/password")

    def _headers(self, content_type=None):
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "Shane's UDNS Client"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def post(self, uri, payload=None):
        return self._call(uri, "POST", payload=payload)

    def get(self, uri, params={}, content_type=None):
        # GET requests should always be x-www-form-urlencoded, but the UDNS endpoints inexplicably require "application/json"
        if content_type:
            return self._call(uri, "GET", params=params, content_type=content_type)
        else:
            return self._call(uri, "GET", params=params)

    def delete(self, uri, params={}):
        # DELETE requests should, also, always be x-www-form-urlencoded
        return self._call(uri, "DELETE", params=params, content_type="x-www-form-urlencoded")

    def _call(self, uri, method, params=None, payload=None, retry=True, content_type="application/json"):
        resp = requests.request(method, self.base_url+uri, params=params, data=payload, headers=self._headers(content_type))

        if resp.status_code == requests.codes.NO_CONTENT:
            # DELETE requests and a few other things return no response body
            return {}

        if resp.headers['Content-Type'] == 'application/zip':
            # Return the bytes. Zone exports return zip files
            return resp.content

        if resp.headers['Content-Type'] == 'text/plain':
            # Return plain text. If you request a zone export with 1 domain, it returns a plain text zone file
            return resp.text

        if resp.status_code == requests.codes.ACCEPTED:
            # If there's a task ID in the header, add it to the JSON so the result can be retrieved
            response_data = resp.json()
            response_data.update({"task_id": resp.headers['X-Task-Id']})
            return response_data

        if resp.status_code == 401 and retry:
            # Refresh the token if it expired, then try again
            self._refresh()
            return self._call(uri, method, params, payload, False)

        # Raise any error statuses. Since the UDNS API also produces a response body in most cases, print that too
        try:
            resp.raise_for_status()
        except Exception as e:
            print(resp.text)
            raise

        # Everything else should be JSON (hopefully)
        return resp.json()
