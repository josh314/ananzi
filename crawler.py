import signal
import asyncio

import aiohttp
from aiohttp import web

class Crawler(object): 
    def __init__(self, loop, scraper, max_connections=30, dl_cutoff=100):
        self.loop = loop
        self.scraper = scraper
        self.sem = asyncio.Semaphore(max_connections)#For preventing accidental DOS
        self.queue = set()
        self.processing = set()
        self.done = set()
        self.failed = set()
        self.dl_cutoff = dl_cutoff

    def enqueue(self, url):
        seen = bool(url in self.queue or url in self.processing or url in self.done)
        if not seen:
            self.queue.add(url)
            task = asyncio.Task(self.process_page(url))
        
        
    @asyncio.coroutine
    def get_html(self,url):
        html = None
        err = None
        resp = yield from aiohttp.get(url)
        if resp.status == 200:
            html = yield from resp.read()
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

    @asyncio.coroutine
    def process_page(self, url):
        res = {}
        self.queue.remove(url)
        self.processing.add(url)
        try:
            with (yield from self.sem):#Limits number of concurrent requests
                html = yield from self.get_html(url)
        except Exception as e:
            print('Resource not found: ' + url)
            self.failed.add(url)
        else:
             success, targets = self.scraper.process(url, html)
             if success:
                 for target in targets:
                     self.enqueue(target)
                 self.done.add(url)
             else:
                 self.failed.add(url)

        finally:
            self.processing.remove(url)

        return res

    @asyncio.coroutine
    def crawl(self):
        while (self.queue or self.processing) and len(self.done) <= self.dl_cutoff:
            yield from asyncio.sleep(1)
        
    def launch(self, urls):
        # queue up initial urls 
        for url in urls:
            self.enqueue(url)
        task = asyncio.Task(self.crawl())
        try:
            self.loop.add_signal_handler(signal.SIGINT, self.loop.stop)
        except RuntimeError:
            pass
        self.loop.run_until_complete(task)
