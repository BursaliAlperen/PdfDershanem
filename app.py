@app.route('/check_membership', methods=['POST', 'OPTIONS'])
def check_membership():
    # 1. PRE-FLIGHT (OPTIONS) İsteği Kontrolü
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        
    try:
        # ... (Tüm başarılı veya başarısız üyelik kontrolü mantığı) ...
        
        # Bu kısım, API'den gelen veriye göre is_member: True veya False döndürmelidir.
        response = jsonify({'is_member': is_member})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except TelegramError as e:
        # 2. Telegram API Hatası Yakalanırsa
        print(f"Telegram API Hatasi: {e}")
        response = jsonify({'is_member': False, 'error': f'Telegram API Hatasi: {e.message}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
        
    except Exception as e:
        # 3. Genel Python Hatası Yakalanırsa
        print(f"Genel Hata: {e}")
        response = jsonify({'is_member': False, 'error': f'Sunucu Iç Hatasi: {e}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

    # Bu noktaya normalde gelinmemesi gerekir, ancak garanti olması için:
    except:
        response = jsonify({'is_member': False, 'error': 'Bilinmeyen ve Yakalanmayan Hata.'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
