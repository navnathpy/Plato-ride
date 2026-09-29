FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -m app && mkdir /data && chown app:app /data
COPY app.py .
USER app
ENV DATABASE_PATH=/data/planto.sqlite3
EXPOSE 8788
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8788", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
