from app import app
from app.mlflow import get_model_link
from app.config import *

from flask import request, json
import requests
from xml.etree import ElementTree
from app.k8s import run_k8s_job

from app.utils import remove_cyrillic
from jsonschema import ValidationError, SchemaError, validate
from app.data_models import (
    TEAMCITY_MODEL_BUILD_START,
    TEAMCITY_MODEL_BUILD_STATUS,
    TEAMCITY_MODEL_PUBLISH_START,
    TEAMCITY_MODEL_PUBLISH_STATUS,
    TEAMCITY_VALIDATION_START,
    TEAMCITY_VALIDATION_STATUS
)

############################################################################
################ BUILD, DEPLOY, TEST, DESTROY stage ########################
############################################################################

@app.route('/teamcity/model/build/start', methods=['POST'])
def start_build():
    request_data = request.get_json()
    try:
        validate(request_data, TEAMCITY_MODEL_BUILD_START)
    except (ValidationError, SchemaError) as e:
        app.logger.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    # TEST 121120 start
    app.logger.info("JSON of /teamcity/model/build/start request from SUM: {}".format(request_data))
    get_mlflow_params = get_model_link(request_data["alias"])
    experiment_id = get_mlflow_params["id"]
    run_id = get_mlflow_params["run"]
    modelname, modelversion = request_data["alias"].replace("_", "-").split("-")
    # bug from TEST 121120 START
    try:
        modelID = request_data["ID"]
    except:
        modelID = request_data["model"]
    # bug from TEST 121120 END
    stage = request_data["stage"]
    messageName = request_data["messageName"]
    processInstanceId = request_data["processInstanceId"]
    xml = """<?xml version='1.0' encoding='utf-8'?>
    <build>
        <buildType id = """ + '"' + stage + '"' + """/>
        <properties>
            <property name = "env.MODELNAME" value = """ + '"' + modelname + '"' + """/>
            <property name = "env.MODELVERSION" value = """ + '"' + modelversion + '"' + """/>
            <property name = "env.MODELID" value = """ + '"' + modelID + '"' + """/>
            <property name = "env.EXPERIMENTID" value = """ + '"' + experiment_id + '"' + """/>
            <property name = "env.RUNID" value = """ + '"' + run_id + '"' + """/>
            <property name = "env.stage" value = """ + '"' + stage + '"' + """/>
            <property name = "env.messageName" value = """ + '"' + messageName + '"' + """/>
            <property name = "env.processInstanceId" value = """ + '"' + processInstanceId + '"' + """/>
        </properties>
    </build >"""
    #return xml
    url = teamcity_base_url_api + '/buildQueue'
    r = requests.post(url, data=xml, headers={'Authorization': 'Basic ' + teamcity_authorization, 'Content-Type': 'application/xml'}) #, verify=False)
    app.logger.debug(f"response is: {r.text}")
    tree = ElementTree.fromstring(r.content)
    xml_to_json = {}
    for element in tree.iter():
        if element.tag == 'property':
            xml_to_json[element.items()[0][1]] = element.items()[1][1]
        else:
            for name, value in element.items():
                xml_to_json[name] = value
    app.logger.debug(f"result JSON is: {json.dumps(xml_to_json)}")
    if r.status_code == 200:
        return app.response_class(
            response=json.dumps({"status": "ok", "message": xml_to_json}),
            status=200,
            mimetype="application/json"
        )
    else:
        return app.response_class(
            response=json.dumps({"status": "error", "message": r.content}),
            status=400,
            mimetype="application/json"
        )


