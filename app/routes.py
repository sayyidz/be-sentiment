from flask import Blueprint, render_template, request, jsonify
import io
import tempfile
import pandas as pd
from .utils import preprocess_and_predict, konversi_ke_bulan_tahun, clean_text, assign_sector, model, tfidf
from werkzeug.utils import secure_filename
import re, string
import numpy as np
from datetime import datetime, timedelta
from .models import db, Wisata
from .supabase import supabase, SUPABASE_BUCKET
from werkzeug.security import generate_password_hash, check_password_hash
from.jwt import generate_token, jwt_required
import requests

main = Blueprint('main', __name__)
UPLOAD_FOLDER = 'uploads'

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/files', methods=['GET'])
def list_files():
    try:
        response = supabase.storage.from_(SUPABASE_BUCKET).list('datasets')
        print("DEBUG response:", response)
        files = [f['name'] for f in response if f.get('name') and f.get('metadata', {}).get('mimetype') != 'folder']
        file_urls = [
            {
                'name': name,
                'url': supabase.storage.from_(SUPABASE_BUCKET).get_public_url(f'datasets/{name}')
            }
            for name in files
        ]
        return jsonify(file_urls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/predict', methods=['POST'])
def predict_sentiment():
    try:
        data = request.get_json()
        file_url = data.get('file_url')

        if not file_url:
            return jsonify({'error': 'file_url tidak boleh kosong'}), 400

        # Unduh file CSV dari Supabase Storage URL
        response = requests.get(file_url)
        if response.status_code != 200:
            return jsonify({'error': 'Gagal mengunduh file dari Supabase Storage'}), 500

        try:
            # Coba baca CSV
            file_content = io.StringIO(response.text)
            df = pd.read_csv(file_content, encoding='utf-8')
        except Exception:
            # Coba alternatif encoding dan delimiter jika gagal
            file_content = io.StringIO(response.text)
            df = pd.read_csv(file_content, encoding='ISO-8859-1', sep=',')
        
        # Baca isi CSV
        file_content = io.StringIO(response.text)
        df = pd.read_csv(file_content)
        if 'ulasan' not in df.columns or 'waktu' not in df.columns or 'nama' not in df.columns:
            return jsonify({'error': 'Kolom "ulasan", "waktu", dan "nama" harus ada dalam file CSV'}), 400

        # Tambahkan kolom bulan_tahun
        df['bulan_tahun'] = df['waktu'].apply(konversi_ke_bulan_tahun)

        # Bersihkan teks dan klasifikasi sektor
        df['sektor'] = df['ulasan'].astype(str).apply(lambda x: assign_sector(clean_text(x)))

        result_data, chart_data = preprocess_and_predict(df)
        sentimen_chart_data = chart_data
        # Konversi result_data (list of dict) ke DataFrame
        predicted_df = pd.DataFrame(result_data)

        # Tambahkan kolom 'prediksi' ke df
        df['prediksi'] = predicted_df['prediksi']

        # Hitung 5 sektor dengan komentar negatif terbanyak
        negatif_per_sektor = df[df['prediksi'] == -1]['sektor'].value_counts()
        negatif_per_sektor = negatif_per_sektor[negatif_per_sektor.index != 'lainnya']
        negatif_per_sektor = negatif_per_sektor.head(5)  # Ambil 5 teratas
        negatif_chart_data = negatif_per_sektor.to_dict()

        # Komentar negatif per bulan
        df_negatif = df[df['prediksi'] == -1]
        komentar_negatif_per_bulan = df_negatif.groupby('bulan_tahun').size().reset_index(name='jumlah_negatif')
        komentar_negatif_per_bulan['bulan_tahun_dt'] = pd.to_datetime(komentar_negatif_per_bulan['bulan_tahun'], format='%B %Y')
        komentar_negatif_per_bulan = komentar_negatif_per_bulan.sort_values(by='bulan_tahun_dt')
        komentar_negatif_per_bulan['bulan_tahun'] = komentar_negatif_per_bulan['bulan_tahun_dt'].dt.strftime('%B %Y')
        komentar_negatif_per_bulan = komentar_negatif_per_bulan[['bulan_tahun', 'jumlah_negatif']]


        # Ubah ke format dict
        bulanan_data = komentar_negatif_per_bulan.to_dict(orient='records')

        df_negatif = df[df['prediksi'] == -1]
        df_negatif = df_negatif[df_negatif['sektor'].str.lower() != 'lainnya']

        negatif_per_bulan_sektor = df_negatif.groupby(['bulan_tahun', 'sektor']).size().reset_index(name='jumlah_komentar_negatif')

        negatif_per_bulan_sektor['bulan_tahun_dt'] = pd.to_datetime(negatif_per_bulan_sektor['bulan_tahun'], format='%B %Y')
        negatif_per_bulan_sektor = negatif_per_bulan_sektor.sort_values(by=['bulan_tahun_dt', 'jumlah_komentar_negatif'], ascending=[False, False])
        negatif_per_bulan_sektor['bulan_tahun'] = negatif_per_bulan_sektor['bulan_tahun_dt'].dt.strftime('%B %Y')

        top3 = negatif_per_bulan_sektor.groupby('bulan_tahun').head(3)
        print("=== Data Top 3 ===")
        print(top3.to_string(index=False))

        # Buat struktur data untuk Chart.js
        bulan_list = sorted(top3['bulan_tahun'].unique(), key=lambda x: pd.to_datetime(x, format='%B %Y'))
        sektor_list = top3['sektor'].unique()

        chart_data = {sektor: [] for sektor in sektor_list}

        for bulan in bulan_list:
            data_bulan = top3[top3['bulan_tahun'] == bulan]
            for sektor in sektor_list:
                val = data_bulan[data_bulan['sektor'] == sektor]['jumlah_komentar_negatif']
                if not val.empty:
                    chart_data[sektor].append(int(val.values[0]))
                else:
                    chart_data[sektor].append(0)

        print("=== Chart Data per Sektor ===")
        for sektor in chart_data:
            print(f"{sektor}: {chart_data[sektor]}")

        return jsonify({
            'data': result_data,
            'chart': sentimen_chart_data,
            'negatif_per_sektor': negatif_chart_data,
            'negatif_per_bulan': bulanan_data,
            'top5_bulanan': {
                'labels': bulan_list,
                'datasets': [
                    {'label': sektor, 'data': chart_data[sektor]}
                    for sektor in sektor_list
                ]
            }
        })
        

    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@main.route('/test-sentiment', methods=['POST'])
def test_single_sentiment():
    try:
        data = request.get_json()
        sentence = data.get('sentence', '')

        if not sentence.strip():
            return jsonify({'error': 'Kalimat tidak boleh kosong'}), 400

        cleaned = clean_text(sentence)
        vector = tfidf.transform([cleaned])
        prediction = int(model.predict(vector)[0])
        sector = assign_sector(cleaned)

        sentiment_map = {-1: 'Negatif', 0: 'Netral', 1: 'Positif'}
        sentiment = sentiment_map.get(prediction, 'Tidak diketahui')

        return jsonify({
            'original': sentence,
            'cleaned': cleaned,
            'sentiment': sentiment,
            'sector': sector
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    path = f"datasets/{timestamp}_{filename}"

    try:
        # upload ke storage Supabase
        result = supabase.storage.from_(SUPABASE_BUCKET).upload(path, file.read())
        if not result:
            return jsonify({'error': 'Upload failed'}), 500

        # dapatkan public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(path)
        print("DEBUG URL:", public_url)

        return jsonify({
            'message': 'File uploaded successfully',
            'url': public_url
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api', methods=['GET'])
def ping():
    return jsonify({"message": "API is working!"}), 200

@main.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'Semua field wajib diisi'}), 400

    # Cek apakah user/email sudah ada
    existing = supabase.table('users')\
        .select('id')\
        .or_(f"name.eq.{name},email.eq.{email}")\
        .execute()

    if existing.data:
        return jsonify({'error': 'name atau email sudah digunakan'}), 400

    hashed_pw = generate_password_hash(password)

    result = supabase.table('users').insert({
        'name': name,
        'email': email,
        'password': hashed_pw
    }).execute()

    return jsonify({'message': 'Registrasi berhasil'}), 201

@main.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email dan password wajib diisi'}), 400

    result = supabase.table('users').select('*').eq('email', email).single().execute()
    user = result.data

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Email atau password salah'}), 401

    token = generate_token(user['id'])

    return jsonify({'message': 'Login berhasil', 'token': token})

@main.route('/profile', methods=['GET'])
@jwt_required
def profile():
    return jsonify({'message': f'Akses berhasil untuk user ID: {request.user_id}'})

@main.route('/top-files', methods=['GET'])
def get_top_files():
    try:
        response = supabase.storage.from_(SUPABASE_BUCKET).list('datasets')
        csv_files = [f for f in response if f['name'].endswith('.csv')]

        file_counts = []

        for file in csv_files:
            path = f"datasets/{file['name']}"
            public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(path)
            csv_data = requests.get(public_url)

            if csv_data.status_code == 200:
                df = pd.read_csv(io.StringIO(csv_data.text))
                file_counts.append({
                    'name': file['name'],
                    'count': len(df)
                })

        # Urutkan berdasarkan count terbesar dan ambil 5
        top_files = sorted(file_counts, key=lambda x: x['count'], reverse=True)[:5]

        return jsonify(top_files)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
