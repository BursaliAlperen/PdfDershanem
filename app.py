import requests
import os
import json
from flask import Flask, request, jsonify

# -----------------------------------------------------------
# GÜVENLİK AYARLARI VE BAŞLANGIÇ
# -----------------------------------------------------------
# Render üzerinden okunan Bot Token. Botunuzu bu değişkenle başlatın.
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
REQUIRED_CHANNEL_USERNAME = "@KrallarPDF"
FLASK_PORT = int(os.environ.get("PORT", 5000))

if not BOT_TOKEN:
    print("FATAL HATA: BOT_TOKEN ortam değişkeni ayarlanmadı! API çalışmayacak.")

app = Flask(__name__)

# -----------------------------------------------------------
# TELEGRAM ÜYELİK KONTROL İŞLEVİ
# -----------------------------------------------------------
def check_user_membership(user_id):
    """Kullanıcının Telegram kanalına üye olup olmadığını kontrol eder."""
    if not BOT_TOKEN:
        return False
        
    telegram_api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        'chat_id': REQUIRED_CHANNEL_USERNAME,
        'user_id': user_id
    }
    
    try:
        response = requests.get(telegram_api_url, params=params, timeout=5)
        response.raise_for_status() 
        data = response.json()
        
        if data.get('ok') and 'result' in data:
            status = data['result']['status']
            # member, administrator, creator = üye
            if status in ['member', 'administrator', 'creator']:
                return True
            else:
                return False
        else:
            print(f"Telegram API Hatası: {data.get('description', 'Bilinmeyen Hata - Bot kanalda yönetici mi?')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"İstek Hatası (getChatMember): {e}")
        return False

# -----------------------------------------------------------
# WEB APP'İN İSTEK ATACAĞI API ENDPOINT'İ VE CORS AYARI
# -----------------------------------------------------------
@app.route('/check_membership', methods=['POST', 'OPTIONS'])
def check_membership_api():
    """Web App'ten gelen üyelik kontrol isteğini karşılar."""
    # CORS (Cross-Origin Resource Sharing) başlıkları
    headers = {
        'Access-Control-Allow-Origin': '*', 
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'is_member': False, 'error': 'User ID missing in request'}), 400, headers
            
        is_member = check_user_membership(user_id)
        
        return jsonify({'is_member': is_member}), 200, headers
        
    except Exception as e:
        print(f"Genel API Hatası: {e}")
        return jsonify({'is_member': False, 'error': str(e)}), 500, headers

if __name__ == '__main__':
    print(f"Flask Sunucusu Başlatılıyor. PORT: {FLASK_PORT}")
    # Render'da host=0.0.0.0 kullanmak önemlidir.
    app.run(host='0.0.0.0', port=FLASK_PORT)
