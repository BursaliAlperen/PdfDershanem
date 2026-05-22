pkg update -y && pkg upgrade -y
pkg install clang rust binutils make libffi openssl python -y
pip install --upgrade pip wheel setuptools
pip install python-dotenv instagrapi

cat << 'EOF' > ig_bot.py
import os
import time
import random
from instagrapi import Client
from dotenv import load_dotenv

# --- PRO UI RENKLERİ ---
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def print_log(msg, color=RESET):
    print(f"{color}[{time.strftime('%H:%M:%S')}] {msg}{RESET}")

def print_banner():
    print(f"{CYAN}╔════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║     PREMIUM INSTAGRAM OTO-BOT V3.0         ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════════╝{RESET}")

def main():
    print_banner()
    
    # 1. KİMLİK DOĞRULAMA (.env)
    if not os.path.exists('.env'):
        print_log("İlk Kurulum: Lütfen Instagram bilgilerinizi girin.", YELLOW)
        username = input(f"{CYAN}Instagram Kullanıcı Adı: {RESET}").strip()
        password = input(f"{CYAN}Instagram Şifresi: {RESET}").strip()
        with open('.env', 'w') as f:
            f.write(f"IG_USERNAME={username}\n")
            f.write(f"IG_PASSWORD={password}\n")
        print_log("Bilgiler .env dosyasına güvenle kaydedildi!\n", GREEN)
    
    load_dotenv()
    USERNAME = os.getenv('IG_USERNAME')
    PASSWORD = os.getenv('IG_PASSWORD')
    
    cl = Client()
    print_log("Instagram sunucularına bağlanılıyor...", YELLOW)
    try:
        cl.login(USERNAME, PASSWORD)
        print_log("Giriş Başarılı!", GREEN)
    except Exception as e:
        print_log(f"Giriş Hatası: {e}", RED)
        return

    # 2. GÖREV AYARLARI
    print(f"\n{MAGENTA}--- GÖREV YAPILANDIRMASI ---{RESET}")
    target_username = input(f"{CYAN}Hedef Kullanıcı Adı (Takipçileri kopyalanacak): {RESET}").strip()
    
    try:
        follow_limit = int(input(f"{CYAN}Günlük Takip Limiti (Örn: 50): {RESET}"))
        unfollow_limit = int(input(f"{CYAN}Günlük Takipten Çıkma Limiti (Örn: 100): {RESET}"))
    except ValueError:
        print_log("HATA: Limitler için sadece sayı girmelisiniz! Program durduruluyor.", RED)
        return

    wl_input = input(f"{CYAN}Beyaz Liste (Çıkarılmayacak kişiler, virgülle ayırın, yoksa boş bırakın): {RESET}")
    whitelist = [u.strip() for u in wl_input.split(',')] if wl_input else []
    whitelist.append(USERNAME)

    my_user_id = cl.user_id

    # 3. AŞAMA: HEDEF KİTLEYİ TAKİP ETME
    if follow_limit > 0 and target_username:
        print(f"\n{MAGENTA}--- 1. AŞAMA: TAKİP İŞLEMİ BAŞLIYOR ---{RESET}")
        try:
            target_id = cl.user_id_from_username(target_username)
            print_log(f"@{target_username} adlı kullanıcının takipçileri analiz ediliyor...", YELLOW)
            target_followers = cl.user_followers(target_id, amount=follow_limit + 15)
            my_following_now = cl.user_following(my_user_id)
            
            followed_count = 0
            for uid, user_info in target_followers.items():
                if followed_count >= follow_limit:
                    print_log("Takip etme görev limitine ulaşıldı.", YELLOW)
                    break
                    
                if uid in my_following_now:
                    continue # Zaten takip ediliyorsa atla

                try:
                    cl.user_follow(uid)
                    followed_count += 1
                    print_log(f"[+] TAKİP EDİLDİ: @{user_info.username} ({followed_count}/{follow_limit})", GREEN)
                    
                    delay = random.uniform(30, 60)
                    print_log(f"[*] Anti-Ban: {delay:.1f} saniye bekleniyor...", YELLOW)
                    time.sleep(delay)
                except Exception as e:
                    print_log(f"[-] HATA: @{user_info.username} takip edilemedi ({e})", RED)
                    time.sleep(15)
        except Exception as e:
            print_log(f"Hedef kitle işlemi başarısız: {e}", RED)

    # 4. AŞAMA: GERİ TAKİP ETMEYENLERİ ÇIKARMA
    if unfollow_limit > 0:
        print(f"\n{MAGENTA}--- 2. AŞAMA: TEMİZLİK (GERİ TAKİP ETMEYENLER) ---{RESET}")
        print_log("Hesabınızın güncel takipçi/takip edilen verileri senkronize ediliyor...", YELLOW)
        
        try:
            my_followers = cl.user_followers(my_user_id)
            my_following = cl.user_following(my_user_id)
            
            unfollowed_count = 0
            for uid, user_info in my_following.items():
                if unfollowed_count >= unfollow_limit:
                    print_log("Takipten çıkma görev limitine ulaşıldı.", YELLOW)
                    break
                
                # Eğer beni takip etmiyorsa VE beyaz listede değilse
                if uid not in my_followers:
                    if user_info.username in whitelist:
                        print_log(f"[*] KORUMALI: @{user_info.username} beyaz listede, atlanıyor.", CYAN)
                        continue

                    try:
                        cl.user_unfollow(uid)
                        unfollowed_count += 1
                        print_log(f"[-] ÇIKARILDI: @{user_info.username} ({unfollowed_count}/{unfollow_limit})", RED)
                        
                        delay = random.uniform(30, 60)
                        print_log(f"[*] Anti-Ban: {delay:.1f} saniye bekleniyor...", YELLOW)
                        time.sleep(delay)
                    except Exception as e:
                        print_log(f"[-] HATA: @{user_info.username} çıkarılamadı ({e})", RED)
                        time.sleep(15)
        except Exception as e:
            print_log(f"Temizlik işlemi sırasında hata: {e}", RED)

    print(f"\n{CYAN}╚════════════════════════════════════════════╝{RESET}")
    print_log("TÜM GÖREVLER BAŞARIYLA TAMAMLANDI!", GREEN)

if __name__ == "__main__":
    main()
EOF

python ig_bot.py
