import asyncio

import aiohttp
from aiohttp import web

class Crawler(object): 
    def __init__(self, loop, scraper, max_connections=30, dl_cutoff=100):
        self.loop = loop
        self.scraper = scraper
        self.sem = asyncio.Semaphore(max_connections)#For preventing accidental DOS
        self.queued = set()
        self.processing = set()
        self.done = set()
        self.failed = set()
        self.dl_cutoff = dl_cutoff

    def queue(self, url):
        seen = bool(url in self.queued or url in self.processing or url in self.done)
        if not seen:
            self.queued.add(url)
            task = asyncio.Task(self.process_page(url))
        
        
    async def get_html(self,url):
        html = None
        err = None
        resp = await aiohttp.get(url)
        if resp.status == 200:
            html = await resp.read()
        else:
            if resp.status == 404:
                err = web.HTTPNotFound
            else:
                err = aiohttp.HttpProcessingError(
                    code=resp.status, message=resp.reason,
                    headers=resp.headers)
        resp.close()
        if(err):
            raise err
        return html


    async def process_page(self, url):
        res = {}
        self.queued.remove(url)
        self.processing.add(url)
        try:
            with (await self.sem):#Limits number of concurrent requests
                html = await self.get_html(url)
        except Exception as e:
            print('Resource not found: ' + url)
            self.failed.add(url)
        else:
             success, targets = self.scraper.process(url, html)
             if success:
                 for target in targets:
                     self.queue(target)
                 self.done.add(url)
             else:
                 self.failed.add(url)

        finally:
            self.processing.remove(url)

        return res

    async def crawl(self):
        while (self.queued or self.processing) and len(self.done) <= self.dl_cutoff:
            await asyncio.sleep(1)
        
    def launch(self, urls):
        for url in urls:
            self.queue(url)
        task = asyncio.Task(self.crawl())
        self.loop.run_until_complete(task)