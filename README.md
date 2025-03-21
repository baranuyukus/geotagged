# GeoTagApp

Bu uygulama, kullanıcıların görsellerine coğrafi konum bilgisi (geotag) eklemelerine olanak sağlayan bir web uygulamasıdır.

## Özellikler

- Görsel yükleme (JPG / PNG / WebP formatları desteklenir)
- Mevcut geotag bilgilerini gösterme
- Harita üzerinden veya manuel olarak enlem/boylam bilgisi girme
- Ek EXIF etiketleri ekleme
- Etiketleri görsele yazma
- Etiketlenmiş görselleri indirme

## Kurulum

1. Python 3.8 veya daha yüksek bir sürüm gereklidir.
2. Sanal ortamı kurun ve aktifleştirin:
```
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Gerekli paketleri yükleyin:
```
pip install -r requirements.txt
```

4. Uygulamayı çalıştırın:
```
flask run
```

5. Tarayıcınızda http://127.0.0.1:5000 adresine giderek uygulamayı kullanabilirsiniz.

## Kullanım

1. Görsellerinizi yükleyin
2. Harita üzerinden veya manuel olarak konum bilgisi girin
3. İsteğe bağlı olarak ek etiketler ekleyin
4. "EXIF Etiketlerini Yaz" düğmesine tıklayın
5. Etiketlenmiş görseli indirin

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 