from telegram.error import TelegramError
# ... (diğer import ve setup'lar) ...

@app.route('/check_membership', methods=['POST', 'OPTIONS'])
def check_membership():
    # CORS PRE-FLIGHT isteğini hemen yanıtla
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        
    # Varsayılan hata yanıtı
    default_error_response = {
        'is_member': False, 
        'error': 'Sunucu beklenmedik bir hata verdi.'
    }
    
    try:
        data = request.json
        user_id = data.get('user_id')
        channel_username = data.get('channel_username')
        
        if not user_id or not channel_username:
            response = jsonify({'is_member': False, 'error': 'Eksik Kullanici ID veya Kanal Adi'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400

        # Bot API İSTEĞİ
        # Eğer bot.get_chat_member bu noktada bir hata verirse (Örn: Kanal bulunamadı, BOT_TOKEN yanlış)
        # kod aşağı atlar ve except bloklarından biri yakalar.
        member = bot.get_chat_member(chat_id='@' + channel_username, user_id=user_id)
        
        # Üyelik kontrolü
        is_member = member.status in ['member', 'administrator', 'creator']
        
        # BAŞARILI DURUM: JSON yanıtı gönderiliyor
        response = jsonify({'is_member': is_member})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except TelegramError as e:
        # Telegram API'den kaynaklanan hatalar (Örn: Bot kanalda yönetici değil, kanal adı yanlış)
        print(f"Telegram API Hatasi: {e}")
        
        # Hata durumunda bile Frontend'in beklediği JSON formatını döndür
        response = jsonify({'is_member': False, 'error': f'Telegram API Hatasi: {e.message}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
        
    except Exception as e:
        # Kodun içindeki diğer hatalar (Örn: JSON parse hatası)
        print(f"Genel Hata: {e}")
        
        # Hata durumunda bile Frontend'in beklediği JSON formatını döndür
        response = jsonify({'is_member': False, 'error': f'Sunucu Iç Hatasi: {e}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
