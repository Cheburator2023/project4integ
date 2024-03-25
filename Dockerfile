FROM nexus-ci.corp.dev.vtb/sumd-docker-lib/ubi8-base-integration:v1.0.2
ENV TZ=Europe/Moscow
RUN groupadd -g 1000 user && useradd -m -d /home/user -s /bin/bash -c "User for Integration service" -u 1000 -g 1000 user

COPY requirements.txt /requirements.txt
ARG PIP_INDEX_URL
RUN pip3 install --no-cache -r /requirements.txt

COPY ./ /app/
RUN chown -R 1000:0 /app && chmod -R g=u /app

RUN mkdir /home/user/tmp && mkdir /home/user/integration
RUN chown -R 1000:0 /home && chmod -R g=u /home
RUN git config --system user.name "SUM" && git config --system user.email "sum@vtb-sum.ru"

USER user
WORKDIR /app

EXPOSE 5777

CMD ["gunicorn", "--workers", "5", "--timeout", "90", "--bind", "0.0.0.0:5777", "--log-level", "DEBUG",  "wsgi:app"]