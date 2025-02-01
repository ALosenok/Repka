# Use the Python slim base image
FROM python:3.10.16-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY model /app/model
COPY Route_Perfect_pipe.py /app
COPY Flask_script.py /app

ENV DB_HOST=db_host
ENV DB_NAME=db_name
ENV DB_USER=db_user
ENV DB_PASS=db_pass
ENV OPEN_ROUTE_KEY = open_route_key

EXPOSE 5000

CMD ["python", "Flask_script.py"]
