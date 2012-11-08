# Scrapy settings for registry project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

#COOKIES_DEBUG = True
BOT_NAME = 'registry'

RETRY_TIMES = 9

SPIDER_MODULES = ['registry.spiders']
NEWSPIDER_MODULE = 'registry.spiders'
AUTOTHROTTLE_ENABLED = True

ITEM_PIPELINES = [
    'registry.pipelines.MultiFileJsonLinesPipeline'
]

#DOWNLOAD_DELAY = 0.5
CONCURRENT_REQUESTS_PER_DOMAIN = 8

#DEBUG ONLY
#DEPTH_PRIORITY = 1
#SCHEDULER_DISK_QUEUE = 'scrapy.squeue.PickleFifoDiskQueue'
#SCHEDULER_MEMORY_QUEUE = 'scrapy.squeue.FifoMemoryQueue'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'registry (+http://www.yourdomain.com)'
