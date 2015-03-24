FROM python:2.7
RUN apt-get install libgdal-dev libgdal1h libgdal1-dev
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt
ADD . /code/