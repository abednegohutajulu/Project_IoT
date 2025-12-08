from flask import Flask, request, jsonify
import face_recognition
import numpy as np
from PIL import Image
import os
import requests # <--- LIBRARY PENTING BUAT TELEGRAM

app = Flask(__name__)

# ==========================================================
# KONFIGURASI TELEGRAM (WAJIB DIGANTI!)
# ==========================================================
# 1. Buka Telegram -> Cari "BotFather" -> /newbot -> Dapat Token
TOKEN = "7846556422:AAEJjLLJTqXK6B0YTtYxUJpsqbQi2n_ywJ4" 

# 2. Buka Telegram -> Cari "userinfobot" -> Klik Start -> Dapat ID Angka
CHAT_ID = "6475577413"
# ====================================================================
# ==========================================================

# DATABASE WAJAH SEMENTARA
data_wajah_pemilik = []

def kirim_telegram(pesan, path_gambar):
    """
    Fungsi untuk mengirim notifikasi & foto ke Telegram
    """
    print(f">> [TELEGRAM] Mencoba mengirim pesan: '{pesan}'...")
    
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        
        # Buka file gambar yang baru saja disimpan
        with open(path_gambar, 'rb') as f:
            file_payload = {'photo': f}
            data_payload = {'chat_id': CHAT_ID, 'caption': pesan}
            
            # Kirim Request
            response = requests.post(url, files=file_payload, data=data_payload)
            
            # Cek Status
            if response.status_code == 200:
                print(">> [TELEGRAM] BERHASIL TERKIRIM! ✅")
            else:
                print(f">> [TELEGRAM] GAGAL! Error Code: {response.status_code}")
                print(f">> [TELEGRAM] Pesan dari Server: {response.text}")
                
    except Exception as e:
        print(f">> [TELEGRAM] Error Koneksi: {e}")

@app.route('/')
def home():
    return "SERVER LOKER PINTAR + TELEGRAM SIAP."

@app.route('/upload', methods=['POST'])
def upload_image():
    global data_wajah_pemilik
    
    print("\n[INFO] Menerima data dari ESP32...")
    
    try:
        # 1. CEK FILE MASUK
        if 'imageFile' not in request.files:
            return jsonify({"status": "error", "pesan": "No file"})
        
        file = request.files['imageFile']
        
        # 2. PROSES GAMBAR (METODE PIL)
        try:
            img_pil = Image.open(file)
            img_pil = img_pil.convert('RGB')
            
            # --- SIMPAN FOTO KE DISK (PENTING BUAT TELEGRAM) ---
            # Kita simpan dulu biar bisa dibaca oleh fungsi kirim_telegram
            nama_file = "cek_hasil_foto.jpg"
            img_pil.save(nama_file)
            print(f">> [DEBUG] Foto disimpan sementara: {nama_file}")
            # ---------------------------------------------------
            
            img_arr = np.array(img_pil)
            
        except Exception as e:
            print(f">> [X] Gambar Rusak: {e}")
            return jsonify({"status": "error", "pesan": "Bad Image"})

        # 3. DETEKSI WAJAH
        face_locations = face_recognition.face_locations(img_arr)
        
        if len(face_locations) == 0:
            print(f">> GAGAL: Wajah tidak terdeteksi.")
            return jsonify({"action": "tetap", "pesan": "Wajah Kosong"})

        # 4. AMBIL ENCODING
        face_encodings = face_recognition.face_encodings(img_arr, face_locations)
        if not face_encodings:
             return jsonify({"action": "tetap"})
             
        current_face = face_encodings[0]

        # ================= LOGIKA LOKER =================
        
        # SKENARIO A: DAFTAR BARU
        if len(data_wajah_pemilik) == 0:
            data_wajah_pemilik.append(current_face)
            
            print(">>> SUKSES: PENYEWA BARU TERDAFTAR! <<<")
            
            # --- KIRIM TELEGRAM ---
            pesan_wa = "✅ <b>PENDAFTARAN SUKSES!</b>\n\nWajah ini sekarang menjadi kunci loker."
            kirim_telegram(pesan_wa, nama_file)
            # ----------------------
            
            return jsonify({"action": "daftar", "pesan": "TERDAFTAR"})

        # SKENARIO B: VERIFIKASI (SUDAH ADA ISI)
        else:
            match = face_recognition.compare_faces([data_wajah_pemilik[0]], current_face, tolerance=0.5)
            
            if match[0]:
                print(">>> WAJAH COCOK! PINTU DIBUKA... <<<")
                data_wajah_pemilik.clear() 
                
                # --- KIRIM TELEGRAM ---
                pesan_wa = "🔓 <b>LOKER DIBUKA!</b>\n\nWajah cocok terdeteksi. Sistem di-reset."
                kirim_telegram(pesan_wa, nama_file)
                # ----------------------
                
                return jsonify({"action": "buka", "pesan": "BUKA"})
            else:
                print(">> DITOLAK: Wajah Tidak Cocok.")
                
                # --- KIRIM TELEGRAM (OPSIONAL - UNTUK KEAMANAN) ---
                pesan_wa = "⚠ <b>AKSES DITOLAK!</b>\n\nWajah asing mencoba membuka loker!"
                kirim_telegram(pesan_wa, nama_file)
                # --------------------------------------------------
                
                return jsonify({"action": "tolak", "pesan": "DITOLAK"})

    except Exception as e:
        print(f">> ERROR SISTEM FATAL: {e}")
        return jsonify({"status": "error", "pesan": str(e)})

if __name__ == '__main__':
    print("--> SERVER SIAP. Pastikan Token Telegram Benar!")
    app.run(host='0.0.0.0', port=5000, debug=True)
