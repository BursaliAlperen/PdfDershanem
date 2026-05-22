import json
import time
import os
from datetime import datetime, timedelta
from getpass import getpass
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

# ----- AYARLAR -----
TARGET_USERNAME = "ssekwr"        # takipçileri takip edilecek hesap
FOLLOW_DELAY = 30                 # her takip arası saniye
UNFOLLOW_AFTER_HOURS = 12         # kaç saat sonra takipten çıkılacak
DATA_FILE = "follow_data.json"    # takip bilgilerinin saklanacağı dosya
FOLLOW_LIMIT_PER_CYCLE = 10       # her döngüde en fazla kaç kişi takip edilecek
CONFIG_FILE = "config.json"       # hesap bilgileri (otomatik oluşturulur)
# ------------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_config():
    """config.json varsa kullanıcı adı/şifreyi ordan al, yoksa None döndür."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return cfg.get("username"), cfg.get("password")
        except:
            pass
    return None, None

def save_config(username, password):
    """Başarılı girişten sonra config.json oluştur."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"username": username, "password": password}, f, indent=2)
        print(f"💾 Hesap bilgileri {CONFIG_FILE} dosyasına kaydedildi.")
    except Exception as e:
        print(f"⚠️ config.json kaydedilemedi: {e}")

def login_client():
    cl = Client()
    username, password = load_config()
    auto_login = bool(username and password)  # config var mı?

    if not auto_login:
        # İlk çalıştırma: kullanıcıya sor
        username = input("Instagram kullanıcı adı: ")
        password = getpass("Şifre: ")
    else:
        print(f"🔑 config.json’dan hesap bilgisi okundu ({username})")

    try:
        cl.login(username, password)
        print("✅ Giriş başarılı.\n")

        # Eğer config yoksa ve giriş başarılıysa, otomatik oluştur
        if not auto_login:
            save_config(username, password)

        return cl
    except Exception as e:
        print(f"❌ Giriş başarısız: {e}")
        # Hatalı girişte config varsa silmek ister misin? Şimdilik çık.
        exit(1)

def unfollow_if_needed(cl, followed_data):
    """Süresi dolmuş ve geri takip etmeyenleri unfollow yapar."""
    now = datetime.utcnow()
    threshold = now - timedelta(hours=UNFOLLOW_AFTER_HOURS)
    to_unfollow = []
    
    for user_id, info in followed_data.items():
        followed_at = datetime.fromisoformat(info["followed_at"])
        if followed_at < threshold:
            to_unfollow.append((user_id, info["username"]))
    
    for user_id, username in to_unfollow:
        try:
            friendship = cl.user_friendship(user_id)
            if not friendship.get("followed_by", False):
                cl.user_unfollow(user_id)
                del followed_data[user_id]
                print(f"❎ Takipten çıkıldı (geri takip etmedi): {username}")
            else:
                del followed_data[user_id]
                print(f"✅ Geri takip etti, kayıt silindi: {username}")
        except ClientError as e:
            print(f"⚠️ {username} unfollow hatası: {e}")
        time.sleep(2)

def follow_target_followers(cl, followed_data):
    """Hedef hesabın takipçilerinden yeni kişileri takip et."""
    try:
        target_id = cl.user_id_from_username(TARGET_USERNAME)
    except Exception as e:
        print(f"❌ Hedef kullanıcı bulunamadı: {e}")
        return

    try:
        followers = cl.user_followers(target_id, amount=200)
    except Exception as e:
        print(f"❌ Takipçiler alınamadı: {e}")
        return

    already_following = set(cl.user_following(cl.user_id).keys())
    followed_count = 0

    for user_id, user_info in followers.items():
        if str(user_id) in followed_data:
            continue
        if user_id in already_following:
            continue
        if followed_count >= FOLLOW_LIMIT_PER_CYCLE:
            break

        try:
            cl.user_follow(user_id)
            now = datetime.utcnow()
            followed_data[str(user_id)] = {
                "username": user_info.username,
                "followed_at": now.isoformat()
            }
            print(f"➕ Takip edildi: {user_info.username} ({now.strftime('%H:%M:%S')})")
            followed_count += 1
            time.sleep(FOLLOW_DELAY)
        except ClientError as e:
            print(f"⚠️ {user_info.username} takip hatası: {e}")
            time.sleep(5)

def main():
    print("=== Instagram Takip Botu (Termux) ===\n")
    print("⚠️ Uyarı: Bot kullanımı Instagram kurallarına aykırıdır, hesabınız askıya alınabilir.")
    cl = login_client()
    followed_data = load_data()

    print(f"Hedef: @{TARGET_USERNAME}")
    print(f"Takip aralığı: {FOLLOW_DELAY} saniye")
    print(f"Takipsizlik süresi: {UNFOLLOW_AFTER_HOURS} saat")
    print("Bot başlatıldı. Durdurmak için Ctrl+C\n")

    try:
        while True:
            print("🔄 Kontroller yapılıyor...")
            unfollow_if_needed(cl, followed_data)
            follow_target_followers(cl, followed_data)
            save_data(followed_data)
            print(f"⏳ {FOLLOW_DELAY} saniye bekleniyor...\n")
            time.sleep(FOLLOW_DELAY)
    except KeyboardInterrupt:
        print("\n🛑 Bot durduruldu.")
        save_data(followed_data)

if __name__ == "__main__":
    main()
