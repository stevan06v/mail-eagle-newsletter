FROM python:3.12-slim
 
# Install necessary software
RUN apt-get update && \
    apt-get -y install cron
 
RUN pip install --upgrade pip
 
WORKDIR /app
 
COPY ./requirements.txt /app/requirements.txt
 
RUN pip install -r requirements.txt
RUN pip install -U bootstrap-flask
 
COPY . .
 
EXPOSE 8080
 
CMD ["python3", "app.py"]