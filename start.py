import argparse
import getpass
import json
import keyring
import os
import requests
from display import display_to_terminal

SERVICE_NAME = 'instagram-terminal-news-feed'

def get_credential():
    _username  = keyring.get_password(SERVICE_NAME, 'username')
    if not _username:
        return

    return {
        'username': _username,
        'password': keyring.get_password(SERVICE_NAME, 'password')
    }

def fetch_news_feed(session):
    res = session.get("https://i.instagram.com/api/v1/feed/timeline/", headers={
        'user-agent':"Instagram 10.3.2 (iPhone7,2; iPhone OS 9_3_3; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/420+",
        'cookie':'sessionid={0};'.format(session.cookies['sessionid'])
    })
    if res.status_code != 200:
        print("ERROR: got "+str(res.status_code)+" when fetching!")
        exit()
    res = json.loads(res.text)
    posts_info = {}
    for item in res['items']:
        if 'user' not in item: continue
        username = item['user']['username']
        key = username + '_' +  str(item['taken_at']) + '.jpg'
        try:
            posts_info[key] = {
                'username': username,
                'caption': item['caption']['text'] if item['caption'] else "",
                'image_url': item['image_versions2']['candidates'][0]['url'],
                'likes': str(item['like_count']) if item['like_count'] else '0',
                'site_url': 'https://www.instagram.com/p/' + item['code'] + '/?taken-by=' + username
            }
        except KeyError:
            pass
    return posts_info

def save_image(posts_info, session):
    if not os.path.exists('images'):
        os.makedirs('images')

    for key in posts_info.keys():
        res = session.get(posts_info[key]['image_url'])
        with open('images/' + key, 'wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

def remove_image_dir():
    if not os.path.isdir("./images"):
        return
    file_list = os.listdir('./images/')
    for filename in file_list:
        os.remove('./images/' + filename)

def reset_credentials():
    keyring.delete_password(SERVICE_NAME, 'username')
    keyring.delete_password(SERVICE_NAME, 'password')

def save_credentials(credential, permission):
    if not permission:
        return

    keyring.set_password(SERVICE_NAME, 'username', credential['username'])
    keyring.set_password(SERVICE_NAME, 'password', credential['password'])

def get_login_session(credential):
    session = requests.Session()
    session.headers.update({'Referer': 'https://www.instagram.com/'})
    req = session.get('https://www.instagram.com/')
    session.headers.update({'X-CSRFToken': req.cookies['csrftoken']})
    res = session.post('https://www.instagram.com/accounts/login/ajax/', data=credential, allow_redirects=True)
    login_response = json.loads(res.text);
    if 'two_factor_required' in login_response and login_response['two_factor_required']:
        identifier = login_response['two_factor_info']['two_factor_identifier']
        username = credential['username']
        verification_code = input('2FA Verification Code: ')
        verification_data = {'username': username, 'verificationCode': verification_code, 'identifier': identifier}
        two_factor_request = session.post('https://www.instagram.com/accounts/login/ajax/two_factor/', data=verification_data, allow_redirects=True)
        two_factor_response = json.loads(two_factor_request.text)
        if two_factor_response['authenticated']:
            return session, two_factor_response
        else:
            return None, two_factor_text
    return session, login_response

def login(credential):
    if credential:
        session, _ = get_login_session(credential)
        return session

    user, pwd = "", ""
    while True:
        user = input('Username: ')
        pwd = getpass.getpass(prompt='Password: ')
        session, res = get_login_session({"username": user, "password": pwd})
        if res['authenticated']:
            break
        if not res['authenticated']:
            print("Bad username or password")
        if res['status'] == 'fail':
            print(res['message'])
            exit()

    permission = input("save credentials(y/N)?: ")
    credential = {"username": user, "password": pwd}
    save_credentials(credential, permission == 'y')
    return session

def main():
    credential = {}

    parser     = argparse.ArgumentParser()
    parser.add_argument('--color', action='store_true', help='display image with color')
    parser.add_argument('--reset-credentials', default=False, action='store_true',
            help='reset stored credentials')
    
    args   = parser.parse_args()

    if args.reset_credentials:
        reset_credentials()
    else:
        credential = get_credential()

    session = login(credential)
    remove_image_dir()
    posts_info = fetch_news_feed(session)
    save_image(posts_info, session)
    display_to_terminal(posts_info, args.color)

if __name__ == '__main__':
    main()
