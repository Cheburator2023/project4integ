from app import app
from app.config import *

from flask import request, json
import requests
import logging
from jsonschema import ValidationError, SchemaError, validate
from app.data_models import (
    MLFLOW_RUNS_CREATE,
    MLFLOW_RUNS_UPDATE,
    MLFLOW_LOG_BATCH
)


############### MLFlow ##################
#get experiments list
@app.route('/mlflow/experiments/list')
def list_experimets():
    """Get all experiments."""
    url = mlflow_base_url + '/experiments/list'
    r = requests.get(url)
    experiments = None
    if r.status_code == 200:
    #    experiments = r.json()['experiments']
        return r.json()
    else:
        return {'message': 'get experiments list operation failed!', 'error_info': r.json()}

#get experiment by id
@app.route('/mlflow/experiments/get/<string:id>')
def get_experimet(id):

    """Get experiment by id"""
    url = mlflow_base_url + '/experiments/get?experiment_id=' + id
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'get experiment by ID operation failed!', 'error_info': r.json()}

#get experiment by name
@app.route('/mlflow/experiments/get_by_name/<string:name>')
def get_experiment_by_name(name):

    """Get experiment by name"""
    url = f"{mlflow_base_url}/experiments/get-by-name?experiment_name={name}"
    logging.info("Getting experiment by name...")
    logging.debug(url)
    r = requests.get(url)
    result = {
        "status_code": r.status_code,
        "message": (
            "Ok." if r.status_code == 200
            else "Get experiment by name operation failed."
        ),
        "response": r.json()
    }
    logging.debug(result["message"])
    logging.debug(json.dumps(result["response"]))
    return result

### get run by ID START ###
#get run by id
@app.route('/mlflow/runs/get/<string:id>')
def get_run(id):

    """Get experiment by id"""
    url = mlflow_base_url + '/runs/get?run_id=' + id
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Get run operation failed', 'error_info': r.json()}
### get run by ID END ###

# get runs by experiment id
@app.route('/mlflow/experiments/<string:experiment_id>/get_runs')
def get_run_by_experiment(experiment_id):
    url = f"{mlflow_base_url}/runs/search"
    request_data = {'experiment_ids': [experiment_id]}
    logging.info("Getting run by experiment id...")
    logging.debug(url)
    logging.debug(f"Request data is: {json.dumps(request_data)}")
    r = requests.post(url, json=request_data)
    result = {
        "status_code": r.status_code,
        "message": (
            "Ok." if r.status_code == 200
            else "Get run by experiment id operation failed."
        ),
        "response": r.json()
    }
    logging.debug(result["message"])
    logging.debug(json.dumps(result["response"]))
    return result

# get experiment id and WINNER run id -- for mlflow address
@app.route('/mlflow/experiments/<string:experiment_name>/get_model_link')
def get_model_link(experiment_name):
    logging.info("Getting model link by experiment name...")
    result = get_experiment_by_name(experiment_name)
    if result["status_code"] == 200:
        experiment_id = result["response"]["experiment"]["experiment_id"]
    else:
        return app.response_class(
            response={"status": "error", "message": result["response"]},
            status=400,
            mimetype="application/json"
        )
    result = get_run_by_experiment(experiment_id)
    if result["status_code"] == 200:
        runs = result["response"]
    else:
        return app.response_class(
            response={"status": "error", "message": result["response"]},
            status=400,
            mimetype="application/json"
        )
    res = []
    for run in runs["runs"]:
        if {"key": "RESULT", "value": "True"} in run["data"]["tags"]:
            res.append({"experiment_name": experiment_name, "id": experiment_id, "run": run["info"]["run_uuid"]})
    if len(res) == 1:
        return res[0]
    elif len(res) == 0:
        return {"status": "Error1", "message": "Tagged as best result run not found"}
    else:
        return {"status": "Error2", "message": "There are more than 1 tagged as best result run", "result": res}

