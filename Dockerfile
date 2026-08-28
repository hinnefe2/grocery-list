FROM python:3.10-slim

COPY requirements.txt .

RUN pip install -r requirements.txt

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY service.py .
COPY config.py .

CMD exec gunicorn -b 0.0.0.0:${PORT} service:app 
