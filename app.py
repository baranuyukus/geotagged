import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image, ExifTags
import piexif
import io
import json
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import traceback  # Detaylı hata bilgisi için
import shutil  # Klasör silme işlemi için
import threading  # Arkaplan işlemleri için
import time  # Zamanlama işlemleri için

app = Flask(__name__, static_folder='app/static', template_folder='app/templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'geotag-app-secret-key')
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
app.config['DOWNLOAD_FOLDER'] = 'app/static/downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB maksimum dosya boyutu
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'webp'}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///geotag.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Content tablosu için model sınıfı
class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Content {self.name}>'

# Klasörlerin varlığını kontrol et, yoksa oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Uygulama başladığında veritabanını oluştur
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

def cleanup_files(filepath, delay_seconds=3600):  # 1 saat sonra sil
    """Belirtilen dosyayı belirli bir süre sonra sil"""
    def delete_file():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Dosya silindi: {filepath}")
        except Exception as e:
            print(f"Dosya silinirken hata oluştu: {e}")
    
    # Arkaplanda çalışacak bir iş parçacığı başlat
    thread = threading.Thread(target=delete_file)
    thread.daemon = True  # Ana program kapandığında bu iş parçacığı da kapansın
    thread.start()

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Dosya seçilmedi')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Dosya seçilmedi')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Dosyayı 1 saat sonra silmek için zamanla
        cleanup_files(file_path)
        
        # EXIF verilerini oku
        exif_data = {}
        try:
            img = Image.open(file_path)
            if hasattr(img, '_getexif') and img._getexif():
                exif = {
                    ExifTags.TAGS[k]: v
                    for k, v in img._getexif().items()
                    if k in ExifTags.TAGS
                }
                
                # GPS verilerini kontrol et
                gps_info = {}
                if 'GPSInfo' in exif:
                    gps_info = {
                        ExifTags.GPSTAGS.get(k, k): v
                        for k, v in exif['GPSInfo'].items()
                    }
                    
                    # Enlem ve boylam değerlerini dönüştür
                    if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                        lat_ref = 1 if gps_info.get('GPSLatitudeRef', 'N') == 'N' else -1
                        lon_ref = 1 if gps_info.get('GPSLongitudeRef', 'E') == 'E' else -1
                        
                        lat = lat_ref * (
                            gps_info['GPSLatitude'][0] + 
                            gps_info['GPSLatitude'][1] / 60 + 
                            gps_info['GPSLatitude'][2] / 3600
                        )
                        
                        lon = lon_ref * (
                            gps_info['GPSLongitude'][0] + 
                            gps_info['GPSLongitude'][1] / 60 + 
                            gps_info['GPSLongitude'][2] / 3600
                        )
                        
                        exif_data['latitude'] = lat
                        exif_data['longitude'] = lon
        except Exception as e:
            flash(f"EXIF verilerini okurken hata oluştu: {str(e)}")
        
        return render_template('geotagging.html', 
                              filename=unique_filename, 
                              original_filename=filename, 
                              exif_data=exif_data)
    else:
        flash('İzin verilen dosya türleri: JPG, PNG, WebP')
        return redirect(request.url)

