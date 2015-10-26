import signal
import asyncio

import aiohttp
from aiohttp import web

class Crawler(object): 
    def __init__(self, loop, scraper, max_connections=30, traversal="breadth-first"):
        self.loop = loop
        self.scraper = scraper
        self.sem = asyncio.Semaphore(max_connections)#For preventing accidental DOS
        #Set queue type based upon traversal type
        if traversal == "depth-first":
            self.queue = asyncio.LifoQueue()
        elif traversal == "breadth-first":
            self.queue = asyncio.Queue()
        else:
            raise ValueError("Unknown traversal type. Use 'breadth-first' or 'depth-first'.")
        self.processing = set()
        self.done = set()
        self.failed = set()
        self.seen = set()

    def enqueue(self, url):
        if url not in self.seen:
            self.seen.add(url)
            self.queue.put_nowait(url)
        
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

    @asyncio.coroutine
    def crawl(self):
        while True:
            try:
                url = yield from asyncio.wait_for(self.queue.get(),5)
                self.loop.create_task(self.process_page(url))
            except asyncio.TimeoutError:
                print("No more pages to crawl.")
                break
        
    def launch(self, urls):
        # queue up initial urls 
        for url in urls:
            self.enqueue(url)
        task = self.loop.create_task(self.crawl())
        try:
            self.loop.add_signal_handler(signal.SIGINT, self.loop.stop)
        except RuntimeError:
            pass
        self.loop.run_until_complete(task)