@app.route('/teamcity/model/build/status', methods=['POST'])
def callback_translate_to_camunda():
    request_data = request.get_json()
    try:
        validate(request_data, TEAMCITY_MODEL_BUILD_STATUS)
    except (ValidationError, SchemaError) as e:
        app.logger.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    #return request_data
    try:
        imageSumNexusAddr = request_data["imageSumNexusAddr"]
    except:
        imageSumNexusAddr = "Null"
    json_data = {
        "messageName": request_data["messageName"],
        "processInstanceId": request_data["processInstanceId"],
        "processVariables": {"status": {"value": request_data["status"], "type": "string"},
                             "statusMessage": {"value": request_data["statusMessage"], "type": "string"},
                             "imageSumNexusAddr": {"value": imageSumNexusAddr, "type": "string"}}
    }
    app.logger.info("SUM teamcity callback request")
    app.logger.debug("callback_json is: {}".format(json.dumps(request_data)))
    app.logger.debug("camunda_json is: {}".format(json.dumps(json_data)))
    url = camunda_base_url_api + '/message'

    r = requests.post(url, json=json_data, headers={'Authorization': 'Basic ' + camunda_authorization,  'Content-Type': 'application/json'}) #, verify=False)

    if r.status_code == 204:
        app.logger.info("SUM Camunda request status ok")
        return app.response_class(
            response=json.dumps({"status": "ok", "message": ""}),
            status=200,
            mimetype="application/json"
        )
    else:
        app.logger.error("SUM Camunda request status error, status code is {}".format(r.status_code))
        return app.response_class(
            response=json.dumps({"status": "error", "message": r.content}),
            status=400,
            mimetype="application/json"
        )

############################################################################
################ PUBLISH stage #############################################
############################################################################

@app.route('/teamcity/model/publish/start', methods=['POST'])
def start_publish():
    app.logger.info("TEAMCITY model publish start")
    request_data = request.get_json()
    try:
        validate(request_data, TEAMCITY_MODEL_PUBLISH_START)
    except (ValidationError, SchemaError) as e:
        app.logger.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    messageName = request_data["messageName"]
    processInstanceId = request_data["processInstanceId"]
    imageSumNexusAddr = request_data["imageSumNexusAddr"]
    containerCfgBitbucketAddr = request_data["containerCfgBitbucketAddr"]
    json_body = {
        "messageName": messageName,
        "processInstanceId": processInstanceId,
        "processVariables": {"status": {"value": "ok", "type": "string"},
                             "statusMessage": {"value": "Success", "type": "string"},
                             "imagePimNexusAddr": {"value": imageSumNexusAddr, "type": "string"},
                             "containerCfgPimNexusAddr": {"value": containerCfgBitbucketAddr, "type": "string"}}
    }
    app.logger.info("SUM direct callback request to camunda")
    app.logger.debug("JSON from SUM PUBLISH request: {}".format(json.dumps(request_data)))
    app.logger.debug("camunda_json for STATUS is: {}".format(json.dumps(json_body)))
    url = f'{camunda_base_url_api}/message'
    r = requests.post(url, json=json_body, headers={'Authorization': 'Basic ' + camunda_authorization,
                                                    'Content-Type': 'application/json'})  # , verify=False)
    app.logger.info(f"Camunda status code: {r.status_code}")
    app.logger.debug(f"Camunda text: {r.text}")
    if r.status_code == 204:
        app.logger.info("SUM Camunda request status ok")
        return app.response_class(
            response=json.dumps({"status": "ok"}),
            status=200,
            mimetype="application/json"
        )
    else:
        app.logger.error("SUM Camunda request status error, status code is {}".format(r.status_code))
        return app.response_class(
            response=json.dumps({"status": "error"}),
            status=r.status_code,
            mimetype="application/json"
        )


@app.route('/teamcity/model/publish/status', methods=['POST'])
def callback_publish_to_camunda():
    #
    app.logger.warning("WARNING SUM method teamcity/model/publish/status DEPRECATED")
    request_data = request.get_json()
    try:
        validate(request_data, TEAMCITY_MODEL_PUBLISH_STATUS)
    except (ValidationError, SchemaError) as e:
        app.logger.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    json_body = {
        "messageName": request_data["messageName"],
        "processInstanceId": request_data["processInstanceId"],
        "processVariables": {"status": {"value": request_data["status"], "type": "string"},
                             "statusMessage": {"value": request_data["statusMessage"], "type": "string"},
                             "imagePimNexusAddr": {"value": request_data["imagePimNexusAddr"], "type": "string"},
                             "containerCfgPimNexusAddr": {"value": request_data["containerCfgPimNexusAddr"], "type": "string"}}
        }
    app.logger.info("SUM teamcity PUBLISH callback request")
    app.logger.debug("callback_json is: {}".format(json.dumps(request_data)))
    app.logger.debug("camunda_json is: {}".format(json.dumps(json_body)))
    url = camunda_base_url_api + '/message'

    r = requests.post(url, json=json_body, headers={'Authorization': 'Basic ' + camunda_authorization,  'Content-Type': 'application/json'}) #, verify=False)

    if r.status_code == 204:
        app.logger.info("SUM Camunda request status ok")
        return app.response_class(
            response=json.dumps({"status": "ok", "message": ""}),
            status=200,
            mimetype="application/json"
        )
    else:
        app.logger.error("SUM Camunda request status error, status code is {}".format(r.status_code))
        return app.response_class(
            response=json.dumps({"status": "error", "message": r.content}),
            status=400,
            mimetype="application/json"
        )


