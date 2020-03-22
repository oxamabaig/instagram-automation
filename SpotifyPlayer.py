import datetime
import logging
import os
import pickle
from random import choice, randint
from pyvirtualdisplay import Display
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
import socket
import sys
import sqlite3
from sqlite3 import Error
from time import sleep
import xpath

class SpotifyPlayer:
    def __init__(self, **kwargs):
        logging.basicConfig(level=20,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%d.%m.%Y %H:%M')
        self.chrome_options = Options()
        if 'headless' in kwargs:
            self.headless = kwargs.get('headless')
        else:
            self.headless = False
        if 'proxy' in kwargs:
            #self.chrome_options.add_argument('--proxy-server=%s' % kwargs.get('proxy'))
            print(kwargs.get('proxy'))
        if 'mute_audio' in kwargs:
            if kwargs.get('mute_audio'):
                self.chrome_options.add_argument("--mute-audio")
        self.chrome_options.add_argument("--incognito")
        #self.chrome_options.add_argument("--headless")
        self.conn = self.connect()
        self.cur = self.conn.cursor()
    
    def idElementPresent(self, id):
        try:
            self.driver.find_element_by_id(id).click()
            return True
        except NoSuchElementException:
            return False

    def xPathElementPresent(self,xpath):
        try:
            self.driver.find_element_by_xpath(xpath).click()
            return True
        except NoSuchElementException:
            return False


    def check_connection(self):
        try:
            s = socket.create_connection((socket.gethostbyname("www.google.com"), 80), 2)
            s.close()
        except OSError:
            logging.critical("SpotifyPlayer is not connected to the internet.")
            sys.exit(0)

    def connect(self):
        try:
            conn = sqlite3.connect('assets/spotify_accounts.db')
            return conn
        except Error as e:
            logging.error(e)
            return None

    def fetch_credentials(self):
        self.cur.execute("SELECT username, password FROM accounts")
        rows = self.cur.fetchall()
        return rows
    
    def add_user(self, username, password):
        try:
            sql = '''INSERT INTO accounts (username, password) VALUES ('{}', '{}')'''.format(username, password)
            self.cur.execute(sql)
            self.conn.commit()
            logging.info("User "+username+" has been added to database.")
        except sqlite3.IntegrityError:
            logging.error("User "+username+" is already in database.")

    def delete_user(self, username):
        try:
            self.cur.execute('DELETE FROM accounts WHERE username = "{}"'.format(username))
            self.conn.commit()
            logging.info(self.database_status())
            return True
        except Exception as e:
            logging.error(e)
            return False

    def database_status(self):
        accounts = len(self.fetch_credentials())
        logging.info("We currently have "+str(accounts)+" accounts in database.")
        return accounts

    def check_response(self):
        if '504 Gateway Time-out' in self.driver.page_source:
            logging.error("Received error: 504 Gateway Time-out")
            logging.info("Refreshing...")
            self.driver.refresh()

    def login_again(self, username, password, retry=False):
        if not retry:
            logging.info("************** SPOTIFY PLAYER **************")
        self.check_connection()
        webdriver_path = os.path.dirname(os.path.realpath(__file__))+"/"+"assets/chromedriver"
        if self.headless:
            self.display = Display(size=(800,600))
            self.display.start()
        self.driver = webdriver.Chrome(webdriver_path, options=self.chrome_options)
        self.driver.maximize_window()
        self.driver.get("""https://accounts.spotify.com/en/login?continue=https:%2F%2Fopen.spotify.com%2Fbrowse%2Ffeatured""")
        self.check_response()
        sleep(3)
        try:
            while not self.idElementPresent("login-username"):
                continue
            self.driver.find_element_by_id("login-username").send_keys(username)
            while not self.idElementPresent("login-password"):
                continue
            self.driver.find_element_by_id("login-password").send_keys(password)
            while not self.idElementPresent("login-button"):
                continue
            sleep(7)
            return True
        except NoSuchElementException:
            logging.info("Could not find login page fields, refreshing...")
            return False


    def login(self, username, password, retry=False):
        if not retry:
            logging.info("************** SPOTIFY PLAYER **************")
        self.check_connection()
        webdriver_path = os.path.dirname(os.path.realpath(__file__))+"/"+"assets/chromedriver"
        if self.headless:
            self.display = Display(size=(800,600))
            self.display.start()
        self.driver = webdriver.Chrome(webdriver_path, options=self.chrome_options)
        self.driver.get("""https://accounts.spotify.com/en/login?continue=https:%2F%2Fopen.spotify.com%2Fbrowse%2Ffeatured""")
        self.check_response()
        sleep(3)
        try:
            cookies = pickle.load(open("assets/cookies/"+username+".pkl", "rb"))
            sleep(1)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                self.driver.add_cookie(cookie)
        except FileNotFoundError:
            try:
                self.driver.find_element_by_id("login-username").send_keys(username)
                sleep(1)
                self.driver.find_element_by_id("login-password").send_keys(password)
                sleep(1)
                self.driver.find_element_by_id("login-button").click()
                sleep(3)
            except NoSuchElementException:
                print("Could not find login page fields, refreshing...")
                self.driver.refresh()
                sleep(3)
                self.driver.find_element_by_id("login-username").send_keys(username)
                sleep(1)
                self.driver.find_element_by_id("login-password").send_keys(password)
                sleep(1)
                self.driver.find_element_by_id("login-button").click()
                sleep(3)
            try:
                self.driver.find_element_by_class_name('alert-warning')
                logging.error("Incorrect username or password for "+username+".")
                self.stop()
                return False
            except NoSuchElementException:
                pickle.dump(self.driver.get_cookies(), open("assets/cookies/"+username+".pkl","wb"))
        try:
            self.driver.get("https://open.spotify.com/")
            self.check_response()
            sleep(4)
            account = self.driver.find_element_by_css_selector(xpath.current_username).get_attribute("innerHTML")
            logging.info("Logged in as "+account+".")
            return True
        except NoSuchElementException:
            os.remove("assets/cookies/"+username+".pkl")
            logging.info("Cookie has expired, creating new one...")
            self.driver.close()
            return self.login(username, password, retry=True)

    def play_next(self, delay):
        self.check_response()
        while not self.xPathElementPresent(xpath.play_next):
            continue
        status = self.status()
        if status:
            print("Currently playing "+status+".")
            logging.info("Currently playing "+status+".")
        if delay is not None:
            while True:
                clock = self.playing_time()
                seconds = int(clock[0])*60+int(clock[1])
                if seconds >= delay:
                    break
                sleep(1)
            print("Played the track for "+str(seconds)+" seconds.")    
            logging.info("Played the track for "+str(seconds)+" seconds.")	
	
    def play(self, track, delay):
        self.driver.get(track)
        self.check_response()
        sleep(5)
        while not self.xPathElementPresent(xpath.play_button):
            continue
        status = self.status()
        if status:
            print("Currently playing "+status+".")
            logging.info("Currently playing "+status+".")
        if delay is not None:
            while True:
                clock = self.playing_time()
                seconds = int(clock[0])*60+int(clock[1])
                if seconds >= delay:
                    break
                sleep(1)
            print("Played the track for "+str(seconds)+" seconds.")    
            logging.info("Played the track for "+str(seconds)+" seconds.")


    def play_album(self, album, delay):
        self.driver.get(album)
        self.check_response()
        sleep(5)
        while not self.xPathElementPresent(xpath.play_album):
            continue
        status = self.status()
        if status:
            print("Currently playing "+status+".")
            logging.info("Currently playing "+status+".")
        if delay is not None:
            while True:
                clock = self.playing_time()
                seconds = int(clock[0])*60+int(clock[1])
                if seconds >= delay:
                    break
                sleep(1)
            print("Played the track for "+str(seconds)+" seconds.")    
            logging.info("Played the track for "+str(seconds)+" seconds.")

    def play_artist(self, album, delay):
        self.driver.get(album)
        self.check_response()
        sleep(5)
        while not self.xPathElementPresent(xpath.play_artist):
            continue
        status = self.status()
        if status:
            print("Currently playing "+status+".")
            logging.info("Currently playing "+status+".")
        if delay is not None:
            while True:
                clock = self.playing_time()
                seconds = int(clock[0])*60+int(clock[1])
                if seconds >= delay:
                    break
                sleep(1)
            print("Played the track for "+str(seconds)+" seconds.")    
            logging.info("Played the track for "+str(seconds)+" seconds.")        
			
	
    def set_repeat(self):
        try:
            self.driver.find_element_by_css_selector(xpath.repeat_button).click()
            logging.info("Player has been set to repeat.")
        except NoSuchElementException:
            logging.info("Player is already in repetitive mode.")
    
    def status(self, retry=False):
        sleep(3)
        try:
            status = self.driver.find_element_by_css_selector(xpath.current_track).get_attribute("innerHTML")
            return status
        except NoSuchElementException:
            if retry:
                logging.error("Could not fetch current track name.")
                return False
            return self.status(retry=True)
        
    def play_mode(self):
        sleep(3)
        try:
            self.driver.find_element_by_css_selector(xpath.is_playing)
            return True
        except NoSuchElementException:
            return False

    def start_playing(self):
        logging.info("Session is starting playing again...")
        self.driver.find_element_by_css_selector(xpath.start_playing).click()       

    def playing_time(self):
        time = self.driver.find_element_by_css_selector(xpath.playing_time).get_attribute("innerHTML").split(':')
        return time

    def skip(self, delay=False):
        if delay:
            sleep(delay)
        self.driver.find_element_by_xpath(xpath.skip_button).click()
        logging.info("Skipping the track...")
    
    def like(self, track=None):
        if track is not None:
            self.driver.get(track)
            self.check_response()
            sleep(3)
        self.driver.find_element_by_xpath(xpath.like_button).click()
        logging.info("Track liked!")

    def follow(self, artist):
        if artist is not None:
            self.driver.get(artist)
            self.check_response()
            sleep(3)

        if (self.driver.find_element_by_xpath(xpath.follow).text == 'FOLLOW'):
            self.driver.find_element_by_xpath(xpath.follow).click()
        logging.info("Artist followed!")    

    def stop(self):
        logging.info("Finished handling all tasks.")
        self.driver.close()
        if self.headless:
            self.display.stop()
