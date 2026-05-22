from instagrapi import Client
import time
import json
from datetime import datetime, timedelta

USERNAME = "leylaaszk"
TARGET_INFLUENCER = "ssekwr"
CHECK_INTERVAL = 30  # saniye
UNFOLLOW_AFTER_HOURS = 12
FOLLOW_LIMIT_PER_CYCLE = 5

DATA_FILE = "followed_users.json"

cl = Client()


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


print("Instagram giriş")
password = input("Şifre: ")

try:
    cl.login(USERNAME, password)
    print("Giriş başarılı")
except Exception as e:
    print("Giriş hatası:", e)
    exit()

followed_data = load_data()

try:
    target_id = cl.user_id_from_username(TARGET_INFLUENCER)
except Exception as e:
    print("Hedef kullanıcı bulunamadı:", e)
    exit()

print(f"{TARGET_INFLUENCER} takipçileri alınıyor...")

while True:
    try:
        followers = cl.user_followers(target_id)
        my_followers = cl.user_followers(cl.user_id)

        my_follower_ids = set(my_followers.keys())

        # Yeni kişileri takip et
        count = 0
        for user_id, user in followers.items():
            if count >= FOLLOW_LIMIT_PER_CYCLE:
                break

            if str(user_id) in followed_data:
                continue

            try:
                cl.user_follow(user_id)
                followed_data[str(user_id)] = {
                    "username": user.username,
                    "time": datetime.now().isoformat()
                }
                save_data(followed_data)

                print(f"Takip edildi: {user.username}")
                count += 1

                time.sleep(10)

            except Exception as e:
                print(f"Takip hatası {user.username}: {e}")

        # 12 saat sonra geri takip etmeyenleri çıkar
        remove_list = []

        for user_id, info in followed_data.items():
            followed_time = datetime.fromisoformat(info["time"])

            if datetime.now() - followed_time >= timedelta(hours=UNFOLLOW_AFTER_HOURS):
                if int(user_id) not in my_follower_ids:
                    try:
                        cl.user_unfollow(int(user_id))
                        print(f"Takipten çıkıldı: {info['username']}")
                        remove_list.append(user_id)
                        time.sleep(10)

                    except Exception as e:
                        print(f"Çıkış hatası {info['username']}: {e}")
                else:
                    print(f"Geri takip etti: {info['username']}")
                    remove_list.append(user_id)

        for uid in remove_list:
            followed_data.pop(uid, None)

        save_data(followed_data)

        print(f"{CHECK_INTERVAL} saniye bekleniyor...")
        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        print("Ana döngü hatası:", e)
        time.sleep(60)