############################################################################
################### VALIDATION #############################################
############################################################################


@app.route('/teamcity/validation/start', methods=['POST'])
def start_validation():
    """Старт операции валидации"""
    request_data = request.get_json()
    try:
        validate(request_data, TEAMCITY_VALIDATION_START)
    except (ValidationError, SchemaError) as e:
        app.logger.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    app.logger.debug("Teamcity VALIDATION request data is: {}".format(json.dumps(request_data)))
    # Алиас модели
    model_name, model_version = request_data["alias"].replace("_", "-").split("-")
    # id модели
    # bug from TEST 121120 START
    model_id = request_data.get("ID", "bug_121120")
    # id кубика на диаграмме, т.е. в какой кубик ждет ответа
    message_name = request_data["messageName"]
    # id процеса в рамках которого запущен вызов TeamCity
    process_instance_id = request_data["processInstanceId"]
    # выборка для валидации/название файла xlsx в Bitbucket
    df_pth_val = request_data["df_pth_val"]
    # выборка для разработки/название файла xlsx в Bitbucket
    df_pth_dev = request_data["df_pth_dev"]
    # Конфиг файл валидации, нзвание json файла
    config = request_data["config"]
    # Мастер шкала, json
    scale = request_data["scale"]
    # название итогового отчета
    path_out = request_data["path_out"]

    # Формат транлсируемых в k8s данных
    env = {"MODELNAME": model_name,
           "MODELVERSION": model_version,
           "MODELID": model_id,
           "messageName": message_name,
           "processInstanceId": process_instance_id,
           "DFPTHVAL": df_pth_val,
           "DFPTHDEV": df_pth_dev,
           "PATHOUT": path_out,
           "CONFIG": config,
           "SCALE": scale,
           "MASTERSCALE": scale,
           "callback_url": k8s_callback_url
           }
    app.logger.info("Data to k8s after remove_cyrillic is : {}".format(remove_cyrillic(str(env))))
    try:
        run_k8s_job(env)
        return {"status": "ok"}
    except Exception as e:
        app.logger.error(e)
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=400,
            mimetype="application/json"
        )


@app.route('/teamcity/validation/status', methods=['POST'])
def callback_validation_to_camunda():
    request_data = request.get_json()
    try:
        validate(request_data, TEAMCITY_VALIDATION_STATUS)
    except (ValidationError, SchemaError) as e:
        app.logger.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    app.logger.info("callback_json VALIDATION from TeamCity is: {}".format(request_data))
    request_data = {
        "messageName": request_data["messageName"],
        "processInstanceId": request_data["processInstanceId"],
        "processVariables": {"status": {"value": request_data["status"], "type": "string"},
                             "first_auto_validation_result": {"value": request_data["first_auto_validation_result"], "type": "string"},
                             "first_auto_validation_report": {"value": request_data["first_auto_validation_report"], "type": "string"}}
        }
    app.logger.info("SUM teamcity VALIDATION callback request")
    app.logger.debug("camunda_json VALIDATION is: {}".format(json.dumps(request_data)))
    url = camunda_base_url_api + '/message'

    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + camunda_authorization,  'Content-Type': 'application/json'}) #, verify=False)

    if r.status_code == 204:
        app.logger.info("SUM Camunda request status ok")
        return app.response_class(
            response=json.dumps({"status": "ok", "message": ""}),
            status=200,
            mimetype="application/json"
        )
    else:
        app.logger.error("SUM Camunda request status error, status code is {}".format(r.status_code))
        return app.response_class(
            response=json.dumps({"status": "error", "message": r.content}),
            status=400,
            mimetype="application/json"
        )

