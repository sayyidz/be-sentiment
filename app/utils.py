import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np
import re, string

# Load model dan TF-IDF
model = joblib.load('app/model/svm_model.pkl')
tfidf = joblib.load('app/model/tfidf.pkl')

stopwords_id = set([
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "ada", "karena", "saja", "lebih", "tidak", "bukan", "atau",
    "sudah", "masih", "seperti", "pada", "oleh", "itu", "ini", "sangat", "juga", "akan", "dalam", "adalah", "ia",
    "mereka", "kami", "kita", "aku", "saya", "engkau", "kamu", "dia", "bagi", "pada", "tentang", "maupun", "hanya",
    "hingga", "sebagai", "apa", "siapa", "dimana", "kapan", "mengapa", "bagaimana", "ya", "oh", "nah", "loh", "kok",
    "pun", "lagi", "lah", "tapi", "dan", "jadi", "maka", "agar", "sehingga", "kalau", "namun", "meskipun", "walaupun",
    "setelah", "sebelum", "selama", "tanpa", "selain", "tersebut", "yakni", "yaitu", "dll", "dst", "terhadap",
    "antar", "antara", "oleh", "pada", "dapat", "hal", "bahwa", "lain", "oleh", "itu", "dalam", "tersebut", "dengan",
    "berupa", "berada", "telah", "agar", "bahkan", "karena", "sebab", "akibat", "demi", "guna", "sekitar", "sekira",
    "sekitar", "maupun", "hingga", "hingga", "sebab", "setiap", "tanpa", "namun", "semua", "sudah", "baru", "lama",
    "sangat", "dalam", "juga", "akan", "kalau", "tentu", "mereka", "kami", "kita", "dia",
    "jadi", "namun", "semua", "bisa", "harus", "dapat", "lagi", "hanya", "agar",
    "ya", "nah", "kok", "lah", "dong", "pun", "eh", "deh", "toh", "tuh", "si", "punya"
])

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = text.strip()
    text = ' '.join([word for word in text.split() if word not in stopwords_id])
    return text

def preprocess_and_predict(df):
    if 'ulasan' not in df.columns:
        raise ValueError("CSV harus memiliki kolom 'ulasan'")

    # Inisialisasi list hasil
    cleaned_list = []
    prediction_list = []

    # Buat salinan df hanya dengan ulasan valid
    valid_df = df.dropna(subset=['ulasan']).copy()
    valid_df = valid_df[valid_df['ulasan'].astype(str).str.strip() != ""]

    for ulasan in valid_df['ulasan']:
        cleaned = clean_text(str(ulasan))
        vector = tfidf.transform([cleaned])
        pred = model.predict(vector)[0]

        cleaned_list.append(cleaned)
        prediction_list.append(int(pred))

    # Tambahkan hasil ke valid_df
    valid_df['cleaned'] = cleaned_list
    valid_df['prediksi'] = prediction_list

    # Hitung statistik
    count = valid_df['prediksi'].value_counts().to_dict()
    sentiment_map = {-1: 'Negatif', 0: 'Netral', 1: 'Positif'}
    count_mapped = {sentiment_map.get(k, str(k)): v for k, v in count.items()}

    return valid_df.to_dict(orient='records'), count_mapped

def konversi_ke_bulan_tahun(waktu_str):
    now = datetime.now()
    if pd.isna(waktu_str):
        return np.nan
    waktu_str = str(waktu_str).lower()

    try:
        if "detik" in waktu_str or "menit" in waktu_str or "jam" in waktu_str:
            tanggal = now
        elif "hari" in waktu_str:
            hari = int(waktu_str.split()[0])
            tanggal = now - timedelta(days=hari)
        elif "minggu" in waktu_str:
            minggu = int(waktu_str.split()[0]) if waktu_str.split()[0].isdigit() else 1
            tanggal = now - timedelta(weeks=minggu)
        elif "bulan" in waktu_str:
            bulan = int(waktu_str.split()[0]) if waktu_str.split()[0].isdigit() else 1
            bulan_lalu = now.month - bulan
            tahun = now.year
            if bulan_lalu <= 0:
                bulan_lalu += 12
                tahun -= 1
            tanggal = datetime(tahun, bulan_lalu, 1)
        elif "tahun" in waktu_str:
            tahun = now.year - int(waktu_str.split()[0]) if waktu_str.split()[0].isdigit() else 1
            tanggal = datetime(tahun, now.month, 1)
        else:
            return np.nan

        return tanggal.strftime('%B %Y')
    except:
        return np.nan

