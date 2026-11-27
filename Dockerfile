FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DB_PATH=/data/data.db
EXPOSE 8000
# Усередині контейнера слухаємо 0.0.0.0: контейнер це окрема маленька машина.
# Назовні порт видно лише на 127.0.0.1:8000 сервера (compose.yaml), далі nginx і Tailscale.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]
