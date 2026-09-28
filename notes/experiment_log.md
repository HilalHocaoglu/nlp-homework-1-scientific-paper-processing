# Experiment log

Bu günlük, gerçek denemeleri ve alınan kararları kaydeder. Başarısız veya
yarım kalan denemeler de silinmeden burada tutulur.

## 28 Eylül — Başlangıç / PDF metin çıkarma

- **Soru:** Bu çalışma ortamında verilen PDF'lerden sayfa metnini hangi yerel
  araçla çıkarabiliriz?
- **Kontrol:** `pdftotext`, `mutool`, PyMuPDF, `pdfplumber`, `pypdf` ve spaCy
  kullanılabilir mi diye kontrol edildi.
- **Gözlem:** Başlangıçta bu ortamda PDF araçları kurulu değildi. İnternet
  erişimi onaylandıktan sonra PyMuPDF yerel `.venv` ortamına kuruldu. SpaCy
  henüz kurulmadı.
- **İlk yöntem:** PyMuPDF `page.get_text("text", sort=True)` taban çizgisi
  olarak denendi. Sayfa başına metin ve sayfa numarası korunuyor; okuma sırası
  garantisi vermiyor.
- **Neden bu seçim:** PyMuPDF ödev kısıtlarında izinli. `sort=True` sayfa
  konumuna göre okuma sırasını düzenlemeyi dener; iki sütun ve karmaşık şekiller
  için ayrı gözlem gerekecek.
- **Çıktı:** Dokuz PDF'nin tamamı aynı kodla işlendi: 107 sayfa, toplam 465.733
  karakter ve 57.726 kelime (kelime sayımı Unicode harf/rakam ve tireli
  birleşikleri tek kelime sayan regex ile).
- **İlk gözlem:** Attention sayfa 2'de `sort=True`, başlık ve paragraflar için
  temiz boşluklar üretti. Ancak `1406.1078v3.pdf` sayfa 2'de şekil etiketleri
  metin bloklarına karıştı (`Decoder2`, `xTwhere` gibi). `N16-1024.pdf` sayfa
  2'de `sort=True` sol ve sağ sütun metinlerini satır satır iç içe geçirdi.
- **Kontrollü karşılaştırma:** Aynı üç sayfada `sort=False` ve `sort=True`
  karşılaştırıldı. `sort=False`, Attention sayfa 2'de paragraf metnini korudu
  ama başlık satırını ayrı satırlara böldü. N16 sayfa 2'de `sort=False` sol
  sütundaki paragraf akışını korurken, `sort=True` sağ sütunla satırları
  karıştırdı. Bir ayar tüm düzen türlerinde en iyi değil.
- **Karar:** İki sıralama biçimi de seçenek olarak tutuldu (`sort_blocks` ve
  `--preserve-pdf-order`). Henüz birini evrensel olarak üstün ilan etmiyoruz.
- **Sıradaki deneme:** Sütunlu ve tek sütunlu sayfalarda iki ayarı sistematik
  karşılaştırmak; sonra koordinatlarla önce sütunlara ayırma gibi üçüncü bir
  yöntemin ek karmaşıklığına değip değmediğine karar vermek.
- **Açık sınırlamalar:** Formüller ve tablolar düz metne dönüştürülürken
  bozulabiliyor; başlık/altbilgiler henüz temizlenmedi. Gözlemler şimdilik üç
  sayfaya dayanıyor, dokuz makalenin tamamı için kalite iddiası değil.
