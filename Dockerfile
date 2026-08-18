FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD python3 main.py
