import scrapy
from ..items import ArticleItem,CommentItem,RepliesItem
import time
import re

class PchomeSpider(scrapy.Spider):
    name='pchome'
    custom_settings={
        'ITEM_PIPELINES':{
                'tutorial.pipelines.PchomePipeline':300#修改
        }
    }#指定的pipeline
    allowed_domains=['news.pchome.com.tw']
    keywords=['預報','溫度','日環蝕','颱風路徑','寒冬','發燒','氣候服務', '降雨', '下雨', '救災', '災害', '低溫預報', '落山風',
             'COP', '聯合國氣候大會', '高溫', '登革熱', '日偏蝕', '天文氣象', '寒流', '強風', '芒果', '高低溫預報', '懸日', '淹水',
             '龍眼', '欠收', '城鄉預報', '劇烈天氣', '暖冬', '積水', '天氣預測', '氣溫', '濃霧', '颱風雨量', '歉收', '暖化', '颱風', 
             '颱風預報','災防', '風力發電', '觀光', '預報不準', '氣候變遷', '停水', '綠能', '豐收', '再生能源', '感冒', '防災', '天氣',
             '太陽能', '香蕉','防災假', '警報', '農業氣象', 'COP25', '天氣風險', '乾旱', '氣候推估', '海平面上昇', '天氣預報', '長浪',
             '高溫預報', '韌性', '旅遊', '暴潮', '聯合國氣候會議', '缺水', '光電', '地震', '寒潮', '鋒面', '土石流', '極端氣候', '颱風強度',
             '放假', '流感', '氣象官網', '瘋狗浪', '氣象達人', '颱風假', '體感溫度', '梅雨']
    #setting pipeline
    def start_requests(self):
        
        for keyword in self.keywords:
            url='https://news.pchome.com.tw/search.php?k='+keyword+'&submit=Go'
            yield scrapy.Request(url,callback=self.parse)
    
    def parse(self,response):
        article_links=[link for link in response.xpath('//section/div[@class="channel_newssection"]/p[1]/a/@href').getall()]
        if '&p=' not in response.url:
            next_page=response.xpath('//*[@id="pages"]/a[5]/@href').get()
            #next_page_text=response.xpath('//*[@id="pages"]/a[5]/text()').get()
        else:
            next_page=response.xpath('//*[@id="pages"]/a[7]/@href').get()
            #next_page_text=response.xpath('//*[@id="pages"]/a[7]/text()').get()
        yield from response.follow_all(article_links,callback=self.article_parse)
        
        #if next_page_text == '下一頁':
        if next_page is not None:
            yield response.follow(next_page,callback=self.parse)
        
    def article_parse(self,response):
        items=ArticleItem()
        texts=''
        for i in response.xpath('//*[@id="newsContent"]/div/text()').getall():
            texts+=i#之後去除\n
        items['title']=response.xpath('//*[@id="iCliCK_SafeGuard"]/text()').get()
        items['post_time']=response.xpath('//*[@id="cont-area"]/div/article/section[1]/ul/li[1]/time/@datetime').get()
        items['author_name']=response.xpath('//*[@id="cont-area"]/div/article/section[3]/ul/li[1]/a/text()').get()
        items['context']=texts
        items['platform_id']=self.name
        items['url']=response.url
        yield items
