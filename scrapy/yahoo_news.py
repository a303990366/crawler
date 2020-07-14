import scrapy
import json
import time
from ..items import ArticleItem,CommentItem,RepliesItem
class YahooSpider(scrapy.Spider):
    name='yahoo'
    keywords=['預報','溫度','日環蝕','颱風路徑','寒冬','發燒','氣候服務', '降雨', '下雨', '救災', '災害', '低溫預報', '落山風',
             'COP', '聯合國氣候大會', '高溫', '登革熱', '日偏蝕', '天文氣象', '寒流', '強風', '芒果', '高低溫預報', '懸日', '淹水',
             '龍眼', '欠收', '城鄉預報', '劇烈天氣', '暖冬', '積水', '天氣預測', '氣溫', '濃霧', '颱風雨量', '歉收', '暖化', '颱風', 
             '颱風預報','災防', '風力發電', '觀光', '預報不準', '氣候變遷', '停水', '綠能', '豐收', '再生能源', '感冒', '防災', '天氣',
             '太陽能', '香蕉','防災假', '警報', '農業氣象', 'COP25', '天氣風險', '乾旱', '氣候推估', '海平面上昇', '天氣預報', '長浪',
             '高溫預報', '韌性', '旅遊', '暴潮', '聯合國氣候會議', '缺水', '光電', '地震', '寒潮', '鋒面', '土石流', '極端氣候', '颱風強度',
             '放假', '流感', '氣象官網', '瘋狗浪', '氣象達人', '颱風假', '體感溫度', '梅雨']
    url_origin='https://tw.news.yahoo.com/_td-news/api/resource/NewsSearchService;query='#+keyword+';offset='
    custom_settings={
        'ITEM_PIPELINES':{
                'tutorial.pipelines.YahooPipeline':500#修改
        }
    }#指定的pipeline
    def change_time(self,item):
        t=int(item)
        t=time.localtime(t)
        return time.strftime("%Y-%m-%d",t)
    
    def start_requests(self):
        for keyword in self.keywords:
            count=0           
            url=self.url_origin+keyword+';offset='+str(count)
            yield scrapy.Request(url,callback=self.parse,meta={'keyword':keyword,
                                                               'count':count})
                
    def parse(self,response):
        data=json.loads(response.text)
        article_links=[]
        keyword=response.meta['keyword']
        count=response.meta['count']
        
        if len(data)>int(0):
            for i in range(0,len(data)):
                article_links.append(data[i]['url'])
            yield from response.follow_all(article_links,callback=self.article_parse)
            count+=10
            url=self.url_origin+keyword+';offset='+str(count)
            yield scrapy.Request(url,callback=self.parse,
                                 meta={'keyword':keyword,'count':count})
            
    def article_parse(self,response):
        items_a=ArticleItem()
        
        texts=''
        for i in response.xpath('//article[@itemprop="articleBody"]//p/text()').getall():
            texts+=i
            
        
        items_a['title']=response.xpath('//*[@id="Col1-1-HeadComponentTitle"]/h1/text()').get()
        items_a['author_name']=response.xpath('//*[@id="Col1-2-HeadComponentAttribution"]/div[2]/span/span/a/text()').get()
        items_a['post_id']=response.xpath('//a[@data-sharetype="line"]/@data-ylk').get().split('g:')[1].split(';',1)[0]
        items_a['post_time']=response.xpath('//time/text()').get()
        items_a['context']=texts
        items_a['platform_id']='Yahoo'
        url='https://tw.news.yahoo.com/_td/api/resource/canvass.getMessageListForContext_ns;apiVersion=v1;context='+items_a['post_id']+';count=30;lang=zh-Hant-TW;namespace=yahoo_content;oauthConsumerKey=frontpage.oauth.canvassKey;oauthConsumerSecret=frontpage.oauth.canvassSecret;rankingProfile=;sortBy=popular'
        yield scrapy.Request(url,callback=self.comment_parse,meta={'post_id':items_a['post_id'],
                                                                   'platform_id':items_a['platform_id']})
        yield items_a

    def comment_parse(self,response):
        items_c=CommentItem()
        
        data=json.loads(response.text)
        if len(data['canvassMessages'])!=0:
            for comment in range(0,len(data['canvassMessages'])):
                items_c['post_id']=response.meta['post_id']
                items_c['author_id']=data['canvassMessages'][comment]['meta']['author']['guid']
                items_c['author_name']=data['canvassMessages'][comment]['meta']['author']['nickname']
                items_c['post_time']=self.change_time(data['canvassMessages'][comment]['meta']['createdAt'])
                items_c['context']=data['canvassMessages'][comment]['details']['userText']
                items_c['platform_id']=response.meta['platform_id']
                items_c['comment_id']=data['canvassMessages'][comment]["messageId"]
                items_c['like_num']=data['canvassMessages'][comment]["reactionStats"]["upVoteCount"]
                
                if data['canvassMessages'][comment]['reactionStats']['replyCount']>0:
                    #message_id=data['canvassMessages'][comment]['messageId']
                    url='https://tw.news.yahoo.com/_td/api/resource/canvass.getReplies_ns;action=showNext;apiVersion=v1;context='+items_c['post_id']+';count=30;index=null;lang=zh-Hant-TW;messageId='+items_c['comment_id']+';namespace=yahoo_content;oauthConsumerKey=frontpage.oauth.canvassKey;oauthConsumerSecret=frontpage.oauth.canvassSecret'
                    yield scrapy.Request(url,callback=self.reply_parse,
                                         meta={'post_id':items_c['post_id'],
                                               'comment_id':items_c['comment_id'],
                                               'platform_id':response.meta['platform_id']})

                yield items_c
                
            if data["nextIndex"] != None:
                if ';index=' in response.url:
                    url=response.url.split(';index=')[0]
                    url=url+';index='+data["nextIndex"]
                else:
                    url=response.url+';index='+data["nextIndex"]
                yield scrapy.Request(url,callback=self.comment_parse,meta={'post_id':response.meta['post_id'],
                                                                           'platform_id':response.meta['platform_id']})
    def reply_parse(self,response):
        items_r=RepliesItem()
                
        data=json.loads(response.text)
        for i in range(0,len(data)):
            items_r['reply_id']=data[i]['replyId']
            items_r['author_id']=data[i]['meta']['author']['guid']
            items_r['author_name']=data[i]['meta']['author']['nickname']
            items_r['context']=data[i]['details']['userText']
            items_r['post_id']=response.meta['post_id']
            items_r['post_time']=self.change_time(data[i]['meta']['createdAt'])
            items_r['comment_id']=response.meta['comment_id']
            items_r['platform_id']=response.meta['platform_id']
            yield items_r

                
        
                
