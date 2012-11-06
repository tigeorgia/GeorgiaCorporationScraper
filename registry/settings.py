# Scrapy settings for registry project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'registry'

SPIDER_MODULES = ['registry.spiders']
NEWSPIDER_MODULE = 'registry.spiders'

#DEBUG ONLY
DEPTH_PRIORITY = 1
SCHEDULER_DISK_QUEUE = 'scrapy.squeue.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeue.FifoMemoryQueue'

#COOKIES_DEBUG = True
# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'registry (+http://www.yourdomain.com)'
