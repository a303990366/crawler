import scrapy
from ..items import ArticleItem,CommentItem,RepliesItem
import json,time
import re
class LineSpider(scrapy.Spider):
    name='line'
    keywords=['預報','溫度','日環蝕','颱風路徑','寒冬','發燒','氣候服務', '降雨', '下雨', '救災', '災害', '低溫預報', '落山風',
             'COP', '聯合國氣候大會', '高溫', '登革熱', '日偏蝕', '天文氣象', '寒流', '強風', '芒果', '高低溫預報', '懸日', '淹水',
             '龍眼', '欠收', '城鄉預報', '劇烈天氣', '暖冬', '積水', '天氣預測', '氣溫', '濃霧', '颱風雨量', '歉收', '暖化', '颱風', 
             '颱風預報','災防', '風力發電', '觀光', '預報不準', '氣候變遷', '停水', '綠能', '豐收', '再生能源', '感冒', '防災', '天氣',
             '太陽能', '香蕉','防災假', '警報', '農業氣象', 'COP25', '天氣風險', '乾旱', '氣候推估', '海平面上昇', '天氣預報', '長浪',
             '高溫預報', '韌性', '旅遊', '暴潮', '聯合國氣候會議', '缺水', '光電', '地震', '寒潮', '鋒面', '土石流', '極端氣候', '颱風強度',
             '放假', '流感', '氣象官網', '瘋狗浪', '氣象達人', '颱風假', '體感溫度', '梅雨']

    custom_settings={
        'ITEM_PIPELINES':{
                'tutorial.pipelines.LinePipeline':500#修改
        }
    }#指定的pipeline
    data_article_count=0
    def change_time(self,item):
        t=int(item[0:-3])
        t=time.localtime(t)
        return time.strftime("%Y-%m-%d",t)
    
    def start_requests(self):
        for keyword in self.keywords:
            count=1
            url='https://hub.line.me/search/'+keyword+'?module=news&sort=LATEST'
            yield scrapy.Request(url,callback=self.parse,meta={'url':url,
                                                               'count':count})
            

    def parse(self,response):
        count=response.meta['count']
        if count <= 134:
            article_links=[link for link in response.xpath('//div[@class="searchToday-itemsContainer"]/a/@href').getall()]
            yield from response.follow_all(article_links,callback=self.article_parse)
            #time.sleep(1)
            count+=1
            url_origin=response.meta['url']
            url=url_origin+'&pageIndex='+str(count)
            yield scrapy.Request(url,callback=self.parse,meta={'url':url_origin,
                                                               'count':count})
            

    def article_parse(self,response):
        #post_time=response.xpath('//dd[@itemprop="datePublished"]/text()').get().replace('發布時間','').strip()
        #post_time_year=int(post_time.split('年')[0])
        post_time=response.xpath('//*[@id="header"]/div/p[2]/text()')[1].get().split('日')[0]
        post_time=re.findall(r'\d+',post_time)
        post_time_year=int(post_time[0])
        if post_time_year>=2018:
            texts=''
            for i in response.xpath('//article[@class="news-content"]/p/text()').getall():
                texts+=i
            #time.sleep(1)
            items_a=ArticleItem()
            #items_a['title']=response.xpath('//*[@id="article"]/section/h2/text()').get()
            items_a['title']=response.xpath('//*[@id="header"]/h1/text()').get()
            #items_a['author_name']=response.xpath('//*[@id="article"]/section/dl/dd[1]/text()').get().strip()
            items_a['author_name']=response.xpath('//*[@id="header"]/div/p[1]/text()').get().strip()
            items_a['post_time']= post_time[0]+'-'+post_time[1]+'-'+post_time[2]
            items_a['context']=texts
            items_a['platform_id']=self.name
            temp_post_id_data=response.xpath('/html/body/script[2]/text()').get()
            temp_post_id_data=re.search(r'articleId = "\d+"',temp_post_id_data).group()
            post_id=re.search(r'\d+',temp_post_id_data).group()
            items_a['post_id']=post_id
            #items_a['post_id']=response.xpath('//script[@type="text/javascript"]').getall()[1].split(';')[2].split('"')[1]
            self.data_article_count+=1
            print('目前已解析%d則文章' % self.data_article_count)
            url='https://api.today.line.me/webapi/article/dinfo?articleIds='+items_a['post_id']+'&country=TW'
            yield scrapy.Request(url,callback=self.likenum_parse,meta={'items_a':items_a})

    def likenum_parse(self,response):
        data=json.loads(response.text)
        items_a=response.meta['items_a']
        like_num=data['result']['commentLikes'][0]["likeViews"]['count']
        items_a['like_num']=like_num
        pivot=1
        url='https://api.today.line.me/webapi/comment/list?articleId='+items_a['post_id']+'&limit=100&country=TW&replyCount=true'
        #comment_url
        yield scrapy.Request(url,callback=self.comment_parse,meta={'items_a':items_a,
                                                                   'url_origin':url,
                                                                   'pivot':pivot})
        yield items_a

    def comment_parse(self,response):
        items_c=CommentItem()
        data=json.loads(response.text)
        #time.sleep(1)
        
        for i in range(0,len(data['result']['comments']['comments'])):
            items_c['comment_id']=data['result']['comments']['comments'][i]['commentSn']
            try:
                items_c['author_name']=data['result']['comments']['comments'][i]['displayName']
            except:
                pass
            items_c['context']=data['result']['comments']['comments'][i]['contents'][0]['extData']['content']
            items_c['post_id']=data['result']['comments']['comments'][i]['articleId']
            items_c['post_time']=self.change_time(str(data['result']['comments']['comments'][i]['createdDate']))
            items_c['platform_id']=response.meta['items_a']['platform_id']
            try:
                items_c['like_num']=data['result']['comments']['comments'][i]['ext']['likeCount']['up']
            except:
                items_c['like_num']=0

            reply_count=int(data['result']['comments']['comments'][i]['ext']['replyCount'])
            if reply_count>0:
                url=response.url+'&parentCommentSn='+items_c['comment_id']
                yield scrapy.Request(url,callback=self.reply_parse,meta={'items_c':items_c})
            
            yield items_c

        if data['result']['comments']['hasMore']==True:
            url_origin=response.meta['url_origin']
            pivot=response.meta['pivot']
            url=url_origin+'&pivot='+str(pivot*100)
            pivot+=1
            yield scrapy.Request(url,callback=self.comment_parse,meta={'items_a':response.meta['items_a'],
                                                                       'url_origin':url_origin,
                                                                       'pivot':pivot})
    def reply_parse(self,response):
        
        items_r=RepliesItem()
        data=json.loads(response.text)
        for i in range(0,len(data['result']['comments']['comments'])):
            items_r['reply_id']=data['result']['comments']['comments'][i]['commentSn']
            #items_r['author_id']=
            try:
                items_r['author_name']=data['result']['comments']['comments'][i]['displayName']
            except:
                items_r['author_name']=None
            items_r['context']=data['result']['comments']['comments'][i]['contents'][0]['extData']['content']
            items_r['post_id']=data['result']['comments']['comments'][i]['articleId']
            items_r['post_time']=self.change_time(str(data['result']['comments']['comments'][0]['createdDate']))
            items_r['comment_id']=data['result']['comments']['comments'][i]['parentCommentSn']
            items_r['platform_id']=response.meta['items_c']['platform_id']
            yield items_r