sektor_keywords = {
    "Kebersihan Toilet Buruk": [
        "toilet", "wc", "kamar mandi", "kotor", "jorok", "bau", "mampet", "rusak", "pesing",
        "toilet kotor", "wc bau", "toilet jorok", "bau pesing", "toilet rusak", "wc penuh", "wc mampet",
        "bau menyengat", "kamar mandi jorok"
    ],
    "Ketidaknyamanan Area Parkir": [
        "parkir", "penuh", "sempit", "susah", "jauh", "macet",
        "parkiran sempit", "sulit parkir", "tidak ada parkiran", "area parkir tidak aman",
        "parkir mahal", "parkir jauh", "tidak tertata", "susah keluar"
    ],
    "Pelayanan Petugas": [
        "petugas", "staff", "cs", "pegawai", "jutek", "kasar", "lambat", "tidak ramah", "tidak membantu",
        "pelayanan lambat", "tidak sopan", "kurang membantu", "tidak informatif"
    ],
    "Harga Tidak Sesuai": [
        "mahal", "murah", "harga", "biaya", "tiket", "ongkos", "tidak sebanding", "kemahalan",
        "harga mahal", "biaya tinggi", "harga tidak sesuai", "tiket terlalu mahal", "pelayanan tidak sepadan"
    ],
    "Antrian Panjang dan Tidak Teratur": [
        "antri", "antrian", "lama", "penuh", "desak", "tidak tertib", "berdesakan",
        "antrian panjang", "tidak tertib", "berdesakan", "antri lama", "sistem antri buruk",
        "tidak ada nomor antri", "rebutan antrian"
    ],
    "Transportasi dan Lokasi Sulit": [
        "macet", "terpencil", "jauh", "akses", "sulit", "transportasi", "rusak", "tidak dijangkau",
        "sulit dijangkau", "transportasi terbatas", "tidak ada angkutan umum", "akses buruk", 
        "jalan rusak", "tidak ada petunjuk arah"
    ],
    "Kurangnya Informasi dan Petunjuk Arah": [
        "bingung", "tidak tahu", "tidak jelas", "minim", "kurang", "informasi", "arah", "papan",
        "tidak ada petunjuk", "minim informasi", "bingung arah", "tidak ada papan informasi",
        "kurang penjelasan", "tidak diarahkan"
    ],
    "Kerusakan atau Ketidaksiapan Fasilitas": [
        "rusak", "bocor", "mati", "patah", "tidak berfungsi", "tidak tersedia", "lampu", "ac", "lift", "keran",
        "fasilitas rusak", "kursi patah", "atap bocor", "lampu mati", "AC tidak dingin",
        "keran rusak", "wifi mati", "kunci rusak"
    ],
    "Kondisi Lingkungan Kotor": [
        "sampah", "jorok", "kotor", "kumuh", "tidak rapi", "bau", "buruk", "tidak terurus", "semrawut",
        "lingkungan kumuh", "banyak sampah", "tidak dibersihkan", "tanaman mati", 
        "pemandangan buruk", "bau tak sedap"
    ],
    "Tingkat Keamanan Rendah": [
        "tidak aman", "rawan", "copet", "pencuri", "penjaga", "satpam", "pengawasan", "terancam",
        "kehilangan", "keamanan", "penipuan", "kerusuhan"
    ],
    "Gangguan dari Pengunjung Lain": [
        "ribut", "bising", "perokok", "gaduh", "berisik", "kasar", "tidak nyaman", "ramai",
        "pengunjung ribut", "anak-anak berisik", "pengunjung kasar", "bikin gaduh", "rokok"
    ],
    "Ketersediaan Tempat Duduk": [
        "kursi", "duduk", "tidak ada kursi", "tidak bisa duduk", "area tunggu sempit",
        "kurang tempat duduk", "duduk di lantai", "tempat duduk penuh"
    ],
    "Kondisi Cuaca": [
        "panas", "hujan", "banjir", "becek", "cuaca", "terik", "berlumpur",
        "panas terik", "tidak ada peneduh", "hujan deras", "tidak nyaman karena cuaca"
    ],
    "Masalah Pemesanan Tiket": [
        "gagal", "sulit", "error", "habis", "lambat", "tidak bisa", "pesan", "beli", "booking",
        "gagal pesan tiket", "aplikasi error", "tiket habis", "tidak bisa beli tiket",
        "susah akses aplikasi", "website lambat"
    ]
}


def assign_sector(text):
    text = text.lower()
    sector_scores = {sector: 0 for sector in sektor_keywords}
    for sector, keywords in sektor_keywords.items():
        for keyword in keywords:
            if keyword in text:
                sector_scores[sector] += 1

    max_score = max(sector_scores.values())
    if max_score == 0:
        return "lainnya"

    best_sectors = [sector for sector, score in sector_scores.items() if score == max_score]
    return best_sectors[0]