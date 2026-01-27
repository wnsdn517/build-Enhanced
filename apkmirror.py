import time,cloudscraper,os
from urllib.parse import unquote,quote_plus
from bs4 import BeautifulSoup
from tqdm import tqdm

class APKMirror:
    def __init__(self,timeout:int=0,results:int=5,user_agent:str=None):
        self.timeout,self.results=timeout,results
        self.user_agent=user_agent or"Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0"
        self.headers,self.base_url={"User-Agent":self.user_agent},"https://www.apkmirror.com"
        self.base_search=f"{self.base_url}/?post_type=app_release&searchtype=apk&s="
        self.scraper=cloudscraper.create_scraper()

    def search(self,query):
        soup=BeautifulSoup(self.scraper.get(self.base_search+quote_plus(query),headers=self.headers,timeout=30).text,"html.parser")
        apps=[]
        for app in soup.find_all("div",{"class":"appRow"})[:self.results]:
            try:
                if not(t:=app.find("h5",{"class":"appRowTitle"}))or not(l:=app.find("a",{"class":"downloadLink"}))or not(i:=app.find("img",{"class":"ellipsisText"})):continue
                apps.append({"name":t.text.strip(),"link":self.base_url+l["href"],"image":self.base_url+i["src"].replace("h=32","h=512").replace("w=32","w=512")})
            except(AttributeError,KeyError,TypeError):continue
        return apps

    def get_app_details(self,app_link):
        time.sleep(self.timeout)
        soup=BeautifulSoup(self.scraper.get(app_link,headers=self.headers,timeout=30).text,"html.parser")
        rows=soup.find_all("div",{"class":["table-row","headerFont"]})
        if len(rows)<2:raise ValueError("Insufficient table rows")
        links=rows[1].find_all("a",{"class":"accent_color"})
        if not links:raise ValueError("Missing download link")
        return self.get_download_link(self.base_url+links[0]["href"])

    def get_download_link(self,app_download_link):
        time.sleep(self.timeout)
        soup=BeautifulSoup(self.scraper.get(app_download_link,headers=self.headers,timeout=30).text,"html.parser")
        if not(btn:=soup.find("a",{"class":"downloadButton"})):raise ValueError("Download button not found")
        return self.get_direct_download_link(self.base_url+btn["href"])

    def get_direct_download_link(self,app_download_url):
        time.sleep(self.timeout)
        soup=BeautifulSoup(self.scraper.get(app_download_url,headers=self.headers,timeout=30).text,"html.parser")
        if not(data:=soup.find("a",{"rel":"nofollow","data-google-interstitial":"false","href":lambda h:h and"/wp-content/themes/APKMirror/download.php"in h})):
            raise ValueError("Direct download link not found")
        return self.download(self.base_url+data["href"])

    def download(self,app_download_url,output_dir="download"):
        time.sleep(self.timeout)
        r=self.scraper.head(app_download_url,headers=self.headers,allow_redirects=True)
        filename=unquote(r.url.split("/")[-1].split("?")[0])
        if len(filename)>200:
            name,ext=filename.rsplit('.',1);filename=f"{name[:150]}.{ext}"
        os.makedirs(output_dir,exist_ok=True)
        filepath=os.path.join(output_dir,filename)
        r=self.scraper.get(r.url,headers=self.headers,stream=True)
        total=int(r.headers.get('content-length',0))
        with open(filepath,"wb")as f:
            with tqdm(total=total,unit='B',unit_scale=True,unit_divisor=1024,desc=filename[:40],bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}]',ncols=80,miniters=1,dynamic_ncols=False,leave=True)as pbar:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:pbar.update(f.write(chunk))
        print(f"\n[done] Downloaded")
        return filepath
