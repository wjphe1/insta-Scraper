import os
from os.path import join
import platform
import json
import hashlib
import hmac
import time
import six.moves.urllib as urllib
from tqdm import tqdm
from requestium import Session, Keys 
import logging

DEVICE_SETTINTS = {
    'manufacturer': 'samsung',
    'model': 'herolte',
    'device': 'SM-G960F',
    'android_version': 26,
    'android_release': '8.0'
}
#41.0.0.13.92


class API:
    def __init__(self, path):
        self.last_json = ""
        self.last_response = None
        self.IG_SIG_KEY = '4f8732eb9ba7d1c8e8897a75d6474d4eb3f5279137431b2aafb71fafe2abe178'
        self.SIG_KEY_VERSION = '4'
        self.USER_AGENT = 'Instagram 10.26.0 Android ({android_version}/{android_release}; 640dpi; 1440x2560; {manufacturer}; {device}; {model}; samsungexynos8890; en_US)'.format(
    **DEVICE_SETTINTS)
        self.s = Session(webdriver_path= path, browser='chrome',default_timeout=15)
        self.logger = logging.getLogger('[instatesi_{}]'.format(id(self)))
        self.privateUsers = {}
        self.users = {}
        fh = logging.FileHandler(filename='instatesi.log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self.logger.setLevel(logging.DEBUG)
        self.lastUserHandled = None
    
    def saveScrapedFollowers(self):
        import json
        self.logger.info("Except for the selected Followers...")
        if not os.path.exists(os.getcwd()+"/ScrapedFollowers/"+self.lastUserHandled +".txt"):
            with open(os.getcwd()+"/ScrapedFollowers/" + self.lastUserHandled + ".txt", "w") as f:
                """ f.write("Scraped following from " + self.lastUserHandled +"\n")
                f.write("-------Non private users-------\n")
                f.write(json.dumps(self.users[''], indent=2))
                f.write("\n-------Private users-------\n")
                f.write(json.dumps(self.privateUsers, indent=2)) """
                for k, v in self.users.items():
                    f.write(k + ',\n')
            self.logger.info("Following successfully saved!")
            self.users = dict()
            self.privateUsers = dict()

        else:
            self.logger.warning("Warning! The user is already present in the database. Overwrite?")
            #Define some logic for file overwriting
    
    def saveScrapedFollowing(self):
        import json
        self.logger.info("Except for the Following's Following...")
        if not os.path.exists(os.getcwd()+"/ScrapedFollowing/"+self.lastUserHandled +".txt"):
            with open(os.getcwd()+"/ScrapedFollowing/" + self.lastUserHandled + ".txt", "w") as f:
                f.write("Scraped following from " + self.lastUserHandled +"\n")
                f.write("-------Non private users-------\n")
                f.write(json.dumps(self.users, indent=2))
                f.write("\n-------Private users-------\n")
                f.write(json.dumps(self.privateUsers, indent=2))
            self.logger.info("Following successfully saved!")
            self.users = dict()
            self.privateUsers = dict()
        else:
            self.logger.warning("Warning! The user is already present in the database. Overwrite?")
            #Define some logic for file overwriting
    
    def getUserFollowers(self,userID, rank_token, selection="followers"):
        self.logger.info("User ID follower scraping started " +str(userID))
        followers = self.getTotalFollowers(userID, rank_token, fromInput= selection)
        return [str(item['username']) for item in followers][::-1] if followers else []
    
    def __getUsernameInfo(self,usernameId):
        return self.__send_request('users/' + str(usernameId) + '/info/')
    
    def __send_request_for_user_followers(self,user_id, rank_token, max_id='', selection="followers"):
        url = 'friendships/{user_id}/followers/?rank_token={rank_token}' if selection=="followers" else 'friendships/{user_id}/following/?max_id={max_id}&ig_sig_key_version={sig_key}&rank_token={rank_token}'
        url = url.format(user_id=user_id, rank_token=rank_token) if selection=="followers" else url.format(
            user_id=user_id,
            max_id=max_id,
            sig_key=self.SIG_KEY_VERSION,
            
            rank_token=rank_token)
        if max_id:
            url += '&max_id={max_id}'.format(max_id=max_id)
        return self.__send_request(url)

    def searchUsername(self,username):
        url = 'users/{username}/usernameinfo/'.format(username=username)
        self.logger.info("Looking for user information " + username)
        return self.__send_request(url)
    

    def getUsernameFromID(self, user_id):
        url = 'users/{user_id}/info/'.format(user_id=user_id)
        self.__send_request(url)
        self.logger.info("Return the requested username, or " + str(self.last_json['user']['username']))
        return self.last_json['user']['username']

    def __generateSignature(self,data, IG_SIG_KEY, SIG_KEY_VERSION):
        body = hmac.new(IG_SIG_KEY.encode('utf-8'), data.encode('utf-8'),hashlib.sha256).hexdigest() + '.' + urllib.parse.quote(data)
        signature = 'ig_sig_key_version={sig_key}&signed_body={body}'
        return signature.format(sig_key=SIG_KEY_VERSION, body=body)
    
    def castUsernameToUserID(self,usernameToLook):
        self.lastUserHandled = usernameToLook
        userID = ""
        self.searchUsername(usernameToLook)
        if "user" in self.last_json:
            userID = str(self.last_json["user"]["pk"])
        self.logger.info("The username " + usernameToLook + " corresponds to the ID " + userID)
        return userID
    
    def seeStories(self):
        self.__send_request("feed/reels_tray/")
        return self.last_json

    def getTotalFollowers(self,usernameId, rank_token, fromInput = "followers"):
        sleep_track = 0
        followers = []
        next_max_id = ''
        self.__getUsernameInfo(usernameId)
        if "user" in self.last_json:
            total_followers = self.last_json["user"]['follower_count'] if fromInput =="followers" else self.last_json["user"]['following_count']
            if total_followers > 200000:
                self.logger.warning("There are over 200,000 followers. It may take a while.")
        else:
            return False
        with tqdm(total=total_followers, desc="Retrieving followers", leave=False) as pbar:
            while True:
                self.__send_request_for_user_followers(usernameId, rank_token, next_max_id, selection=fromInput)
                temp = self.last_json
                try:
                    pbar.update(len(temp["users"]))
                    for item in temp["users"]:
                        if item['is_private']:
                            self.privateUsers[item['username']] = {
                                'ID' : item['pk'],
                                'user_handle': item['username'],
                                'is_verified': item['is_verified'],
                                'is_private': item['is_private'],
                                'profile pic': item['profile_pic_url'],
                                'Full Name': item['full_name']
                            }
                        else:
                            self.users[item['username']] = {
                                'ID' : item['pk'],
                                'user_handle': item['username'],
                                'is_private': item['is_private'],
                                'is_verified': item['is_verified'],
                                'profile pic': item['profile_pic_url'],
                                'Full Name': item['full_name']
                            }
                        followers.append(item)
                        sleep_track += 1
                        if sleep_track >= 20000:
                            import random
                            sleep_time = random.randint(120,180)
                            self.logger.info("Waiting for " + str(float(sleep_time / 60)) + " due to excessive demands.")
                            time.sleep(sleep_time)
                            sleep_track = 0
                    if len(temp["users"]) == 0 or len(followers) >= total_followers:
                        self.logger.info("Returning account followers in the scraping phase, ie " +str(len(followers[:total_followers])))
                        return followers[:total_followers]
                except Exception:
                    self.logger.error("Returning account followers in the scraping phase, ie " +str(len(followers[:total_followers])))
                    return followers[:total_followers]
                if temp["big_list"] is False:
                    self.logger.info("Returning account followers in the scraping phase, ie " +str(len(followers[:total_followers])))
                    return followers[:total_followers]
                next_max_id = temp["next_max_id"]

    def __send_request(self,endpoint, post=None, login=False, with_signature=True):
        self.s.headers.update({
            'Connection': 'close',
            'Accept': '*/*',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie2': '$Version=1',
            'Accept-Language': 'en-US',
            'User-Agent': self.USER_AGENT
        })
        try:
            if post is not None:  # POST
                if with_signature:
                    post = self.__generateSignature(post, self.IG_SIG_KEY, self.SIG_KEY_VERSION)
                response = self.s.post('https://i.instagram.com/api/v1/' + endpoint, data=post)
            else:  # GET
                response = self.s.get('https://i.instagram.com/api/v1/' + endpoint)
        except Exception as e:
            self.logger.error("Exception due to endpoint " + endpoint)
            self.logger.error(e)
            return False
        if response.status_code == 200:
            self.logger.info("The request to the endpoint " + endpoint + " has been successful")
            self.last_response = response
            self.last_json = json.loads(response.text)
            return True
        else:
            return False