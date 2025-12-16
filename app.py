import os
import json
from flask import Flask, request, jsonify
from telegram import Bot
from telegram.error import TelegramError, Unauthorized # Telegram Hata sınıfını import edin

# -------------------------------------------------------------
# 1. ORTAM DEĞİŞKENLERİ VE İLK BAĞLANTI (ÇOK ÖNEMLİ)
# -------------------------------------------------------------

# BOT_TOKEN'i Render Environment'tan güvenli şekilde çekin.
BOT_TOKEN = os.environ.get('8086964160:AAEvy02LNcs1zOh5bW9REqrHfg2h2hkiXD8')

# Eğer BOT_TOKEN yoksa, uygulama hiç başlamamalıdır.
if not BOT_TOKEN:
    # Bu hata, Render loglarında (günlüklerinde) net görünür.
    print("HATA: BOT_TOKEN ortam değişkeni bulunamadi. Uygulama başlatılamiyor.")
    # Render'da uygulama başlatma hatası oluşur.
    # Bu, 'Unexpected end of JSON input' hatasını önler.
    exit(1)

# Bot objesini oluşturun
try:
    bot = Bot(token=BOT_TOKEN)
except Exception as e:
    print(f"HATA: Telegram Bot objesi oluşturulurken hata: {e}")
    exit(1)

# Bot'un kimliğini doğrulayın (Opsiyonel ama iyi bir pratik)
try:
    bot_info = bot.get_me()
    print(f"Bot Başariyla Başlatildi: @{bot_info.username}")
except Unauthorized:
    print("HATA: BOT_TOKEN geçersiz veya yetkisiz. Lütfen kontrol edin.")
    exit(1)
except Exception as e:
    print(f"HATA: Bot bilgisi alinirken genel hata: {e}")
    exit(1)

# Zorunlu Kanal Kullanıcı Adı (Render Environment'tan çekilmesi tavsiye edilir)
REQUIRED_CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', 'KrallarPDF')

# Flask Uygulamasını başlatın
app = Flask(__name__)

# -------------------------------------------------------------
# 2. ÜYELİK KONTROLÜ ENDPOINT'İ
# -------------------------------------------------------------

@app.route('/check_membership', methods=['POST', 'OPTIONS'])
def check_membership():
    # PRE-FLIGHT (OPTIONS) İsteği Kontrolü
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }

    # İstek gövdesini JSON olarak almaya çalışın
    try:
        data = request.get_json(force=True)
        user_id = data.get('user_id')
        channel_username = data.get('channel_username', REQUIRED_CHANNEL_USERNAME)
    except Exception:
        response = jsonify({'is_member': False, 'error': 'Gecersiz JSON veya eksik veri.'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400

    if not user_id or not channel_username:
        response = jsonify({'is_member': False, 'error': 'user_id veya channel_username eksik.'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400

    is_member = False
    
    try:
        # Telegram API'si ile üyelik kontrolü yapılır
        chat_member = bot.get_chat_member(chat_id=f"@{channel_username}", user_id=user_id)
        
        # Üyelik durumu kontrolü: member, administrator, creator
        status = chat_member.status
        if status in ['member', 'administrator', 'creator']:
            is_member = True
        
        # 3. Başarılı Yanıt Döndürülür
        response = jsonify({'is_member': is_member, 'status': status})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

    except TelegramError as e:
        # 4. Telegram API Hatası Yakalanırsa (Örn: Kullanıcı bulunamazsa, bot kanalda değilse)
        # Bu hata genellikle kullanıcı kanalda yoksa "User not found" veya "Bad Request" döner.
        print(f"Telegram API Hatasi yakalandi: {e.message}")
        
        # is_member: False döndürülmesi mantıklıdır.
        response = jsonify({'is_member': False, 'error': f'Telegram API Hatasi: {e.message}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200 # 500 yerine 200 (is_member=False) döndürmek daha temizdir

    except Exception as e:
        # 5. Genel Python/Sunucu Hatası Yakalanırsa
        # Bu genellikle 'Internal Server Error'dır
        print(f"Genel Python/Sunucu Hatasi: {e}")
        response = jsonify({'is_member': False, 'error': f'Sunucu Ic Hatasi: {e}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

# -------------------------------------------------------------
# 3. ANA UYGULAMA ÇALIŞTIRMA (Render/Gunicorn uyumlu)
# -------------------------------------------------------------
if __name__ == '__main__':
    # Gunicorn veya Render bunu kullanmaz, ancak yerel test için gereklidir.
    app.run(debug=True, port=int(os.environ.get('PORT', 5000))) 
