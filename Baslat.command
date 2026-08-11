#!/bin/zsh
cd "${0:A:h}"
if [[ -d ".venv" && -f ".venv/bin/python3" ]]; then
  PYTHON_BIN=".venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" run.py "$@"
if [[ $? -ne 0 ]]; then
  echo ""
  echo "Başlatma başarısız oldu. Hata yukarıda gösterilmektedir."
  echo "Devam etmek için Enter tuşuna basın..."
  read key
fi
