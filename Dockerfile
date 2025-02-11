FROM python:3.9-slim

RUN pip install requests

WORKDIR /app
COPY counter.py .

CMD ["python", "-u", "/app/counter.py"]