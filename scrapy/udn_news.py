import scrapy
import json
from ..items import ArticleItem,CommentItem,RepliesItem
import time
import re
class UdnSpider(scrapy.Spider):
    name = 'udn'
    keywords=['預報','溫度','日環蝕','颱風路徑','寒冬','發燒','氣候服務', '降雨', '下雨', '救災', '災害', '低溫預報', '落山風',
        'COP', '聯合國氣候大會', '高溫', '登革熱', '日偏蝕', '天文氣象', '寒流', '強風', '芒果', '高低溫預報', '懸日', '淹水',
        '龍眼', '欠收', '城鄉預報', '劇烈天氣', '暖冬', '積水', '天氣預測', '氣溫', '濃霧', '颱風雨量', '歉收', '暖化', '颱風', 
        '颱風預報','災防', '風力發電', '觀光', '預報不準', '氣候變遷', '停水', '綠能', '豐收', '再生能源', '感冒', '防災', '天氣',
        '太陽能', '香蕉','防災假', '警報', '農業氣象', 'COP25', '天氣風險', '乾旱', '氣候推估', '海平面上昇', '天氣預報', '長浪',
        '高溫預報', '韌性', '旅遊', '暴潮', '聯合國氣候會議', '缺水', '光電', '地震', '寒潮', '鋒面', '土石流', '極端氣候', '颱風強度',
        '放假', '流感', '氣象官網', '瘋狗浪', '氣象達人', '颱風假', '體感溫度', '梅雨']
             
    article_count=0          
    allowed_domains = ['udn.com']
    custom_settings={
        'ITEM_PIPELINES':{
                'tutorial.pipelines.UdnNewsPipeline':300#修改
        }
    }#指定的pipeline
    app_id='350231215126101'
    channel='https%3A%2F%2Fstaticxx.facebook.com%2Fconnect%2Fxd_arbiter.php%3Fversion%3D46%23cb%3Df1fe07122f86c%26domain%3Dudn.com%26origin%3Dhttps%253A%252F%252Fudn.com%252Ff21e89d1ba97e18%26relation%3Dparent.parent'
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
            page_count=1
            url='https://udn.com/api/more?page='+str(page_count)+'&id=search:'+keyword+'&channelId=2&type=searchword'   
            yield scrapy.Request(url,callback=self.parse,meta={'page_count':page_count,
                                                               'keyword':keyword})
            

    def parse(self,response):
        
        data=json.loads(response.text)
        for i in range(0,len(data['lists'])):
            url=data['lists'][i]['titleLink']
            post_time_year=int(str(data['lists'][i]['time']['dateTime']).split('-')[0])
            if post_time_year>=2018:
        
                yield scrapy.Request(url,callback=self.article_parse)

        page_count=response.meta['page_count']
        page_count+=1
        keyword=response.meta['keyword']
        if page_count<=600:
            url='https://udn.com/api/more?page='+str(page_count)+'&id=search:'+keyword+'&channelId=2&type=searchword'
            yield scrapy.Request(url,callback=self.parse,meta={'page_count':page_count,
                                                                  'keyword':keyword})

        

    def article_parse(self,response):
        items=ArticleItem()

        texts=''
        for i in response.xpath('//section[@class="article-content__editor "]/p/text()').getall():
            texts+=i

        if  response.xpath('//span[@class="article-content__author"]/a/text()').get() is not None:
            author_name=response.xpath('//span[@class="article-content__author"]/a/text()').get()
        else:
            author_name=response.xpath('//span[@class="article-content__author"]/text()').get().strip()
            pattern=r'(.)* /'
            author_name=re.search(pattern,author_name).group().replace('/','').strip()
        items['title']=response.xpath('//h1[@class="article-content__title"]/text()').get()
        items['post_time']=response.xpath('//time[@class="article-content__time"]/text()').get()
        items['author_name']=author_name
        items['context']=texts
        items['platform_id']=self.name
        items['url']=response.url
        
        #----------like_num-----------    
        url='https://www.facebook.com/v5.0/plugins/like.php?action=like&app_id='+self.app_id+'&channel='+self.channel+'&container_width=0&href='+response.url+'&layout=button_count&locale=zh_TW&sdk=joey&share=true&show_faces=true&size=small'
        yield scrapy.Request(url,callback=self.likenum_parse,meta={'item':items},dont_filter=True)
        #----------post_id----------- 
        url='https://www.facebook.com/plugins/feedback.php?app_id='+self.app_id+'&channel='+self.channel+'&href='+response.url
        yield scrapy.Request(url,callback=self.postid_parse,meta={'item':items},dont_filter=True)
        self.article_count+=1
        print('目前共解析%d篇文章' % self.article_count)
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
            yield scrapy.FormRequest(url,formdata=self.params_0,callback=self.comment_parse,dont_filter=True,meta={'url':temp_url})
        
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
        
