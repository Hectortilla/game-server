FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir /app
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip && pip install -r requirements.txt

ENV DOCKER=1

# RUN chmod +x /app/entrypoint.sh
# ENTRYPOINT /app/entrypoint.sh

CMD /bin/bash -c 'sleep 5; python -m twisted game-server'
