FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
EXPOSE 8124
CMD ["python", "server.py"]
