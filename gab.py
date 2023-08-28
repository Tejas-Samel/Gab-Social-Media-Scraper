"""Scrapes Gab Website for groups"""
import re
import sys
from concurrent.futures.thread import ThreadPoolExecutor
import logging
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import pymongo
import configparser


config = configparser.ConfigParser()
config.read('config.ini')

cluster = pymongo.MongoClient(config['Database']['mongodb_connection'])
db = cluster[config['Database']['database']]
collections = db[config['Database']['collection']]

logging.basicConfig(filename='gab_group.log',level=logging.DEBUG,
                    format='%(asctime)s : %(levelname)s : %(message)s')



class Gab:
    """This class is for scraping posts of groups"""

    def __init__(self):
        """A session is created with the site and logged in it"""
        self.regex = r"\<[^<>]*\>"
        self.session = HTMLSession()
        self.payload = {
            "authenticity_token": "",
            "user[email]": config['Account_Credentials']['email'],
            "user[password]": config['Account_Credentials']['password'],
            "button": ""
        }

        self.headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36'
                                      ' (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

        try:
            sign_response = self.session.get("https://gab.com/auth/sign_in",headers=self.headers)
            soup = BeautifulSoup(sign_response.content, "html.parser")

            #If CSRF token is not passed in headers the server responds with same page
            self.headers['x-csrf-token']=soup.find("meta",{"name":"csrf-token"}).get("content")

            self.payload["authenticity_token"]=soup.find("input", {"name": "authenticity_token"}).get("value")
            resp=self.session.post("https://gab.com/auth/sign_in", data=self.payload,headers=self.headers)

            sign_resp=BeautifulSoup(resp.text,"html.parser").find("strong")

            if sign_resp is not None:
                # if password or mail is invalid
                raise AttributeError("Invalid Credentials")


            print("SIGNED IN")

        except Exception as signin_except:
            logging.error(" INVALID SIGNIN CREDENTIALS ")
            self.exception_handler(group_id='SIGN_IN ERROR', exception=signin_except)
            print(signin_except)
            print("UNABLE TO SIGIN IN")

        self.account_details = None
        self.username = None
        self.id = None
        self.group_link = None
        self.username = None
        self.id_list = []
        self.keyword = ''

    def exception_handler(self, group_id='', profile_data='', page='', exception=''):
        """This method is for handling exception """

        exception_type, exception_object, exception_traceback = sys.exc_info()
        line_number = exception_traceback.tb_lineno

        print(f'Error in line_number: {str(line_number)} for group_id: {str(group_id)} '
              f'on page{str(page)}. And error is: {str(exception)}')

        with open('error.txt', 'a',encoding='utf-8') as error_file:
            logging.error(f'Error {str(exception)} line no. {str(line_number)}')
            error_file.write('Error' + '\n')
            error_file.write(f'Error/group_id {str(group_id)}')
            error_file.write(str(profile_data))
            error_file.write('line number' + str(line_number))
            error_file.write(str(exception))
            error_file.write("\n")

    def scrape_post_account(self):
        """This method scrapes the post changing max id"""
        try:
            max_Id = ""
            while True:
                max_Id = "&max_id=" + self.get_data_account(max_Id)
                print(max_Id)

                if max_Id == "&max_id=End":
                    break
        except Exception as scrape_post:
            self.exception_handler(exception=scrape_post)

    def profile_detail_account(self):
        """This method scrapes account details"""
        try:
            link = f"https://gab.com/api/v1/account_by_username/{self.username}"

            profile_json = self.session.get(link).json()
            self.account_details={
                'account_id':profile_json['id'],
                'account_username':profile_json['username'],
                'profile_created_timestamp':str(profile_json['created_at'])
                    .replace('T', ' ').split('.', 1)[0],
                'account_about':re.sub(self.regex,'',profile_json['note']),
                'followers_count':profile_json['followers_count'],
                'following_count':profile_json['following_count'],

            }
            self.id= profile_json['id']
            print(profile_json)
        except Exception as profile_except:
            self.exception_handler(exception=profile_except)

    def get_data_account(self,last_post):
        """This method scrapes the post of account"""
        try:
            response = self.session.get(f"https://gab.com/api/v1/accounts/{self.id}"
                                        f"/statuses?exclude_replies=true&max_id={last_post}")

            if len(response.json()) == 0:
                return "End"
            for post in response.json():

                if post["reblog"] is not None:
                    post = post["reblog"]

                dictionary = {
                "post_id":post['id'],
                "post_url":post["url"],
                "post_text": re.sub(self.regex, "", post["content"]),
                "post_likes":post["favourites_count"],
                "post_comments":post["replies_count"],
                "post_reposts":post['reblogs_count'],
                "account_detail":self.account_details
                }

                media_list=[]
                for media in post["media_attachments"]:
                    media_list.append({
                        "media_id":media['id'],
                        "media_url":media['url'],
                        "media_description":media['description']
                    })

                dictionary["media"] = media_list
                dictionary["post_date"] = str(post["created_at"]).replace("T",' ')

                print(dictionary)
                if collections.count_documents({'post_url':dictionary['post_url']})==0:
                    collections.insert_one(dictionary)
        except Exception as get_data_except:
            self.exception_handler(exception=get_data_except)
        return response.json()[len(response.json()) - 1]["id"]



    def group(self):
        """This method searches keyword and get group ids from all pages
         and append it to  self.id list"""
        page=0
        print("Getting Total Number Of Groups")

        while True:
            group_link = f'https://gab.com/api/v3/search?type=group&onlyVerified=false&q=' \
                         f'{self.keyword}&resolve=true&page={page}'
            page+=1
            try:
                response_groups = self.session.get(group_link,headers=self.headers).json()
            except ConnectionError as connecterror:
                print(connecterror)
                print("UNABLE TO SCRAPE NUMBER OF GROUPS")
                self.exception_handler(group_id=connecterror, exception=connecterror)
            except Exception as response_exception:
                print(response_exception)
                self.exception_handler(group_id=response_exception, exception=response_exception)

            # If the website returns nothing we have all the groups related to keyword
            if len(response_groups) == 0:
                break

            response_groups = response_groups['groups']
            for group in response_groups:
                self.id_list.append(group['id'])

        print("Total number of groups")
        print(len(self.id_list))

    def profile_detail_group(self, group_id):
        """This method gets the group details"""
        link = f"https://gab.com/api/v1/groups/{group_id}"

        try:
            profile_json = self.session.get(link,headers=self.headers).json()
        except ConnectionError as connecterror:
            print(connecterror)
            self.exception_handler(group_id=connecterror, exception=connecterror)

        profile_data = {
            'id': profile_json['id'],
            'username': profile_json['title'],
            'followers': profile_json['member_count'],
            'description': profile_json['description'],
            'profile_url': profile_json['url'],
            'created_at': str(profile_json['created_at']).replace('T', ' ').split('.', 1)[0],
        }
        try:
            self.get_data_group(group_id, profile_data)
        except Exception as exceptionerror:
            self.exception_handler(exception=exceptionerror)

    def get_data_group(self, group_id, profile_data):
        """This method gets all the posts and related information"""
        page=0

        while True:
            try:
                url = f'https://gab.com/api/v1/timelines/group/{group_id}?page={page}&sort_by=newest'
                response = self.session.get(url,headers=self.headers)

                page+=1
                posts_response = response.json()
                if len(posts_response) == 0:
                    break
                if not response.ok:
                    print("ERROR")
                    raise ConnectionError('No connection')
            except Exception as exception:
                self.exception_handler(group_id=group_id, profile_data=profile_data,
                                       page=page, exception=exception)

            try:
                for posts in posts_response:
                    post_data = {
                        'post_id': posts['id'],
                        'post_created': str(posts['created_at']).replace('T', ' ').split('.', 1)[0],
                        'post_url': posts['url'],
                        'likes': posts['favourites_count'],
                        'comments': posts['replies_count'],
                        'content': re.sub(self.regex, '', posts['content']),
                        'group': profile_data
                    }

                    if posts['reblogs_count']>0:
                        post_data['reblogged'] = posts['reblogs_count']

                    if posts['has_quote']:
                        posts_quote = posts['quote']
                        quote = {
                            'quote_id': str(posts_quote['id']),
                            'quote_created_at': str(posts_quote['created_at'])
                                .replace('T', ' ').split('.', 1)[0],
                            'quoted_url': posts_quote['url'],
                            'quotes_comment': posts_quote['replies_count'],
                            'reposted': posts_quote['reblogs_count'],
                            'quote_content': re.sub(self.regex, '', posts_quote['content']),
                        }
                        if len(posts_quote['media_attachments']) != 0:
                            media_attachments = posts_quote['media_attachments']
                            media_details = []
                            for media in media_attachments:
                                quote_m = {
                                    'media_id': str(media['id']),
                                    'media_type': media['type'],
                                    'media_url': media['url']
                                }
                                if media['description']:
                                    quote_m['description'] = media['description']
                                media_details.append(quote_m)
                            quote['quote_media_attachments'] = media_details
                        post_data['quote'] = quote

                    if len(posts['media_attachments']) != 0:
                        media_attachments = posts['media_attachments']
                        media_details = []
                        for media in media_attachments:
                            post_m = {
                                'media_id': media['id'],
                                'media_type': media['type'],
                                'media_url': media['url']
                            }
                            if media['description']:
                                post_m['description'] = media['description']
                            media_details.append(post_m)
                        post_data['media_attachments'] = media_details

                    posts = posts['account']
                    posted_by = {
                        'id': posts['id'],
                        'username': posts['username'],
                        'account_note': re.sub(self.regex, '', posts['note']),
                        'account_url': posts['url'],
                        'followers': posts['followers_count'],
                        'following': posts['following_count'],
                        'gabs': posts['statuses_count']
                    }
                    post_data['posted_by'] = posted_by

                    try:
                        if collections.count_documents({'post_url': post_data['post_url']}) == 0:
                            print(post_data)
                            collections.insert_one(post_data)
                    except Exception as mongoexcept:
                        with open('error.txt', 'a', encoding='utf-8') as error_file:
                            exception_type, exception_object, exception_traceback = sys.exc_info()
                            line_number = exception_traceback.tb_lineno

                            logging.critical(f"Database error {str(mongoexcept)}")

                            print('mongoexcept')
                            print(exception_type, exception_object, exception_traceback)
                            print(line_number)
                            error_file.write('MONGODB ERROR' + '\n')
                            error_file.write(str(mongoexcept) + '\n')

            except Exception as data_except:
                self.exception_handler(group_id=group_id,page=page,exception=data_except)


    def multithread(self):
        """This method maps the profile detail to id"""
        try:
            print(self.id_list)
            with ThreadPoolExecutor() as executor:
                executor.map(self.profile_detail_group, self.id_list)
        except Exception as multithread_except:
            print(multithread_except)
            logging.error(f'Error in multithread {str(multithread_except)}')


    def get_link_or_keyword(self):
        """This method should be called as  object
        is created to get link or keyword to be searched"""
        print("Enter")
        print("1.Keyword")
        print("2.Grouplink")
        print("3.Account Name")
        choice = int(input())

        if choice == 1:
            print("Enter Keyword")
            self.keyword = str(input()).strip()
            self.group() #We call this method to get all the groups
            self.multithread() # we map the group with the link
        elif choice == 2:
            print("Enter Group link")
            group_link = str(input()).split('/')[-1]
            self.profile_detail_group(group_link)
        elif choice == 3:
            print("Enter Username")
            self.username = str(input()).strip()
            self.profile_detail_account()
            self.scrape_post_account()
        else:
            print("Enter Valid choice")

if __name__ == '__main__':
    obj = Gab()
    obj.get_link_or_keyword()
