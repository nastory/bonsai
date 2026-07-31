FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py

EXPOSE 5000

CMD ["sh", "-c", "flask db upgrade && python seed.py && python run.py"]
