<!-- Ishlastish -->
## Contest platformasi uchin Readme.md file


<!-- Deploy qilishdan oldin ishlatish kerak buladigan comandalar -->
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -path "*/migrations/*.py" ! -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
rm -f db.sqlite3

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runbolt --dev
```

# `runbolt` Command Options

`runbolt` management command quyidagi parametrlarni qo'llab-quvvatlaydi.

| Option | Default | Tavsifi |
|--------|---------|---------|
| `--host` | `0.0.0.0` | Server bind address (IP manzil). |
| `--port` | `8000` | Server ishlaydigan port. |
| `--workers` | `1` | Har bir process uchun workerlar soni. |
| `--processes` | `1` | Processlar soni. |
| `--dev` | `off` | Development rejimi va auto-reloadni yoqadi. |
| `--no-admin` | `off` | Django Admin integratsiyasini o'chiradi. |
| `--backlog` | `1024` | Socket listen backlog hajmi. |
| `--keep-alive` | `OS default` | HTTP Keep-Alive timeout qiymati. |

---

## Misollar

### Development rejimi (Auto Reload)

```bash
python manage.py runbolt --dev
```

Kod yoki HTML template o'zgarganda server avtomatik qayta ishga tushadi.

---

### Production rejimi (Scaling)

```bash
python manage.py runbolt --processes 4 --workers 2
```

Bu konfiguratsiya:

- **4 ta process**
- Har bir process uchun **2 ta worker**

Jami **8 ta worker** bilan serverni ishga tushiradi.

---

### Maxsus Host va Port

```bash
python manage.py runbolt --host 127.0.0.1 --port 3000
```

Server `127.0.0.1:3000` manzilida ishga tushadi.

---

## Development Auto Reload

`--dev` parametri Django uslubidagi auto-reload mexanizmidan foydalanadi.

Avtomatik qayta yuklanadigan fayllar:

- Python (`*.py`) fayllari
- HTML template fayllari

Quyidagi fayllar **auto-reload** ni ishga tushirmaydi:

- Log fayllari
- Ma'lumotlar bazasi (`db.sqlite3` va boshqalar)
- Runtime davomida yaratiladigan boshqa fayllar
- Generated artifacts

