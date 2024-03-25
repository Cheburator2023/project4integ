#### **Инструкция по настройке задачи валидации.**

**Как это работает.**

Метод POST /teamcity/validation/start принимает запрос на валидацию модели.
Для этого он создает k8s job, которая выполнит валидацию.
Код который выполняет k8s job находится в integration/k8s/validation-pipeline/run_validation.sh
k8s скачивает модель из s3, запускает валидацию через jupyter,
и загружает файлы с результатыми валидации обратно в s3 репозиторий модели.
После вызывает метод POST /teamcity/validation/status, куда сообщает что задача завершена.


**Что нужно настроить**

Для работы метода /teamcity/validation/start необходимо сначало подготовить docker image. 
Dockerfile для этого находится в текущей папке, в integration/k8s.

Пример:
docker build -t nexus-ci.corp.dev.vtb/sumd-docker-lib/validation-k8s:2f .

Далее нужно происвоить переменной окружения k8s_image имя docker image который мы собрали.

Пример:
k8s_image: nexus-ci.corp.dev.vtb/sumd-docker-lib/validation-k8s:2f

Также надо определить переменную окружения k8s_callback_url,
 в неё нужно прописать адрес интеграционного сервиса через который будет происходить работа с s3
 и куда будут отравлены результаты работы k8s job.
 
 Пример:
 k8s_callback_url: https://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb

