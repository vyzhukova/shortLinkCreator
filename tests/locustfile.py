from locust import HttpUser, task, between
import random
import string

class ShortLinkUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        password = "pass"
        self.client.post("/register", json={"username": username, "password": password})
        resp = self.client.post("/login", data={"username": username, "password": password})
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def create_link(self):
        url = f"https://example.com/{random.randint(1, 100000)}"
        with self.client.post("/links/shorten", json={"original_url": url}, headers=self.headers, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Failed to create link: {resp.status_code}")

    @task(1)
    def access_link(self):
        code = "test" 
        self.client.get(f"/links/{code}", name="/[code]", allow_redirects=False)

    @task(1)
    def get_stats(self):
        code = "test"
        self.client.get(f"/links/{code}/stats", name="/links/[code]/stats")