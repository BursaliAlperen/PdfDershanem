#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Instagram Takip Botu - Termux için optimize edildi

import os
import sys
import time
import random
import json
import logging
from pathlib import Path

def install_requirements():
    """Eksik kütüphaneleri otomatik yükle"""
    try:
        import instagrapi
        from dotenv import load_dotenv
    except ImportError:
        print("[!] Gerekli kütüphaneler yükleniyor...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "instagrapi==1.6.4", "python-dotenv", "--no-build-isolation"])
        print("[✓] Kütüphaneler başarıyla yüklendi!")
        os.execv(sys.executable, ['python3'] + sys.argv)

install_requirements()

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, UserNotFound
from dotenv import load_dotenv

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

class InstagramBot:
    def __init__(self):
        self.client = Client()
        self.following_list = {}
        self.today_followed = 0
        self.today_unfollowed = 0
        self.session_file = "session.json"
    
    def load_environment(self):
        env_path = Path(".env")
        if not env_path.exists():
            self.create_env_file()
            print(f"{Colors.GREEN}[✓] .env oluşturuldu. Bilgilerini gir ve tekrar başlat.{Colors.END}")
            sys.exit(0)
        
        load_dotenv()
        self.username = os.getenv("INSTAGRAM_USERNAME")
        self.password = os.getenv("INSTAGRAM_PASSWORD")
        self.target_username = os.getenv("TARGET_USERNAME")
        self.daily_follow_limit = int(os.getenv("DAILY_FOLLOW_LIMIT", "50"))
        self.daily_unfollow_limit = int(os.getenv("DAILY_UNFOLLOW_LIMIT", "100"))
        self.whitelist = [u.strip() for u in os.getenv("WHITELIST_USERS", "").split(",") if u.strip()]
        
        if not all([self.username, self.password, self.target_username]):
            print(f"{Colors.RED}[HATA] .env dosyasını doldur!{Colors.END}")
            sys.exit(1)
    
    def create_env_file(self):
        with open(".env", "w") as f:
            f.write("""INSTAGRAM_USERNAME=kullanici_adiniz
INSTAGRAM_PASSWORD=sifreniz
TARGET_USERNAME=hedef_kullanici
DAILY_FOLLOW_LIMIT=50
DAILY_UNFOLLOW_LIMIT=100
WHITELIST_USERS=
""")
    
    def random_delay(self, min_sec=30, max_sec=60):
        delay = random.uniform(min_sec, max_sec)
        print(f"{Colors.YELLOW}[⏳] {delay:.1f} saniye bekleniyor...{Colors.END}")
        time.sleep(delay)
    
    def save_session(self):
        try:
            with open(self.session_file, "w") as f:
                json.dump(self.client.get_settings(), f)
        except:
            pass
    
    def load_session(self):
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, "r") as f:
                    self.client.set_settings(json.load(f))
                return True
        except:
            pass
        return False
    
    def login(self):
        print(f"{Colors.BLUE}[*] Giriş yapılıyor...{Colors.END}")
        
        if self.load_session():
            try:
                self.client.user_id
                print(f"{Colors.GREEN}[✓] Otomatik giriş: @{self.client.username}{Colors.END}")
                return True
            except LoginRequired:
                pass
        
        try:
            self.client.login(self.username, self.password)
            print(f"{Colors.GREEN}[✓] Giriş başarılı: @{self.username}{Colors.END}")
            self.save_session()
            return True
        except Exception as e:
            print(f"{Colors.RED}[✗] Giriş hatası: {e}{Colors.END}")
            return False
    
    def get_user_following(self):
        try:
            self.following_list = self.client.user_following(self.client.user_id)
            print(f"{Colors.GREEN}[✓] {len(self.following_list)} takip edilen{Colors.END}")
            return self.following_list
        except Exception as e:
            print(f"{Colors.RED}[✗] Hata: {e}{Colors.END}")
            return {}
    
    def follow_users(self):
        if self.today_followed >= self.daily_follow_limit:
            return
        
        remaining = self.daily_follow_limit - self.today_followed
        try:
            target_id = self.client.user_id_from_username(self.target_username)
            followers = self.client.user_followers(target_id, amount=min(remaining, 100))
        except UserNotFound:
            print(f"{Colors.RED}[✗] @{self.target_username} bulunamadı!{Colors.END}")
            return
        
        for user_id, user in followers.items():
            if self.today_followed >= self.daily_follow_limit:
                break
            if user_id in self.following_list:
                continue
            
            try:
                self.client.user_follow(user_id)
                self.today_followed += 1
                print(f"{Colors.GREEN}[✓] @{user.username} takip edildi ({self.today_followed}/{self.daily_follow_limit}){Colors.END}")
                self.following_list[user_id] = user
                self.random_delay(30, 60)
            except Exception as e:
                print(f"{Colors.RED}[✗] @{user.username}: {e}{Colors.END}")
                self.random_delay(20, 30)
    
    def unfollow_users(self):
        if self.today_unfollowed >= self.daily_unfollow_limit or not self.following_list:
            return
        
        for user_id, user in list(self.following_list.items()):
            if self.today_unfollowed >= self.daily_unfollow_limit:
                break
            if user.username in self.whitelist:
                continue
            
            try:
                friendship = self.client.user_friendship(user_id)
                if not friendship.followed_by:
                    self.client.user_unfollow(user_id)
                    self.today_unfollowed += 1
                    print(f"{Colors.GREEN}[✓] @{user.username} çıkarıldı ({self.today_unfollowed}/{self.daily_unfollow_limit}){Colors.END}")
                    del self.following_list[user_id]
                    self.random_delay(30, 60)
            except Exception as e:
                print(f"{Colors.RED}[✗] @{user.username}: {e}{Colors.END}")
    
    def show_stats(self):
        print(f"\n{Colors.BOLD}{'='*50}{Colors.END}")
        print(f"{Colors.HEADER}📊 @{self.username} | Takip: {self.today_followed}/{self.daily_follow_limit} | Çıkar: {self.today_unfollowed}/{self.daily_unfollow_limit}{Colors.END}")
        print(f"{Colors.BOLD}{'='*50}{Colors.END}\n")
    
    def run(self):
        print(f"{Colors.BLUE}╔════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BLUE}║   Instagram Takip Botu v2.0   ║{Colors.END}")
        print(f"{Colors.BLUE}╚════════════════════════════════╝{Colors.END}")
        
        self.load_environment()
        if not self.login():
            sys.exit(1)
        
        self.get_user_following()
        
        try:
            while True:
                self.follow_users()
                self.random_delay(60, 120)
                self.unfollow_users()
                self.show_stats()
                
                if self.today_followed >= self.daily_follow_limit and self.today_unfollowed >= self.daily_unfollow_limit:
                    print(f"{Colors.YELLOW}[!] Limitler doldu, 1 saat bekleniyor...{Colors.END}")
                    time.sleep(3600)
                    self.today_followed = 0
                    self.today_unfollowed = 0
                else:
                    wait = random.uniform(300, 900)
                    print(f"{Colors.YELLOW}[*] {wait/60:.1f} dakika bekleniyor...{Colors.END}")
                    time.sleep(wait)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[!] Bot durduruldu{Colors.END}")
            self.save_session()

if __name__ == "__main__":
    InstagramBot().run()