### create run in experiment START ###
@app.route('/mlflow/runs/create', methods=['POST'])
def create_run():

    """Create run in experiment"""
    url = mlflow_base_url + '/runs/create'
    request_data = request.get_json()
    try:
        validate(request_data, MLFLOW_RUNS_CREATE)
    except (ValidationError, SchemaError) as e:
        logging.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    # return {"req_data": request_data}
    #payload = {'experiment_id': experiment_id, 'start_time': int(time.time() * 1000), 'user_id': _get_user_id()}
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Creating run failed!', 'error_info': r.json()}
    # return {"run_id": run_id}

@app.route('/mlflow/runs/log-batch', methods=['POST'])
def log_batch():

    """Log a batch of metrics, params, and tags for a run."""
    url = mlflow_base_url + '/runs/log-batch'
    request_data = request.get_json()
    try:
        validate(request_data, MLFLOW_LOG_BATCH)
    except (ValidationError, SchemaError) as e:
        logging.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    # return {"req_data": request_data}
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        # run_id = r.json()['run']['info']['run_uuid']
        return r.json()
    else:
        return {'message': 'Log batch operation failed!', 'error_info': r.json()}
    # return {"run_id": run_id}

@app.route('/mlflow/runs/update', methods=['POST'])
def update_run():

    """Update run metadata. Here used for run finish"""
    url = mlflow_base_url + '/runs/update'
    request_data = request.get_json()
    try:
        validate(request_data, MLFLOW_RUNS_UPDATE)
    except (ValidationError, SchemaError) as e:
        logging.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    # return {"req_data": request_data}
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Update run operation failed!', 'error_info': r.json()}
    # return {"run_id": run_id}
### create run in experiment END ###

@app.route('/mlflow/runs/set-tag', methods=['POST'])
def set_tag_on_run():

    url = mlflow_base_url + '/runs/set-tag'
    request_data = request.get_json()
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Set tag on run operation failed!', 'error_info': r.json()}

@app.route('/mlflow/runs/delete-tag', methods=['POST'])
def del_tag_on_run():

    url = mlflow_base_url + '/runs/delete-tag'
    request_data = request.get_json()
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Delete tag on run operation failed!', 'error_info': r.json()}


####################################################
############## TEST mlflow2 methods -- FOR TEST ONLY ################
####################################################

#get experiment by name TEST
@app.route('/mlflow/experiments/get_by_name_test/<string:name>')
def get_experiment_by_name_test(name):

    """Get experiment by name"""
    url = mlflow_test_base_url + '/experiments/get-by-name?experiment_name=' + name
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'get experiment by name operation failed!', 'error_info': r.json()}


# get runs by experiment id TEST
@app.route('/mlflow/experiments/<string:experiment_id>/get_runs_test')
def get_run_by_experiment_test(experiment_id):
    url = mlflow_test_base_url + '/runs/search'
    logging.info(experiment_id)
    request_data = {'experiment_ids': [experiment_id]}
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Get run operation failed!', 'error_info': r.json()}


# get experiment id and WINNER run id -- for mlflow address TEST
@app.route('/mlflow/experiments/<string:experiment_name>/get_model_link_test')
def get_model_link_test(experiment_name):
    experiment_id = get_experiment_by_name_test(experiment_name)["experiment"]["experiment_id"]
    runs = get_run_by_experiment_test(experiment_id)
    res = []
    for run in runs["runs"]:
        if {"key": "RESULT", "value": "True"} in run["data"]["tags"]:
            res.append({"experiment_name": experiment_name, "id": experiment_id, "run": run["info"]["run_uuid"]})
    if len(res) == 1:
        return res[0]
    elif len(res) == 0:
        return {"status": "Error1", "message": "Tagged as best result run not found"}
    else:
        return {"status": "Error2", "message": "There are more than 1 tagged as best result run", "result": res}

@app.route('/mlflow/runs/set-tag_test', methods=['POST'])
def set_tag_on_run_test():

    url = mlflow_test_base_url + '/runs/set-tag'
    request_data = request.get_json()
    r = requests.post(url, json=request_data)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Set tag on run operation failed!', 'error_info': r.json()}

