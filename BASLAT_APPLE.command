#!/bin/zsh
cd "${0:A:h}"

# --- 1) Python yorumlayıcısını bul ---------------------------------------
if [[ -d ".venv" && -f ".venv/bin/python3" ]]; then
  PYTHON_BIN=".venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo ""
  echo "  [!] Python bulunamadı."
  echo ""
  echo "  Yapmanız gereken:"
  echo "    1. https://www.python.org/downloads/ adresinden Python 3.9 veya"
  echo "       üzerini kurun."
  echo "    2. Kurulum bitince bu dosyaya yeniden çift tıklayın."
  echo ""
  echo "  Devam etmek için Enter tuşuna basın..."
  read -r key
  exit 1
fi

# --- 2) Sürüm yeterli mi -------------------------------------------------
if ! "$PYTHON_BIN" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
  echo ""
  echo "  [!] Kurulu Python sürümü bu program için çok eski. En az 3.9 gerekiyor."
  echo ""
  echo "  Devam etmek için Enter tuşuna basın..."
  read -r key
  exit 1
fi

# --- 3) Gerekli kütüphaneler var mı --------------------------------------
if ! "$PYTHON_BIN" -c "import pdfplumber, openpyxl" >/dev/null 2>&1; then
  echo ""
  echo "  [!] Gerekli kütüphaneler kurulu değil (pdfplumber, openpyxl)."
  echo "      Bu tek seferlik bir işlemdir ve internet bağlantısı gerektirir."
  echo ""
  printf "  Şimdi kurulsun mu? (E/H): "
  read -r cevap
  if [[ "$cevap" != "E" && "$cevap" != "e" ]]; then
    echo ""
    echo "  Kurulumu daha sonra şu komutla yapabilirsiniz:"
    echo "      pip install -e ."
    echo ""
    echo "  Devam etmek için Enter tuşuna basın..."
    read -r key
    exit 1
  fi
  echo ""
  echo "  Kuruluyor, lütfen bekleyin..."
  if ! "$PYTHON_BIN" -m pip install -e .; then
    echo ""
    echo "  [!] Kurulum başarısız oldu. İnternet bağlantınızı kontrol edin."
    echo ""
    echo "  Devam etmek için Enter tuşuna basın..."
    read -r key
    exit 1
  fi
fi

"$PYTHON_BIN" run.py "$@"
if [[ $? -ne 0 ]]; then
  echo ""
  echo "  [!] Başlatma başarısız oldu. Hata açıklaması yukarıdadır."
  echo ""
  echo "  Devam etmek için Enter tuşuna basın..."
  read -r key
fi
