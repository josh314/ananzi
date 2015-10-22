import asyncio
import logging

import aiohttp

from crawler import Crawler

class DummyScraper(object):
    def __init__(self):
        pass

    def process(self, url, html):
        print("Processing: " + url)
        return {}
        
#logging.basicConfig(level=logging.DEBUG)

urls = [
    'http://www.google.com',
    'http://www.wikipedia.org/wiki/Barack_Obama',
    'http://reddit.com',
    'http://fhqwhgads.com/',
]

loop = asyncio.get_event_loop()
#loop.set_debug(True)

ananzi = Crawler(loop, DummyScraper())
ananzi.launch(urls)
loop.close()
