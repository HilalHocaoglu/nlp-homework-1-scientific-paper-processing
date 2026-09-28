# Homework 1 — Scientific Paper Processing with spaCy

Bu depo, bilimsel makaleleri PDF'den başlayarak yapılandırılmış NLP verisine
dönüştürmek için adım adım geliştiriliyor. İlk aşama, sayfa numaralarını ve
satır sonlarını koruyarak PDF metnini çıkarmak.

## Durum

- [x] Başlangıç depo yapısı
- [x] Sayfa bazında PyMuPDF çıkarım prototipi
- [ ] PDF'ler üzerinde ilk kalite incelemesi
- [ ] Bölüm ve paragraf tespiti
- [ ] spaCy cümleleme, tokenizasyon ve dilbilgisi etiketleri
- [ ] İstatistikler ve JSON çıktıları
- [ ] Rapor ve son kullanım yönergeleri

Deneme kararları ve bulgular [`notes/experiment_log.md`](notes/experiment_log.md)
içinde tutuluyor.

## Kurulum

Python 3 ile sanal ortam oluşturup bağımlılıkları kur:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## İlk aşamayı çalıştırma

PDF yollarını komut satırında ver:

```bash
PYTHONPATH=src python -m scipaper.extraction \
  "$HOME/Downloads/AttentionYouNeed.pdf" \
  --output-dir outputs/extracted_text
```

Birden çok PDF yolu aynı komutta verilebilir. Her PDF için `outputs/extracted_text/`
altına sayfa işaretli bir `.txt` dosyası yazılır; sayfa, karakter ve kelime
sayıları terminale JSON olarak yazdırılır. Okuma sırası yöntemini karşılaştırmak
için `--preserve-pdf-order` seçeneği, PyMuPDF'nin varsayılan sırasını kullanır;
seçenek verilmezse bloklar sayfa konumuna göre sıralanır.

## Girdi ve çıktı

- **Girdi:** PDF dosyaları. PDF'leri repoya kopyalamak zorunlu değil; yolları
  komuta veya notebook ayarına ver.
- **İlk çıktı:** Sayfa sınırları `===== PAGE n =====` ile işaretlenmiş UTF-8
  metin dosyaları.
- **Sonraki çıktı:** Her makale için Homework 2'de kullanılacak JSON.

## Sınırlamalar

İlk prototip metin sırasını sayfa koordinatlarına göre düzenlemeyi dener; iki
sütunlu sayfalarda, tablolar, denklemler ve başlık/altbilgilerde hata yapabilir.
Bu durumları gerçek çıktıyı inceledikten sonra deney günlüğüne yazacağız.
