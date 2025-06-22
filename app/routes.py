from flask import Blueprint, render_template, request, jsonify
import os, csv
import tempfile
import pandas as pd
from .utils import preprocess_and_predict, konversi_ke_bulan_tahun, clean_text, assign_sector, model, tfidf
from werkzeug.utils import secure_filename
import re, string
import numpy as np
from datetime import datetime, timedelta
from .models import db, Wisata
from .supabase import supabase, SUPABASE_URL

main = Blueprint('main', __name__)
UPLOAD_FOLDER = 'uploads'

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/predict', methods=['POST'])
def predict_sentiment():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        df = pd.read_csv(filepath)
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

        # Hitung jumlah komentar negatif per sektor
        negatif_per_sektor = df[df['prediksi'] == -1]['sektor'].value_counts()
        negatif_per_sektor = negatif_per_sektor[negatif_per_sektor.index != 'lainnya']
        negatif_chart_data = negatif_per_sektor.to_dict()

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

        top5 = negatif_per_bulan_sektor.groupby('bulan_tahun').head(5)

        # Buat struktur data untuk Chart.js
        bulan_list = sorted(top5['bulan_tahun'].unique(), key=lambda x: pd.to_datetime(x, format='%B %Y'))
        sektor_list = top5['sektor'].unique()

        chart_data = {sektor: [] for sektor in sektor_list}

        for bulan in bulan_list:
            data_bulan = top5[top5['bulan_tahun'] == bulan]
            for sektor in sektor_list:
                val = data_bulan[data_bulan['sektor'] == sektor]['jumlah_komentar_negatif']
                if not val.empty:
                    chart_data[sektor].append(int(val.values[0]))
                else:
                    chart_data[sektor].append(0)

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
def upload_file():
    file = request.files.get('file')
    nama_wisata = request.form.get('nama_wisata')

    if not file or not nama_wisata:
        return jsonify({'error': 'Nama wisata dan file diperlukan'}), 400

    filename = secure_filename(file.filename)

    # Simpan sementara ke file disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        file.save(temp_file.name)
        temp_path = temp_file.name

    try:
        # Upload ke Supabase dari file path
        res = supabase.storage.from_('wisata-data').upload(
            path=filename,
            file=temp_path,  # HARUS path
            file_options={"content-type": "text/csv"}
        )

        if res.get("error"):
            return jsonify({"error": "Gagal upload ke Supabase", "detail": res["error"]["message"]}), 500

        public_url = f"{SUPABASE_URL}/storage/v1/object/public/wisatadata/{filename}"

        # Baca CSV dari path temp
        df = pd.read_csv(temp_path)
        jumlah_ulasan = len(df)

        # Simpan ke database
        wisata = Wisata(
            nama_wisata=nama_wisata,
            jumlah_ulasan=jumlah_ulasan,
            link_file=public_url
        )
        db.session.add(wisata)
        db.session.commit()

        return jsonify({'message': 'Data wisata berhasil ditambahkan'})

    finally:
        # Hapus file temp setelah selesai
        if os.path.exists(temp_path):
            os.remove(temp_path)

@main.route('/api', methods=['GET'])
def ping():
    return jsonify({"message": "API is working!"}), 200