@app.route('/write_exif', methods=['POST'])
def write_exif():
    try:
        filename = request.form.get('filename')
        original_filename = request.form.get('original_filename')
        latitude = float(request.form.get('latitude', 0))
        longitude = float(request.form.get('longitude', 0))
        keywords = request.form.get('keywords', '')
        description = request.form.get('description', '')
        
        if not filename:
            flash('Dosya bulunamadı')
            return redirect(url_for('index'))
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Çıktı dosya adını oluştur
        file_ext = os.path.splitext(original_filename)[1]
        output_filename = f"botmarketi.com.tr_{uuid.uuid4()}{file_ext}"
        output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], output_filename)
        
        # Sadece JPG formatı için EXIF'i doğrudan destekler
        if file_ext.lower() in ['.jpg', '.jpeg']:
            # Görüntüyü aç
            img = Image.open(input_path)
            
            # Mevcut EXIF verilerini al
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
            try:
                if hasattr(img, '_getexif') and img._getexif():
                    exif_bytes = piexif.dump(piexif.load(input_path))
                    exif_dict = piexif.load(exif_bytes)
            except:
                pass  # Mevcut EXIF yoksa boş dict kullan
            
            # Görsel boyutları
            width, height = img.size
            exif_dict["Exif"][piexif.ExifIFD.PixelXDimension] = width
            exif_dict["Exif"][piexif.ExifIFD.PixelYDimension] = height
            
            # Anahtar kelimeler
            if keywords:
                try:
                    # DocumentName için UTF-8
                    exif_dict["0th"][piexif.ImageIFD.DocumentName] = keywords.encode('utf-8')
                    
                    # Windows XPKeywords için UTF-16 (little endian)
                    if hasattr(piexif.ImageIFD, 'XPKeywords'):
                        # UTF-16LE ile kodla ve null byte ekle
                        utf16_data = keywords.encode('utf-16le')
                        if not utf16_data.endswith(b'\x00\x00'):  # Eğer null byte yoksa ekle
                            utf16_data += b'\x00\x00'
                        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = utf16_data
                except Exception as e:
                    print(f"Anahtar kelimeler eklenirken hata: {e}")
            
            # Açıklama
            if description:
                try:
                    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
                except Exception as e:
                    print(f"Açıklama eklenirken hata: {e}")
            
            # GPS verileri
            if latitude != 0 or longitude != 0:
                # Referans değerleri
                lat_ref = 'N' if latitude >= 0 else 'S'
                lon_ref = 'E' if longitude >= 0 else 'W'
                
                # Mutlak değerler
                lat_abs = abs(latitude)
                lon_abs = abs(longitude)
                
                # Derece, dakika, saniye dönüşümü
                lat_deg = int(lat_abs)
                lat_min = int((lat_abs - lat_deg) * 60)
                lat_sec = int(((lat_abs - lat_deg) * 60 - lat_min) * 60 * 100)  # 100 ile çarparak hassasiyeti artırıyoruz
                
                lon_deg = int(lon_abs)
                lon_min = int((lon_abs - lon_deg) * 60)
                lon_sec = int(((lon_abs - lon_deg) * 60 - lon_min) * 60 * 100)  # 100 ile çarparak hassasiyeti artırıyoruz
                
                # GPS sözlüğünü güncelle
                exif_dict["GPS"] = {
                    piexif.GPSIFD.GPSVersionID: (2, 2, 0, 0),
                    piexif.GPSIFD.GPSLatitudeRef: lat_ref.encode('utf-8'),
                    piexif.GPSIFD.GPSLatitude: ((lat_deg, 1), (lat_min, 1), (lat_sec, 100)),  # Payda 100 yaparak hassasiyeti koruyoruz
                    piexif.GPSIFD.GPSLongitudeRef: lon_ref.encode('utf-8'),
                    piexif.GPSIFD.GPSLongitude: ((lon_deg, 1), (lon_min, 1), (lon_sec, 100)),  # Payda 100 yaparak hassasiyeti koruyoruz
                    piexif.GPSIFD.GPSDateStamp: datetime.now().strftime("%Y:%m:%d").encode('utf-8')
                }
            
            # EXIF verilerini oluştur ve görüntüye kaydet
            try:
                exif_bytes = piexif.dump(exif_dict)
                # Kalite parametresini kaldırdık, görüntüyü olduğu gibi kaydet
                img.save(output_path, format='JPEG', exif=exif_bytes)
                
                # İndirme dosyasını da 1 saat sonra sil
                cleanup_files(output_path)
                
                # Doğrulama sayfasına yönlendir
                return redirect(url_for('verify', filename=output_filename))
                
            except Exception as e:
                print(f"EXIF yazma hatası: {e}")
                print(traceback.format_exc())
                flash(f"EXIF verilerini yazarken hata oluştu: {str(e)}")
                return redirect(url_for('index'))
        else:
            # JPG formatı dışındakiler için EXIF desteği sınırlı
            img = Image.open(input_path)
            img.save(output_path)
            flash('EXIF verileri yalnızca JPG formatında tam olarak desteklenir. Görseliniz kaydedildi ancak EXIF verileri eklenemedi.')
            
            # İndirme dosyasını da 1 saat sonra sil
            cleanup_files(output_path)
            
            # Doğrulama sayfasına yönlendir
            return redirect(url_for('verify', filename=output_filename))
            
    except Exception as e:
        print(f"Genel işlem hatası: {e}")
        print(traceback.format_exc())
        flash(f"İşlem sırasında hata oluştu: {str(e)}")
        return redirect(url_for('index'))

# Yeni doğrulama route'u ekle
@app.route('/verify/<filename>')
def verify(filename):
    # Dosyanın varlığını kontrol et
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash('Dosya bulunamadı')
        return redirect(url_for('index'))
    
    # Dosya oluşturulma zamanını kontrol et
    try:
        file_creation_time = os.path.getctime(file_path)
        current_time = time.time()
        
        # Eğer dosya 5 saniyeden daha eskiyse, muhtemelen eski bir dosya
        if current_time - file_creation_time > 5:
            flash('Bu oturum zaman aşımına uğradı. Lütfen işlemi tekrar yapın.')
            return redirect(url_for('index'))
    except Exception as e:
        print(f"Dosya zaman kontrolü hatası: {e}")
    
    return render_template('verify.html', filename=filename)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    
    # Dosyanın varlığını ve yaşını kontrol et
    if os.path.exists(file_path):
        file_creation_time = os.path.getctime(file_path)
        current_time = time.time()
        
        # Dosya en az 10 saniye önce oluşturulmuş olmalı
        if current_time - file_creation_time < 10:
            flash('Lütfen dosyayı indirmek için 10 saniye bekleyin.')
            return redirect(url_for('verify', filename=filename))
            
        # Eğer dosya 1 saatten daha eskiyse
        if current_time - file_creation_time > 3600:
            flash('Bu dosyanın süresi dolmuş. Lütfen işlemi tekrar yapın.')
            return redirect(url_for('index'))
            
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)
    else:
        flash('Dosya bulunamadı')
        return redirect(url_for('index'))

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/impressum', methods=['GET'])
def impressum():
    return render_template('impressum.html')

# Uygulama başladığında eski dosyaları temizle
def cleanup_old_files():
    """Uygulama başladığında uploads ve downloads klasörlerini temizle"""
    try:
        # uploads klasörünü temizle
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        # downloads klasörünü temizle
        if os.path.exists(app.config['DOWNLOAD_FOLDER']):
            shutil.rmtree(app.config['DOWNLOAD_FOLDER'])
            os.makedirs(app.config['DOWNLOAD_FOLDER'])
            
        print("Eski dosyalar temizlendi")
    except Exception as e:
        print(f"Dosyalar temizlenirken hata oluştu: {e}")

# Uygulama başladığında temizlik yap
with app.app_context():
    cleanup_old_files()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0', port=port) 