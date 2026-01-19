import time
from urllib.parse import unquote, quote_plus
from bs4 import BeautifulSoup
import cloudscraper
import os
from config import TIMEOUT_APKM,RESULTS_LIST,PARSER
class APKMirror:
    def __init__(self, timeout: int = TIMEOUT_APKM, results: int = RESULTS_LIST, user_agent: str = None):
        self.timeout = timeout
        self.results = results
        self.user_agent = (
            user_agent
            if user_agent
            else "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0"
        )
        self.headers = {"User-Agent": self.user_agent}
        self.base_url = "https://www.apkmirror.com"
        self.base_search = f"{self.base_url}/?post_type=app_release&searchtype=apk&s="
        self.scraper = cloudscraper.create_scraper()

    def search(self, query):
        search_url = self.base_search + quote_plus(query)
        resp = self.scraper.get(search_url, headers=self.headers)
        print(f"[search] Status: {resp.status_code}")

        soup = BeautifulSoup(resp.text, PARSER)
        apps = []
        appRow = soup.find_all("div", {"class": "appRow"})

        for app in appRow:
            try:
                app_dict = {
                    "name": app.find("h5", {"class": "appRowTitle"}).text.strip(),
                    "link": self.base_url + app.find("a", {"class": "downloadLink"})["href"],
                    "image": self.base_url + app.find("img", {"class": "ellipsisText"})["src"]
                    .replace("h=32", "h=512")
                    .replace("w=32", "w=512"),
                }
                apps.append(app_dict)
            except AttributeError:
                pass

        return apps[: self.results]

    def get_app_details(self, app_link):
        time.sleep(self.timeout)
        resp = self.scraper.get(app_link, headers=self.headers)
        print(f"[get_app_details] Status: {resp.status_code}")

        soup = BeautifulSoup(resp.text, PARSER)
        data = soup.find_all("div", {"class": ["table-row", "headerFont"]})[1]

        architecture = data.find_all("div", {"class": ["table-cell", "rowheight", "addseparator", "expand", "pad", "dowrap"]})[1].text.strip()
        android_version = data.find_all("div", {"class": ["table-cell", "rowheight", "addseparator", "expand", "pad", "dowrap"]})[2].text.strip()
        dpi = data.find_all("div", {"class": ["table-cell", "rowheight", "addseparator", "expand", "pad", "dowrap"]})[3].text.strip()
        download_link = self.base_url + data.find_all("a", {"class": "accent_color"})[0]["href"]

        return {
            "architecture": architecture,
            "android_version": android_version,
            "dpi": dpi,
            "download_link": download_link,
        }
        
    def get_download_link(self, app_download_link):
        time.sleep(self.timeout)
        resp = self.scraper.get(app_download_link, headers=self.headers)
        print(f"[get_download_link] Status: {resp.status_code}")
        return self.base_url + str(
            BeautifulSoup(resp.text, PARSER).find_all("a", {"class": "downloadButton"})[0]["href"]
        )

    def get_direct_download_link(self, app_download_url):
        time.sleep(self.timeout)
        resp = self.scraper.get(app_download_url, headers=self.headers)
        print(f"[get_direct_download_link] Status: {resp.status_code}")
        data = BeautifulSoup(resp.text, PARSER).find(
            "a",
            {
                "rel": "nofollow",
                "data-google-interstitial": "false",
                "href": lambda href: href and "/wp-content/themes/APKMirror/download.php" in href,
            },
        )["href"]
        direct_url = self.base_url + str(data)
        return direct_url
    def download(self, app_download_url):
        time.sleep(self.timeout)
        print("[download_apk] Fetching direct download link...")
        r = self.scraper.get(app_download_url,headers=self.headers, allow_redirects=True)
        final_url = r.url
        filename = unquote(final_url.split("/")[-1].split("?")[0])
        print(f"[detected_filename] {filename}")
        r = self.scraper.get(final_url, stream=True)
        os.makedirs("download", exist_ok=True)
        with open(f"download/{filename}", "wb") as f:
            for chunk in r.iter_content(chunk_size=10*1024*1024):
                if chunk:
                    f.write(chunk)

        print(f"[done] downloaded")
        return f"download/{filename}"
