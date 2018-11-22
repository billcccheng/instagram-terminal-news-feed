import sys
import argparse
import getpass
import json
import os
import requests
from display import display_to_terminal
import pycookiecheat as pcc

def get_credential():
    if not os.path.exists('credential.json'):
        return
    try:
        with open('credential.json') as json_data:
            credential = json.load(json_data)
            return credential
    except FileNotFoundError:
        print("credential.json file not found in current directory. Exiting.")
        exit()

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

    for key in posts_info:
        res = session.get(posts_info[key]['image_url'])
        with open('images/' + key, 'wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

def remove_images():
    if not os.path.isdir("./images"):
        return
    file_list = os.listdir('./images/')
    for filename in file_list:
        os.remove('./images/' + filename)

def save_credentials(credential, permission):
    if not permission:
        return
    with open('credential.json', 'w') as _file:
        json.dump(credential, _file)

def get_login_session(credential):
    session = requests.Session()
    session.headers.update({'Referer': 'https://www.instagram.com/'})
    req = session.get('https://www.instagram.com/')
    session.headers.update({'X-CSRFToken': req.cookies['csrftoken']})
    login_response = session.post('https://www.instagram.com/accounts/login/ajax/', data=credential, allow_redirects=True).json()
    if 'two_factor_required' in login_response and login_response['two_factor_required']:
        identifier = login_response['two_factor_info']['two_factor_identifier']
        username = credential['username']
        verification_code = input('2FA Verification Code: ')
        verification_data = {'username': username, 'verificationCode': verification_code, 'identifier': identifier}
        two_factor_response = session.post('https://www.instagram.com/accounts/login/ajax/two_factor/', data=verification_data, allow_redirects=True).json()
        if two_factor_response['authenticated']:
            return session, two_factor_response
        else:
            return None, two_factor_response
    return session, login_response

def add_instagram_cookies(session, browser):
    added = False
    cookies = list()

    if (browser.lower() == 'chrome'):
        cookies = pcc.chrome_cookies('https://instagram.com')
        for key,value in cookies.items():
            session.cookies.set(key,value)

    if (len(cookies) > 0):
        added = True

    return (session, added)

def reuse_browser_session(session):
    browser = input('What browser? ')
    session, success = add_instagram_cookies(session, browser)
    if not success:
        print('Unsupported brower: browser not in [chrome]')
        return (None, False)
    return (session, True)

def login(credential):
    if credential:
        session, _ = get_login_session(credential)
        return session

    user, pwd = "", ""
    while True:
        user = input('Username: ')
        pwd = getpass.getpass(prompt='Password: ')
        session, res = get_login_session({"username": user, "password": pwd})
        if 'checkpoint_required' in res['message']:
            print(''.join([
                'You have a check point URL to complete:\n',
                'https://instagram.com', res['checkpoint_url']
            ]))
            input('Resolve the challenge in [chrome] then, hit enter..')
            print('We are going to import your instagram browser cookies..')
            session, success = reuse_browser_session(session)
            if not success:
                sys.exit(1)
            break
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', action='store_true', help='Display image with color')
    display_color = parser.parse_args().color
    credential = get_credential()
    reuse_sess = input('Would you like to use an existing browser session? (y,n): ')
    if (reuse_sess.lower() == 'y'):
        session,success = reuse_browser_session(requests.session())
        if not success:
            print('There is something wrong with your browser session')
            sys.exit(1)
    else:
        session = login(credential)
    remove_images()
    posts_info = fetch_news_feed(session)
    save_image(posts_info, session)
    display_to_terminal(posts_info, display_color)

if __name__ == '__main__':
    main()
