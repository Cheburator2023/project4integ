#!/bin/sh
### Скачиваем модель из S3
curl -k --location --request GET $callback_url/s3/$MODELNAME-$MODELVERSION/$MODELNAME-$MODELVERSION/$DFPTHDEV | cat > $DFPTHDEV
curl -k --location --request GET $callback_url/s3/$MODELNAME-$MODELVERSION/$MODELNAME-$MODELVERSION/$DFPTHVAL | cat > $DFPTHVAL
curl -k --location --request GET $callback_url/s3/$MODELNAME-$MODELVERSION/$MODELNAME-$MODELVERSION/$CONFIG | cat > $CONFIG

### Присваиваем переменные
export first_auto_validation_result=first_auto_validation_result.ipynb
export first_auto_validation_report=$PATHOUT
DFPTHDEV=$(pwd)/$DFPTHDEV
CONFIG=$(pwd)/$CONFIG
DFPTHVAL=$(pwd)/$DFPTHVAL
PATHOUT=$(pwd)/$PATHOUT
output_notebook_path=$(pwd)/$first_auto_validation_result
TEMPLATEPATH=/opt/template.xlsx

touch $output_notebook_path
mv /validation-pipeline/report.xlsx $PATHOUT

### Очищаем файл CONFIG от BOM символа если он там есть
sed -i '1s/^\xEF\xBB\xBF//' $CONFIG

### Запускаем валидацию через jupyter
jupyter nbconvert --to notebook --ExecutePreprocessor.kernel_name=python3 --execute /opt/validation.ipynb --output $output_notebook_path

### Загружаем результаты тестирования обратно в S3
curl -k --location --request POST $callback_url/s3/$MODELNAME-$MODELVERSION/$MODELNAME-$MODELVERSION/upload_file/$first_auto_validation_result \
--header 'Content-Type: application/octet-stream' \
--data-binary @/$output_notebook_path

curl -k --location --request POST $callback_url/s3/$MODELNAME-$MODELVERSION/$MODELNAME-$MODELVERSION/upload_file/$first_auto_validation_report \
--header 'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' \
--data-binary @/$PATHOUT


### Кидаем кол бек
export status=ok
export statusMessage=Success
export message=Success

jq -n env | curl -k -H "Content-Type: application/json" -X POST -m 30 -d @- $callback_url/teamcity/validation/status

###
exit 0
