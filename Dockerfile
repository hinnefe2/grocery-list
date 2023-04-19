FROM python:3.10-slim

COPY requirements.txt .

RUN pip install -r requirements.txt

# copy the pretrained huggingface tokenizer blobs
ENV APP_HOME /app
WORKDIR $APP_HOME
RUN mkdir model-files

COPY model-files model-files
COPY service.py .

CMD exec gunicorn -b 0.0.0.0:${PORT} service:app 
