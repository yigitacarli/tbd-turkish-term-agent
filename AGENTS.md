# Proje çalışma talimatları

Bu depoda çalışmaya başlayan her insan veya yapay zekâ aşağıdaki sırayı izlemelidir:

1. `PROJECT_CONTEXT.md` dosyasını tamamen oku.
2. `DECISIONS.md` dosyasını tamamen oku.
3. `V2_ROADMAP.md` ve `AI_HANDOFF.md` dosyalarını oku.
4. `git status --short --branch` ile dalı ve mevcut değişiklikleri kontrol et.

## Kapsam

- V1 korunmuş çalışan sürümdür: `src/terim_etmeni`, `run.py`, `tests`.
- Etkin geliştirme V2'dir: `src/terim_etmeni_v2`, `run_v2.py`, `tests_v2`.
- Açıkça V1 düzeltmesi istenmedikçe V1 üretim dosyalarını değiştirme.
- Yeni özellikleri V2'ye ekle; çalışan V1 parçalarını geçiş sırasında içe aktarmak
  kopyalamaktan daha güvenlidir.
- Kalıcı ürün/mimari kararını `DECISIONS.md` içine kaydet. Devir durumunu iş
  bitiminde `AI_HANDOFF.md` içinde güncelle.
- Sözlüğe otomatik terim ekleme. Model sözlük üyeliği kararı vermemelidir.
- Doğrulanmamış yeni sözlük son sağlam sözlüğün üzerine yazılmamalıdır.

## Zorunlu doğrulama

```bash
PYTHONPYCACHEPREFIX=/private/tmp/terim-etmeni-pycache PYTHONPATH=src .venv/bin/python -m compileall -q src tests tests_v2
PYTHONPYCACHEPREFIX=/private/tmp/terim-etmeni-pycache PYTHONPATH=src .venv/bin/python -m unittest discover -s tests_v2 -v
PYTHONPYCACHEPREFIX=/private/tmp/terim-etmeni-pycache PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

`.venv` yoksa aynı komutlarda `python3` kullanılabilir. `pytest` varsayma.

