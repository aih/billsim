# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9.14-slim-buster
#FROM tiangolo/uvicorn-gunicorn:python3.8

RUN apt-get -y update
RUN apt-get -y install git

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
run python -m pip install -e git+https://github.com/aih/billsim.git#egg=billsim-aih
#RUN apt update && apt upgrade -y
#RUN apt-get install curl -y

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# NOTE: We are dockerize a script, not a API. This runs slightly differently

ADD ./src/billsim/compare.py /
CMD [ "python", "./src/billsim/compare.py" ]
