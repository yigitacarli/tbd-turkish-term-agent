# Proje çalışma talimatları

Bu depoda çalışmaya başlayan her insan veya yapay zekâ aşağıdaki sırayı izlemelidir:

1. `README.md` dosyasını oku.
2. `docs/PROJECT_CONTEXT.md` dosyasını tamamen oku.
3. `docs/DECISIONS.md` dosyasını tamamen oku.
4. `docs/ROADMAP.md` ve `docs/AI_HANDOFF.md` dosyalarını oku.
5. `git status --short --branch` ile dalı ve mevcut değişiklikleri kontrol et.

## Kapsam

- Tek etkin paket vardır: `src/terim_etmeni` ve giriş noktası `run.py`.
- Testler `tests/` altındadır.
- Kalıcı ürün/mimari kararını `docs/DECISIONS.md` içine kaydet. Devir durumunu iş
  bitiminde `docs/AI_HANDOFF.md` içinde güncelle.
- Sözlüğe otomatik terim ekleme. Model sözlük üyeliği kararı vermemelidir.
- Doğrulanmamış yeni sözlük son sağlam sözlüğün üzerine yazılmamalıdır.
- Yeni karmaşık filtre ekleme; işlem hattı `PDF → LLM çıkarımı → normalizasyon →
  sözlük arama → eksik terimler` olarak sade kalmalıdır.

## Zorunlu doğrulama

```bash
PYTHONPYCACHEPREFIX=/private/tmp/terim-etmeni-pycache PYTHONPATH=src .venv/bin/python -m compileall -q src tests
PYTHONPYCACHEPREFIX=/private/tmp/terim-etmeni-pycache PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

`.venv` yoksa aynı komutlarda `python3` kullanılabilir. `pytest` varsayma.
