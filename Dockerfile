FROM python:3.8-slim

RUN pip install --upgrade pip

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

# Install necessary software
RUN apt-get update && \
    apt-get -y install cron

COPY . .

EXPOSE 8080

CMD ["python3", "app.py"]