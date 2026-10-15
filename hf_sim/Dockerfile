FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"
COPY app.py internal_repo.py start.sh ./
COPY secrets ./secrets
EXPOSE 8300 8301
CMD ["sh", "start.sh"]
