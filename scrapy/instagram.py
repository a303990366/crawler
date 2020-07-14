import scrapy
import json
import time
from ..items import ArticleItem,CommentItem,RepliesItem
import re

#流程:
#     1.進入目標網站利用正則表達式獲取帳號id
#     2.利用查詢文章的網址搭配帳號id獲取文章的json檔，並找出end_cursor作為進行下一次查詢的參數
#     3.從文章json檔獲取文章的留言查詢參數short_code
#     4.利用查詢留言的網址搭配short_code獲取留言的json檔，並找出comment_end_cursor作為進行下一次查詢的參數(可順便獲取留言回覆)

class InstagramSpider(scrapy.Spider):
    name='instagram'
    website=[
        'https://www.instagram.com/typhoon_mi/',
        'https://www.instagram.com/cwb_earthquake/',
        'https://www.instagram.com/weather_0228/',
        'https://www.instagram.com/weather_centre/',
        'https://www.instagram.com/weather.taiwan/',
        'https://www.instagram.com/professional_meteorology_hksar/',
        'https://www.instagram.com/weatherrisk/'
        ]
    custom_settings={
    'ITEM_PIPELINES':{
            'tutorial.pipelines.InstagramPipeline':300#修改
        }
    }#指定的pipelin
    def change_time(self,item):
        t=int(item)
        t=time.localtime(t)
        return time.strftime("%Y-%m-%d",t)
    
    def start_requests(self):
        for web in range(0,len(self.website)):
            url=self.website[web]
            yield scrapy.Request(url,callback=self.parse)
            
    def parse(self,response):
        pattern=r'"profilePage_\d+"'
        temp=re.search(pattern,response.text).group()
        pattern='\d+'
        account_id=re.search(pattern,temp).group()
        url_origin='https://www.instagram.com/graphql/query/?query_hash=d496eb541e5c789274548bf473cc553e&variables={"id":"account_id","first":50}'
        url=url_origin.replace('account_id',account_id)
        
        yield scrapy.Request(url,callback=self.article_parse,meta={'url_origin':url})           
        
    def article_parse(self,response):
        time.sleep(5)
        data=json.loads(response.text)
        end_cursor=data['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
        items_a=ArticleItem()
        
        for i in range(0,len(data['data']['user']['edge_owner_to_timeline_media']['edges'])):
            post_time=self.change_time(int(data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']['taken_at_timestamp']))
            pattern=r'\d{4}'
            post_time_year=re.search(pattern,str(post_time)).group()
            if int(post_time_year)>=2018:
                context=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']['edge_media_to_caption']['edges'][0]['node']['text']        
                like_num=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']['edge_media_preview_like']['count']
                post_id=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']['id']
                short_code=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']['shortcode']
                author_id=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']["owner"]['id']
                author_name=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']["owner"]['username']

                items_a['author_name']=author_name
                items_a['author_id']=author_id
                items_a['context']=context
                items_a['platform_id']=self.name
                items_a['post_id']=post_id
                items_a['post_time']=post_time
                items_a['like_num']=like_num

                comment_count=data['data']['user']['edge_owner_to_timeline_media']['edges'][i]['node']['edge_media_to_comment']['count']
                if int(comment_count)>0:
                    url='https://www.instagram.com/graphql/query/?query_hash=a92f76e852576a71d3d7cef4c033a95e&variables={"shortcode":"short_code","child_comment_count":3,"fetch_comment_count":40,"parent_comment_count":24,"has_threaded_comments":true}'.replace('short_code',short_code)

                    yield scrapy.Request(url,callback=self.comment_parse,meta={'post_id':post_id,
                                                                                'short_code':short_code})

                yield items_a
        if end_cursor !=None:
            url=response.meta['url_origin'].split('}')[0]+',"after":"'+end_cursor+'"}'
            yield scrapy.Request(url,callback=self.article_parse,meta={'url_origin':response.meta['url_origin']})
 
    def comment_parse(self,response):
        
        items_c=CommentItem()
        items_r=RepliesItem()
        data=json.loads(response.text)
        
        time.sleep(5)#5
        for i in range(0,len(data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'])):
            comment_id=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['id']#comment_id
            context=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['text']#context
            post_time=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['created_at']#post_time
            author_name=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['owner']['username']#author_name
            like_num=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_liked_by']['count']#like_num
            items_c['comment_id']=comment_id
            items_c['author_name']=author_name
            items_c['context']=context
            items_c['post_id']=response.meta['post_id']
            items_c['post_time']=self.change_time(post_time)
            items_c['platform_id']=self.name
            items_c['like_num']=like_num

            reply_count=len(data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_threaded_comments']['edges'])
            if reply_count<=10:
                for j in range(0,reply_count):
                    reply_id=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_threaded_comments']['edges'][j]['node']['id']
                    context=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_threaded_comments']['edges'][j]['node']['text']
                    post_time=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_threaded_comments']['edges'][j]['node']['created_at']
                    author_id=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_threaded_comments']['edges'][j]['node']['owner']['id']
                    author_name=data['data']['shortcode_media']['edge_media_to_parent_comment']['edges'][i]['node']['edge_threaded_comments']['edges'][j]['node']['owner']['username']
                    comment_id=items_c['comment_id']
                    post_id=items_c['post_id']
                    platform_id=items_c['platform_id']
                    items_r['reply_id']=reply_id
                    items_r['author_id']=author_id
                    items_r['author_name']=author_name
                    items_r['context']=context
                    items_r['post_id']=post_id
                    items_r['post_time']=self.change_time(post_time)
                    items_r['comment_id']=comment_id
                    items_r['platform_id']=platform_id
                    yield items_r
            else:
                #yield scrapy.Request(url_reply,callback=self.reply_parse)
                pass


            yield items_c

        comment_end_cursor=data['data']['shortcode_media']['edge_media_to_parent_comment']['page_info']['end_cursor']
        if comment_end_cursor != None and comment_end_cursor != "{\"bifilter_token\": \"KA8BAgAoAP______AAAAAAAA\"}":
            url_origin='https://www.instagram.com/graphql/query/?query_hash=bc3296d1ce80a24b1b6e40b1e72903f5&variables={"shortcode":"short_code","first":50}'.replace('short_code',response.meta['short_code'])
            url=url_origin.split('}')[0]+',"after":"'+comment_end_cursor+'"}'
            yield scrapy.Request(url,callback=self.comment_parse,meta={'post_id':response.meta['post_id'],
                                                                       'url_origin':url_origin,
                                                                      'short_code':response.meta['short_code']})

            
    def reply_parse(self,response):
        pass
    
        
