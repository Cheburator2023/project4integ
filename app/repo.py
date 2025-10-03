import json
import base64
import requests

from app import app
from flask import request, Response

from app.config import repo_base_url, repo_user, repo_pass

class NotAuthenticatedError(Exception):
    pass

deptMap = {
    "Управление моделирования РБ": "RB",
    "Управление моделирования КИБ и СМБ": "KIB_SMB",
    "Управление перспективных алгоритмов машинного обучения": "ML_ALG",
    "Управление моделирования партнерств и ИТ-процессов": "IT_PROC",
    "Управление процессных и финансовых моделей": "FIN",
}

def send_http_error(message, status_code):
    return app.response_class(
        response=json.dumps({"status": "error", "message": message}),
        status=status_code,
        mimetype="application/json"
    )

def auth() -> str:
    url = repo_base_url + '/get-auth-token'

    creds = f"{repo_user}:{repo_pass}"
    urlsafe_encoded_creds = base64.urlsafe_b64encode(creds.encode('utf-8')).decode('utf-8')

    r = requests.get(url, headers={'Authorization': 'Basic ' + urlsafe_encoded_creds})

    try:
        repo_response = r.json()
    except ValueError:
        repo_response = {}

    if r.status_code == 200 and "access_token" in repo_response:
        return r.json().get("access_token")
    elif r.status_code >= 400 and "error" in repo_response:
        raise NotAuthenticatedError(repo_response.get("error").get("message"))
    raise NotAuthenticatedError("Response is empty or access_token is not set")

@app.route('/repo/create', methods=['POST'])
def create() -> Response:
    url = repo_base_url + '/create-model-repo'

    sum_data = request.get_json()

    if not sum_data.get("general_model_id"):
        return send_http_error("general_model_id is not set", 400)
    if not sum_data.get("model_name"):
        return send_http_error("model_name is not set", 400)
    if not sum_data.get("model_id"):
        return send_http_error("model_id is not set", 400)
    if not sum_data.get("model_desc"):
        return send_http_error("model_desc is not set", 400)
    if not sum_data.get("ds_department"):
        return send_http_error("ds_department is not set", 400)
    if sum_data["ds_department"] not in deptMap:
        return send_http_error(f"ds_department value {sum_data['ds_department']} does not exist in a department map", 400)

    request_data = {
        "model-id": sum_data["general_model_id"],
        "version-name": sum_data["model_name"],
        "version-id": sum_data["model_id"],
        "descr": sum_data["model_desc"],
    }

    try:
        token = auth()
    except NotAuthenticatedError as e:
        app.logger.error(f"Cannot authorize while handling create repo request: {e}")
        return send_http_error(f"Cannot authorize: {e}", 401)

    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-type': 'application/json',
        'CreateOnBehalf': deptMap[sum_data["ds_department"]]
    }

    r = requests.post(url, json=request_data, headers=headers)

    try:
        repo_response = r.json()
        if type(repo_response) is not dict:
            raise ValueError
    except ValueError:
        repo_response = {}

    if r.status_code == 200 and "success" in repo_response:
        return app.response_class(
            response=json.dumps({"model_repo_is_created": repo_response["success"]}),
            status=200,
            mimetype="application/json"
        )
    elif r.status_code >= 400 and "error" in repo_response:
        app.logger.error(f"Error response from Repo service while creating repo: {repo_response.get('error').get('message')}")
        return send_http_error(f"Error response from Repo service: {repo_response.get('error').get('message')}", r.status_code)
    else:
        app.logger.error(f"Incorrect response from Repo service while creating repo. Expected success but was not set: {r.text}")
        return send_http_error("Parameter success was not set in Repo service response", 500)

@app.route('/repo/status', methods=['GET'])
def status() -> Response:
    url = repo_base_url + '/get-repo-by-params'

    general_model_id = request.args.get('general_model_id')
    model_id = request.args.get('model_id')

    if not general_model_id:
        return send_http_error("general_model_id is not set", 400)
    if not model_id:
        return send_http_error("model_id is not set", 400)

    request_data = {
        "model-id": general_model_id,
        "version-id": model_id,
    }

    try:
        token = auth()
    except NotAuthenticatedError as e:
        app.logger.error(f"Cannot authorize while handling status repo request: {e}")
        return send_http_error(f"Cannot authorize: {e}", 401)

    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-type': 'application/json',
    }

    r = requests.post(url, json=request_data, headers=headers)

    try:
        repo_response = r.json()
        if type(repo_response) is not dict:
            raise ValueError
    except ValueError:
        repo_response = {}

    if r.status_code == 200 and "result-list" in repo_response:
        return app.response_class(
            response=json.dumps({"model_repo_is_created": len(repo_response["result-list"]) > 0}),
            status=200,
            mimetype="application/json"
        )
    elif r.status_code >= 400 and "error" in repo_response:
        app.logger.error(f"Error response from Repo service while getting repo status: {repo_response.get('error').get('message')}")
        return send_http_error(f"Error response from Repo service: {repo_response.get('error').get('message')}", r.status_code)
    else:
        app.logger.error(f"Incorrect response from Repo service: expected result-list but was not set: {r.text}")
        return send_http_error("Parameter result-list was not set in Repo service response", 500)
