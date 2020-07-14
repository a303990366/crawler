import scrapy 
import time
from ..items import ArticleItem,CommentItem,RepliesItem
import json
import re

class SetnSpider(scrapy.Spider):
    name='setn'
    page_count=1
    

    app_id='105440539523'#ettoday的app_id
    #ettoday的channel
    channel='https%3A%2F%2Fstaticxx.facebook.com%2Fconnect%2Fxd_arbiter.php%3Fversion%3D46%23cb%3Dfed4db16ad89c8%26domain%3Dwww.setn.com%26origin%3Dhttps%253A%252F%252Fwww.setn.com%252Ff2d66588822a6f8%26relation%3Dparent.parent'
    custom_settings={
        'DOWNLOAD_DELAY':0.5,
        'ITEM_PIPELINES':{
                'tutorial.pipelines.SetnPipeline':300#修改
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
        yield scrapy.Request('https://www.setn.com/project.aspx?ProjectID=3839',callback=self.parse)
        
    def parse(self,response):
        article_links=[link for link in response.xpath('//div[@class="news-title"]/h3/a/@href').getall()]
        self.page_count+=1
        yield from response.follow_all(article_links,callback=self.article_parse)
        if self.page_count<=10:
            
            yield scrapy.Request('https://www.setn.com/project.aspx?ProjectID=3839&p='+str(self.page_count),callback=self.parse)
        
    def article_parse(self,response):
        items=ArticleItem()
        time.sleep(1)
        if '吳德榮' in response.xpath('//div[@id="Content1"]/p/text()').get():
            author_name='吳德榮'
        else:
            author_name=response.xpath('//div[@id="Content1"]/p/text()').get().split('／')[0]
        texts=''
        for i in response.xpath('//div[@id="Content1"]/p/text()').getall()[1:]:
            texts+=i
        
        items['title']=response.xpath('//h1[@class="news-title-3"]/text()').get()
        items['post_time']=response.xpath('//time[@class="page-date"]/text()').get()
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
                                         callback=self.reply_parse,meta={'comment_id':str(i),'url':temp_url},dont_filter=True)
            except:
                pass
        self.params_0['after_cursor']=afterCursor
        if afterCursor=='1':
            pass
        else:
            yield scrapy.FormRequest(response.url,formdata=self.params_0,callback=self.comment_parse,dont_filter=True,meta={'url':temp_url})
            
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
        
