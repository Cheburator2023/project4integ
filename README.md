Как запускать контейнер:
При использовании данного сервиса в докер контейнере то команда запуска будет:

1ый варинт (при использовании env файла), на сервере hdp-devops401lv он лежит по пути: /app/integration/env_integration

docker run -d --name integration -h integration -ti -p 5777:5777 -v /var/run/docker.sock:/var/run/docker.sock -v /app/integration/integration/:/home/user/integration -v /app/integration/tmp:/home/user/tmp --log-driver json-file --env-file /app/integration/env_integration integration:tag_name
2ой вариант изменение непосредственно значений в config.py:

Для этого просто меняем значения в файле config.py к примеру:
меняем bitbucket_hostname = os.environ.get('bitbucket_hostname') на bitbucket_hostname = 'bitbucket.vtb.ru'