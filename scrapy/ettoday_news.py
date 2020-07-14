import scrapy
from ..items import ArticleItem,CommentItem,RepliesItem
import json
import time
import re

class EtTodaySpider(scrapy.Spider):
    
    name = 'ettoday' #spider_name
    
    
    keywords=['溫度','預報','日環蝕','颱風路徑','寒冬','發燒','氣候服務', '降雨', '下雨', '救災', '災害', '低溫預報', '落山風',
         'COP', '聯合國氣候大會', '高溫', '登革熱', '日偏蝕', '天文氣象', '寒流', '強風', '芒果', '高低溫預報', '懸日', '淹水',
         '龍眼', '欠收', '城鄉預報', '劇烈天氣', '暖冬', '積水', '天氣預測', '氣溫', '濃霧', '颱風雨量', '歉收', '暖化', '颱風', 
         '颱風預報','災防', '風力發電', '觀光', '預報不準', '氣候變遷', '停水', '綠能', '豐收', '再生能源', '感冒', '防災', '天氣',
         '太陽能', '香蕉','防災假', '警報', '農業氣象', 'COP25', '天氣風險', '乾旱', '氣候推估', '海平面上昇', '天氣預報', '長浪',
         '高溫預報', '韌性', '旅遊', '暴潮', '聯合國氣候會議', '缺水', '光電', '地震', '寒潮', '鋒面', '土石流', '極端氣候', '颱風強度',
         '放假', '流感', '氣象官網', '瘋狗浪', '氣象達人', '颱風假', '體感溫度', '梅雨'
             ]
             
    app_id='146858218737386'#ettoday的app_id
    #ettoday的channel
    channel='https%3A%2F%2Fstaticxx.facebook.com%2Fconnect%2Fxd_arbiter.php%3Fversion%3D46%23cb%3Df10927eb4e538c%26domain%3Dwww.ettoday.net%26origin%3Dhttps%253A%252F%252Fwww.ettoday.net%252Ff26529478fa3674%26relation%3Dparent.parent'
    custom_settings={
        'ITEM_PIPELINES':{
                'tutorial.pipelines.EtTodayPipeline':300#修改
        }
    }#指定的pipeline
    params_0={
            'app_id': app_id,
            'limit': '10',
            '__user': '0',
            '__a': '1',
            '__req': '2',
            '__beoa': '0',
            'dpr': '1',
            '__comet_req': '1',
            'locale': 'zh_TW',
        }
    params_1={
    'app_id': params_0['app_id'],
    'limit': '10',
    '__user': '0',
    '__a': '1',
    '__req': '2',
    '__beoa': '0',
    'dpr': '1',
    '__comet_req': '0',
    'locale': 'zh_TW',
    '__sp': '1',
    }
    
    def start_requests(self):
        for keyword in self.keywords:
            yield scrapy.Request('https://www.ettoday.net/news_search/doSearch.php?keywords='
                                 +str(keyword)+'&idx=1',callback=self.parse)

    def parse(self, response):
        article_links=[]
        pattern=r'\d{4}'
        data=response.xpath('//div[@class="box_2"]')
        for i in range(0,len(data)):
            href=data[i].xpath('.//h2/a/@href').get()
            post_time=data[i].xpath('.//p/span/text()').getall()[-1]
            post_time_year=re.search(pattern,post_time).group()
            if int(post_time_year)>=2018:
                article_links.append(href)
                
        if 'page' not in response.url:
            next_page=response.xpath('//*[@id="result-list"]/div[11]/div/a[10]/@href').get()
        else:
            next_page=response.xpath('//*[@id="result-list"]/div[11]/div/a[12]/@href').get()
        for article_link in article_links:
            yield scrapy.Request(article_link,callback=self.article_parse)
        if next_page is not None:
            yield scrapy.Request(next_page,callback=self.parse)

        
    def article_parse(self,response):
        
        items=ArticleItem()
        texts=''
        for i in response.xpath('//div[@class="story"]/p/text()').getall()[1:]:
            texts+=i
        
        items['platform_id']=self.name
        items['title']=response.xpath('//h1[@class="title"]/text()').get()
        items['post_time']=response.xpath('//time[@class="date"]/text()').get().strip()
        items['author_name']=response.xpath('//div[@class="story"]/p/text()').get()
        items['context']=texts
        items['url']=response.url
        
        #----------like_num-----------    
        url='https://www.facebook.com/v5.0/plugins/like.php?action=like&app_id='+self.app_id+'&channel='+self.channel+'&container_width=0&href='+response.url+'&layout=button_count&locale=zh_TW&sdk=joey&share=true&show_faces=true&size=small'
        yield scrapy.Request(url,callback=self.likenum_parse,meta={'item':items},dont_filter=True)
        #----------post_id----------- 
        url='https://www.facebook.com/plugins/feedback.php?app_id='+self.app_id+'&channel='+self.channel+'&href='+response.url
        yield scrapy.Request(url,callback=self.postid_parse,meta={'item':items},dont_filter=True)
        
    def likenum_parse(self,response):
        items=response.meta['item']
        like_num=response.xpath('//span[@id="u_0_3"]/text()').get()
        items['like_num']=like_num

    def postid_parse(self,response):
        items=response.meta['item']
        post_id=response.text.split('targetFBID":')[1].split(',')[0].replace('"','')
        items['post_id']=str(post_id)
        temp_url=items['url']
        yield items
        
        pattern='"totalCount":\d+,'
        total_count=re.search(pattern,response.text).group()
        pattern='\d+'
        total_count=int(re.search(pattern,total_count).group())
        if total_count>0:
            url='https://www.facebook.com/plugins/comments/async/'+str(post_id)+'/pager/social/'
            yield scrapy.FormRequest(url,formdata=self.params_0,callback=self.comment_parse,meta={'url':temp_url})
        
    def comment_parse(self,response):
        
        items_c=CommentItem()
        text=json.loads(response.text.split(';',3)[-1])
        comment_id=text['payload']['commentIDs']
        afterCursor=text['payload']['afterCursor']
        temp_url=response.meta['url']
        
        for i in comment_id:
            
            author_id=text['payload']['idMap'][i]['authorID']
            author_name=text['payload']['idMap'][author_id]['name']
            context=text['payload']['idMap'][i]['body']['text']
            post_time=text['payload']['idMap'][i]['timestamp']['text'].split(' ')[0].replace('年','-').replace("月",'-').replace("日",'')
            like_num=text['payload']['idMap'][i]['likeCount']
            post_id=i.split('_')[0]
            items_c['author_id']=author_id
            items_c['platform_id']=self.name
            items_c['post_id']=post_id
            items_c['comment_id']=i 
            items_c['author_name']=author_name
            items_c['post_time']=post_time
            items_c['context']=context
            items_c['like_num']=like_num
            items_c['url']=temp_url
            yield items_c
            #----------回覆--------------
            try:
                text['payload']['idMap'][i]['public_replies']
            #如果relies存在則1.挑出該comment_id2.運行找取回覆的程式碼
                url_r='https://www.facebook.com/plugins/comments/async/comment/'+str(i)+'/pager/'
                yield scrapy.FormRequest(url_r,formdata=self.params_1,
                                         callback=self.reply_parse,meta={'comment_id':str(i),'url':temp_url})
            except:
                pass
        self.params_0['after_cursor']=afterCursor
        if afterCursor=='1':
            pass
        else:
            yield scrapy.FormRequest(response.url,formdata=self.params_0,callback=self.comment_parse,meta={'url':temp_url})
            
    def reply_parse(self,response):
        
        items_r=RepliesItem()
        text=json.loads(response.text.split(';',3)[-1])
        replies_id=text['payload']['commentIDs']
        for i in replies_id:
            items_r['reply_id']=i
            post_id=i.split('_')[0]
            author_id=text['payload']['idMap'][i]['authorID']
            items_r['author_name']=text['payload']['idMap'][author_id]['name']
            items_r['context']=text['payload']['idMap'][i]['body']['text'].replace(u'\n',u'')
            items_r['post_id']=post_id
            items_r['post_time']=text['payload']['idMap'][i]['timestamp']['text'].split(' ')[0].replace('年','-').replace("月",'-').replace("日",'')
            items_r['comment_id']=response.meta['comment_id']
            items_r['platform_id']=self.name
            items_r['author_id']=author_id
            items_r['url']=response.meta['url']
            yield items_r
        
