#!/usr/bin/env bash
# ============================================================
#  MARK XXXIX — macOS/Linux launcher
#  Çift tıkla (chmod +x ile) → ilk kurulum + çalıştır
# ============================================================
set -e

# Bulunduğun klasöre geç (çift tıklamada bile)
cd "$(dirname "$0")"

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "[HATA] python3 bulunamadı."
    echo "macOS: 'brew install python@3.12' ya da python.org'dan indirin."
    echo "Linux: 'sudo apt install python3 python3-venv python3-pip' (Debian/Ubuntu)"
    echo ""
    read -p "Çıkmak için Enter'a basın..."
    exit 1
fi

# venv yoksa oluştur
if [ ! -f ".venv/bin/python" ]; then
    echo ""
    echo "[SETUP] Sanal ortam oluşturuluyor..."
    python3 -m venv .venv
fi

# venv'i aktif et
source .venv/bin/activate

# İlk kurulumda bağımlılıkları yükle
if [ ! -f ".venv/installed.flag" ]; then
    echo ""
    echo "[SETUP] Bağımlılıklar yükleniyor (ilk seferde 2-3 dakika)..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch ".venv/installed.flag"
fi

# Çalıştır
echo ""
echo "[RUN] MARK XXXIX başlatılıyor..."
python main.py

# Hata olursa pencere kapanmasın
if [ $? -ne 0 ]; then
    echo ""
    read -p "Bir hata oluştu. Çıkmak için Enter'a basın..."
fi
