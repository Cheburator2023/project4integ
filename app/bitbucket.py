from app import app
from app import upload
from app.config import *
from app import utils

from flask import request, send_from_directory, abort, make_response, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
import logging
import os
import shutil
import time
import random
import string
import tempfile
import json
from typing import List
from jsonschema import ValidationError, SchemaError, validate
from app.data_models import (
    BITBUCKET_PROJECT_CREATE_SCHEMA,
    BITBUCKET_REPO_CREATE_SCHEMA
)


############### Bitbucket ##################
@app.route('/bitbucket/<string:project_key>')
def get_project_link(project_key):
    url = bitbucket_base_url_api + '/projects/' + project_key
    r = requests.get(url, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        return r.json()["links"]["self"][0]
    else:
        return False

@app.route('/bitbucket/<string:project_key>/<string:repo_slug>')
def get_repo_link(project_key, repo_slug):
    url = bitbucket_base_url_api + '/projects/' + project_key + '/repos/' + repo_slug
    r = requests.get(url, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        return r.json()['links']['self'][0]
    else:
        return False

# get projects list
@app.route('/bitbucket/projects')
def list_projects():
    """Get all projects."""
    url = bitbucket_base_url_api + '/projects'
    # return {'url': url}
    # r = requests.get(url, auth=('admin', 'Yjdsq<bn,frtn1'))
    r = requests.get(url, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'get projects list operation failed!', 'error_info': r.json()}

# get ALL repos list
@app.route('/bitbucket/repos')
def list_all_repos():
    url = bitbucket_base_url_api + '/repos'
    r = requests.get(url, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'get all projects list operation failed!', 'error_info': r.json()}

# get repos list of project
@app.route('/bitbucket/<string:project_key>/repos')
def list_repos(project_key):
    url = bitbucket_base_url_api + '/projects/' + project_key + '/repos'
    r = requests.get(url, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'get projects list operation failed!', 'error_info': r.json()}

# get files list in repo
@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/files')
def list_files_in_repo(project_key, repo_slug):
    # Paged API -- need to add ?limits=10000
    url = bitbucket_base_url_api + '/projects/' + project_key + '/repos/' + repo_slug + '/files?limit=10000'
    r = requests.get(url, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    logging.info(f"List files in repo request by url: {url}")
    logging.debug(f"Result is: {r.status_code} - {json.dumps(r.json())}")
    if r.status_code == 200:
        return {"files_list": r.json()["values"]}
    else:
        return {'message': 'get projects list operation failed!', 'error_info': r.json()}


def prepare_file_link(project_key: str, repo_slug: str, filename: str) -> str:
    return f'{bitbucket_base_url}/projects/{project_key}/repos/{repo_slug}/browse/{filename}?raw'


# get file link
@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/<string:filename>/get-file-link')
def get_file_link(project_key, repo_slug, filename):
    url = prepare_file_link(project_key, repo_slug, filename)
    logging.info(f"Got file link: {url}")
    return {'file_link': url}


# get file
@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/<string:filename>')
def get_file(project_key, repo_slug, filename):
    rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.info("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass
    """Get file -- but on service only."""\
    # http://http://84.201.157.251:7990/projects/TEST3/repos/repo1/raw/mb_manual_x570-aorus-raid.pdf?at=refs%2Fheads%2Fmaster
    url = 'https://' + bitbucket_hostname + ':' + str(bitbucket_port) + '/projects/' + project_key + '/repos/' + \
        repo_slug + '/raw/' + filename # + '?at=refs/heads/master'
    r = requests.get(url, stream=True, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        # with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as f:
        with open(os.path.join(path_to_file, filename), 'wb') as f:
            for chunk in r:
                f.write(chunk)
        res = send_from_directory(path_to_file, filename, as_attachment=True)
        # os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        shutil.rmtree(path_to_file)
        return res
    else:
        return {'message': 'download failed', 'status_code': r.status_code}

# create project
@app.route('/bitbucket/projects/create', methods=['POST'])
def project_create():
    """Create project"""
    url = bitbucket_base_url_api + '/projects'
    request_data = request.get_json()
    try:
        validate(request_data, BITBUCKET_PROJECT_CREATE_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 201:
        # r_json = r.json()
        try:
            url2 = bitbucket_base_url_api + '/projects/' + request_data["key"] + '/permissions/groups?permission=PROJECT_READ&name=dit_group'
            r2 = requests.put(url2, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
        except:
            logging.warning("SUM BITBUCKET -- there is some problem with grant permission for dit_group for this project")
            pass
        return r.json()
    else:
        return {'message': 'Create project failed!', 'error_info': r.json()}

# create repo
@app.route('/bitbucket/<string:project_key>/repos/create', methods=['POST'])
def repo_create(project_key):
    logging.info("SUM BITBUCKET START repo_create operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    """Create project"""
    # Check against http or ssh requests!!!!!!!!!!!!
    url = bitbucket_base_url_api + '/projects/' + project_key + '/repos'
    request_data = request.get_json()
    try:
        validate(request_data, BITBUCKET_REPO_CREATE_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    logging.info(f"request url: {url}")
    logging.info(f"request body: {request_data}")
    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)

    # Repo initialization with one empty file "initial_commit"
    ##repo_slug = request_data["name"]
    # return r.json()
    logging.debug(f"request response body: {r.text}")
    repo_slug = r.json()["slug"]
    rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + rnd_sfx
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.exception("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass
    if os.path.exists(path_to_file):
        os.chdir(path_to_file)
        os.system('touch initial_commit')
        os.system('git init')
        os.system('git add --all')
        os.system('git commit -m "Initial commit"')
        logging.info("SUM BITBUCKET git remote add :")
        os.system('git remote add sshtmporigin' + rnd_sfx + ' ssh://root@' + bitbucket_hostname_ssh + ':' + str(
            bitbucket_port_ssh) +
                  '/' + project_key + '/' + repo_slug + '.git')
        os.system('git push -u sshtmporigin' + rnd_sfx +' master')
        logging.info("SUM BITBUCKET git remote remove sshtmporigin:")
        os.system('git remote remove sshtmporigin' + rnd_sfx)
        logging.info('deleting dir')
        if app.config['UPLOAD_FOLDER']:
            shutil.rmtree(path_to_file)
    logging.info("SUM BITBUCKET END repo_create operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    if r.status_code == 201:
        return r.json()
    else:
        return {'message': 'Create project failed!', 'error_info': r.json()}

def pull_request(project_key, repo_slug, rnd_sfx):
    logging.info("SUM BITBUCKET START pull_request operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    """Create pull_request"""
    # Check against http or ssh requests!!!!!!!!!!!!
    url = bitbucket_base_url_api + '/projects/' + project_key + '/repos/' + repo_slug + '/pull-requests'
    # url = 'ssh://root@' + bitbucket_hostname + ':' + str(bitbucket_port_ssh) + \
    #             '/' + project_key + '/' + repo_slug + '/pull-requests'
    # request_data = request.get_json()
    request_data = {
        "title": "Bitbucket integration service pull request",
        "description": "Bitbucket integration service pull request",
        "fromRef": {
            "id": "refs/heads/tmpbranch" + rnd_sfx
            },
        "toRef": {
            "id": "refs/heads/master"
            }
        }
    logging.debug(json.dumps(request_data))
    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    logging.info(r.content)
    logging.info("SUM BITBUCKET END pull_request operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    if r.status_code == 201:
        return r.json()
    else:
        return {'message': 'Create pull request failed!', 'error_info': r.json()}

# pull_req_id, version_id from return of pull_request()
def merge(project_key, repo_slug, pull_req_id, version_id):
    logging.info("SUM BITBUCKET START merge operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    url = bitbucket_base_url_api + '/projects/' + project_key + '/repos/' + repo_slug + '/pull-requests/' + \
          str(pull_req_id) + '/merge'
    # version_id = bla-bla-bla
    # version_id = 0
    request_data = {"version": version_id}
    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    logging.info("SUM BITBUCKET END merge operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Pull merge request failed!', 'error_info': r.json()}


def replace_file_in_repo(project_key, repo_slug, filename, rnd_sfx=''):
    logging.info("SUM BITBUCKET START replace_file_in_repo operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
    replaced = False
    """Upload file to the repo"""
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.info("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass
    if os.path.exists(path_to_file):
        os.chdir(path_to_file)
        os.system('git init')
        os.rename(filename, filename + '_SUM_TEMPORARY')
        # creating command line alike  'git remote add sshtmporigin ssh://user@84.201.157.251:7999/test3/repo1.git'
        # FYI HTTP link http://84.201.159.230:7990/scm/test1/test1-repo.git')
        os.system('git pull ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                  '/' + project_key + '/' + repo_slug + '.git')
        if os.path.exists(filename):
            os.remove(filename)
            replaced = True
        os.rename(filename + '_SUM_TEMPORARY', filename)
        os.system('git add .')
        if replaced:
            #os.system('git commit -m "Replaced file ' + filename + ' by SUM integration service ' + time.ctime() + '"')
            os.system('git commit -m "Replaced by SUM integration service ' + time.ctime() + '"')
        else:
            os.system('git commit -m "Commit from SUM integration service, replacement file"')
        os.system('git push --set-upstream ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                 '/' + project_key + '/' + repo_slug + '.git master')
        logging.info('deleting dir')
        # check if UPLOAD_FOLDER not set
        if app.config['UPLOAD_FOLDER']:
            shutil.rmtree(path_to_file)
        logging.info("SUM BITBUCKET END replace_file_in_repo operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        return get_file_link(project_key, repo_slug, filename)
    else:
        return {'status': 'error', 'message': path_to_file + ' doesnt exist'}

def upload_new_file_to_repo(project_key, repo_slug, filename, rnd_sfx):
    logging.info("SUM BITBUCKET START upload_new_file_to_repo operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
    logging.info("path_to_file is: {}".format(path_to_file))
    """Upload file to the repo"""
    # generate random suffix
    #rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    logging.info("rnd_sfx in upload_new_file_to_repo is: {}".format(rnd_sfx))
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.warning("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass
    if os.path.exists(path_to_file):
        os.chdir(path_to_file)
        os.system('git init')
        os.system('git add .')
        #os.system('git commit -m "Uploaded file ' + filename + ' by SUM integration service ' + time.ctime() + '"')
        os.system('git commit -m "Uploaded by SUM integration service ' + time.ctime() + '"')
        # creating command line alike  'git remote add sshtmporigin ssh://user@84.201.157.251:7999/test3/repo1.git'
        # FYI HTTP link http://84.201.159.230:7990/scm/test1/test1-repo.git')
        logging.info("SUM BITBUCKET git remote add :")
        os.system('git remote add sshtmporigin' + rnd_sfx + ' ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                '/' + project_key + '/' + repo_slug + '.git')
        logging.info("SUM BITBUCKET first git remote push :")
        os.system('git push sshtmporigin' + rnd_sfx + ' master:refs/heads/tmpbranch' + rnd_sfx)
        ### REST part start
        logging.info("SUM BITBUCKET pull request :")
        pull_req_out = pull_request(project_key, repo_slug, rnd_sfx)
        merge(project_key, repo_slug, pull_req_out["id"], pull_req_out["version"])
        ### REST part end
        logging.info("SUM BITBUCKET second git remote push :")
        os.system('git push sshtmporigin' + rnd_sfx + ' :tmpbranch' + rnd_sfx)
        logging.info("SUM BITBUCKET git remote remove :")
        os.system('git remote remove sshtmporigin' + rnd_sfx)
        # check if UPLOAD_FOLDER not set
        if app.config['UPLOAD_FOLDER']:
            shutil.rmtree(path_to_file)
        logging.info("SUM BITBUCKET END upload_new_file_to_repo operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        return get_file_link(project_key, repo_slug, filename)
    else:
        return {'status': 'error', 'message': path_to_file + ' doesnt exist'}

# upload or replace file in repo
@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/upload_file/<string:filename>', methods=['POST'])
def upload_file(project_key, repo_slug, filename):
    logging.info("SUM BITBUCKET START upload_file operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    # Upload file to the temp dir on integration service:
    upload_state = upload.upload_file(filename, rnd_sfx)
    if not upload_state:
        return upload_state

    if filename in list_files_in_repo(project_key, repo_slug)["files_list"]:
    # if filename in list_files:
        logging.info("REPLACE file {}".format(filename))
        logging.info("SUM BITBUCKET END upload_file operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        return replace_file_in_repo(project_key, repo_slug, filename, rnd_sfx)
    else:
        logging.info("UPLOAD {}".format(filename))
        logging.info("rnd_sfx in upload_file is {}".format(rnd_sfx))
        logging.info("SUM BITBUCKET END upload_file operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        return upload_new_file_to_repo(project_key, repo_slug, filename, rnd_sfx)


@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/upload_multiple_files', methods=['POST'])
def upload_multiple_files(project_key: str, repo_slug: str) -> dict:
    """Endpoint of multiple upload files to bitbucket repository"""
    # получаем общий список файлов в репозитории
    files_set = set()
    files_in_repo = list_files_in_repo(project_key, repo_slug)
    try:
        files_set = set(files_in_repo["files_list"])
    except KeyError:
        logging.warning("KeyError in upload_multiple_files, \"files_list\"")
        abort(make_response(jsonify(files_in_repo), 400))
    new_files = []
    old_files = []
    uploaded = []  # Новые файлы в репозитории
    replaced = []  # Замененные файлы в репозитории
    # Работаем во временном каталоге по адресу app.config['UPLOAD_FOLDER']/случайные_символы -> tmp_dir_name
    # После выхода из данного with, файлы автоматически будут удалены
    with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
        # конструкция для перехода в каталог для обработки файлов
        with utils.working_directory(tmp_dir_name):
            # обход полученных файлов из запроса
            # интересует имя файла (file.filename) и его содержимое (file.stream)
            for file_object in request.files.getlist('file'):
                filename = file_object.filename
                # если файла нет в наборе уже существующих
                if filename not in files_set:
                    new_files.append(filename)
                else:  # если файл уже ранее существовал
                    old_files.append(filename)
                # загружаем/сохраняем все переданные файлы во временный каталог tmp_dir_name
                upload_state = upload.upload_file_stream(filename=filename, file_stream=file_object, path=tmp_dir_name)
                # TODO: нужно подумать как обрабатывать статус загрузки upload_state
            if new_files:
                #  Если появились новые файлы, то осуществляем их загрузку в репозиторий
                uploaded = upload_new_multiple_file_to_repo(project_key, repo_slug, new_files, tmp_dir_name)
            if old_files:
                #  Если изменились старые файлы, то осуществляем их загрузку в репозиторий
                replaced = replace_multiple_file_in_repo(project_key, repo_slug, old_files, tmp_dir_name)
    return {
        "files": {
            "uploaded": [prepare_file_link(project_key, repo_slug, file_name) for file_name in uploaded],
            "replaced": [prepare_file_link(project_key, repo_slug, file_name) for file_name in replaced],
        }
    }


def upload_new_multiple_file_to_repo(project_key: str, repo_slug: str, filename_list: List[str],
                                     path_to_file: str) -> List[str]:
    """multiple upload new files into repository
    :param project_key: prjoect name
    :param repo_slug: repository name
    :param filename_list: File list which need to upload
    :param path_to_file: Temporary dir where files store
    :return: List of processed files
    """
    logging.info(f"SUM BITBUCKET START upload_new_multiple_file_to_repo operation: {utils.get_current_datetime()}")
    logging.info(f"path_to_files is: {path_to_file}")
    if not os.path.exists(path_to_file):
        logging.info(f'{path_to_file} doesnt exist')
        return []
    # генерируем случайную последовательность
    rnd_sfx = utils.get_rnd_sfx()
    # ре/инициализируем локальный репозиторий
    os.system('git init')
    # добавляем в репозиторий файлы
    for file_name in filename_list:
        os.system(f'git add {file_name}')
    # делаем локальный коммит
    os.system(f'git commit -m "Uploaded by SUM integration service {time.ctime()}"')
    logging.info("SUM BITBUCKET git remote add :")
    # добавляем связку для внешнего репозитория
    os.system(f'git remote add sshtmporigin{rnd_sfx} ssh://root@{bitbucket_hostname_ssh}:{bitbucket_port_ssh}/'
              f'{project_key}/{repo_slug}.git')
    logging.info("SUM BITBUCKET first git remote push :")
    # пушим изменения во внешний репозиторий
    os.system(f'git push sshtmporigin{rnd_sfx} master:refs/heads/tmpbranch{rnd_sfx}')
    logging.info("SUM BITBUCKET pull request :")
    # делаем пул запрос
    pull_req_out = pull_request(project_key, repo_slug, rnd_sfx)
    # мерджим изменения
    merge_out = merge(project_key, repo_slug, pull_req_out["id"], pull_req_out["version"])
    logging.info("SUM BITBUCKET second git remote push :")
    # удаляем внешнюю ветку
    os.system(f'git push sshtmporigin{rnd_sfx} :tmpbranch{rnd_sfx}')
    logging.info("SUM BITBUCKET git remote remove :")
    # удаляем свзяку с внешним репозиторием
    os.system(f'git remote remove sshtmporigin{rnd_sfx}')
    # удаляем файлы которые были уже добавлены
    for file_name in filename_list:
        os.remove(os.path.join(path_to_file, file_name))
    logging.info(f"SUM BITBUCKET END upload_new_multiple_file_to_repo operation: {utils.get_current_datetime()}")
    return filename_list


def replace_multiple_file_in_repo(project_key: str, repo_slug: str, filename_list: List[str],
                                  path_to_file: str) -> List[str]:
    """multiple replace files in repository
    :param project_key: project name
    :param repo_slug: repository name
    :param filename_list: File list for update
    :param path_to_file: Temporary dir for uploading
    :return:
    """
    logging.info(f"SUM BITBUCKET START replace_multiple_file_in_repo operation: {utils.get_current_datetime()}")
    if not os.path.exists(path_to_file):
        logging.warning(f'{path_to_file} doesnt exist')
        return []
    # ре/инициализируем локальный репозиторий
    os.system('git init')
    # переименовываем файлы которые хотим заменить
    for filename in filename_list:
        os.rename(filename, f'{filename}_SUM_TEMPORARY')
    git_url = f'ssh://root@{bitbucket_hostname_ssh}:{bitbucket_port_ssh}/{project_key}/{repo_slug}.git'
    # тянем последние изменения
    os.system(f'git pull {git_url}')
    # удаляем файлы которые хотим заменить
    for filename in filename_list:
        if os.path.exists(filename):
            os.remove(filename)
    # обратно переименовываем ранее переименованные файлы
    for filename in filename_list:
        os.rename(f'{filename}_SUM_TEMPORARY', filename)
    # добавляем эти файлы в репозиторий
    for file_name in filename_list:
        os.system(f'git add {file_name}')
    # делаем коммит файлов
    os.system('git commit -m "Commit from SUM integration service, replacement file"')
    # пушим на сервер
    os.system(f'git push --set-upstream {git_url} master')
    logging.info('deleting files')
    for file_name in filename_list:
        # удаляем файлы которые заменяли
        os.remove(os.path.join(path_to_file, file_name))
    logging.info(f"SUM BITBUCKET END replace_file_in_repo operation: {utils.get_current_datetime()}")
    return filename_list


# remove file from bitbucket
@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/<string:filename>/remove')
def remove_file_on_bitbucket(project_key, repo_slug, filename):
    logging.info("SUM BITBUCKET START remove_file_on_bitbucket operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
    replaced = False
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.info("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass
    """Upload file to the repo"""
    if os.path.exists(path_to_file):
        os.chdir(path_to_file)
        os.system('git init')
        # creating command line alike  'git remote add sshtmporigin ssh://user@84.201.157.251:7999/test3/repo1.git'
        # FYI HTTP link http://84.201.159.230:7990/scm/test1/test1-repo.git')
        os.system('git pull ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                  '/' + project_key + '/' + repo_slug + '.git')
        if os.path.exists(filename):
            logging.info('remove file ' + filename)
            os.remove(filename)
        os.system('git add --all ' + filename)
        os.system('git commit -m "Deleting file ' + filename + ' by SUM integration service ' + time.ctime() + '"')
        os.system('git push --set-upstream ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                 '/' + project_key + '/' + repo_slug + '.git master')
        logging.info('deleting dir')
        # check if UPLOAD_FOLDER not set
        if app.config['UPLOAD_FOLDER']:
            shutil.rmtree(path_to_file)
        logging.info("SUM BITBUCKET END remove_file_on_bitbucket operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        return {'message': 'ok'}
    else:
        return {'message': path_to_file + ' unable to create dir for delete operation'}

# create full copy of repo to the new repo

@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/copy_to/<string:project_new_key>/<string:repo_new_slug>')
def create_repo_copy(project_key, repo_slug, project_new_key, repo_new_slug):
    logging.info("SUM BITBUCKET START create_repo_copy operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    path_to_file = app.config['UPLOAD_FOLDER'] + '/repo_copy' + rnd_sfx
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.info("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass
    if os.path.exists(path_to_file):
        os.chdir(path_to_file)
        logging.info("SUM BITBUCKET First clone")
        os.system('git clone ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                  '/' + project_key + '/' + repo_slug + '.git')
        os.system("cp " + repo_new_slug + "/initial_commit ./" + repo_slug + "/")
        os.chdir(path_to_file + '/' + repo_slug)
        os.system('rm -rf .git')
        os.system('git init')
        os.system('git add --all')
        os.system('git commit -m "Initial Commit by SUM integration service ' + time.ctime() + '"')
        os.system('git remote add sshtmporigin' + rnd_sfx + ' ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                         '/' + project_new_key + '/' + repo_new_slug + '.git')
        logging.info("SUM BITBUCKET git push")
        os.system('git push -f sshtmporigin' + rnd_sfx + ' master')
        logging.info("SUM BITBUCKET git remote remove :")
        os.system('git remote remove sshtmporigin' + rnd_sfx)
        logging.info('deleting dir')
        # check if UPLOAD_FOLDER not set
        if app.config['UPLOAD_FOLDER']:
            shutil.rmtree(path_to_file)
        logging.info("SUM BITBUCKET END create_repo_copy operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        return get_repo_link(project_new_key, repo_new_slug)
    else:
        return {'message': path_to_file + ' unable to create dir for delete operation'}


##############################################
# OLD and replaced methods
##############################################

# # upload file to the repository ver2    -- with Upload form
@app.route('/bitbucket/<string:project_key>/<string:repo_slug>/upload_file', methods=['GET', 'POST'])
def upload_new_file_to_bitbucket2(project_key, repo_slug):
    rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
            os.mkdir(path_to_file)
            if os.path.exists(path_to_file):
                file.save(os.path.join(path_to_file, filename))

        #path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
        """Upload file to the repo"""
        if os.path.exists(path_to_file):
            os.chdir(path_to_file)
            os.system('git init')
            os.system('git add .')
            #os.system('git commit -m "Uploaded file ' + filename + ' by SUM integration service ' + time.ctime() + '"')
            os.system('git commit -m "Uploaded by SUM integration service ' + time.ctime() + '"')
            # creating command line alike  'git remote add sshtmporigin ssh://user@84.201.157.251:7999/test3/repo1.git'
            # FYI HTTP link http://84.201.159.230:7990/scm/test1/test1-repo.git')
            logging.info("SUM BITBUCKET git remote add :")
            os.system('git remote add sshtmporigin' + rnd_sfx + ' ssh://root@' + bitbucket_hostname_ssh + ':' + str(bitbucket_port_ssh) +
                    '/' + project_key + '/' + repo_slug + '.git')
            logging.info("SUM BITBUCKET first git remote push :")
            os.system('git push sshtmporigin' + rnd_sfx + ' master:refs/heads/tmpbranch' + rnd_sfx)
            ### REST part start
            logging.info("SUM BITBUCKET pull request :")
            pull_req_out = pull_request(project_key, repo_slug, rnd_sfx)
            # return pull_req_out
            merge_out = merge(project_key, repo_slug, pull_req_out["id"], pull_req_out["version"])
            ### REST part end
            logging.info("SUM BITBUCKET second git remote push :")
            os.system('git push sshtmporigin' + rnd_sfx + ' :tmpbranch' + rnd_sfx)
            logging.info("SUM BITBUCKET git remote remove :")
            os.system('git remote remove sshtmporigin' + rnd_sfx)
            # check if UPLOAD_FOLDER not set
            if app.config['UPLOAD_FOLDER']:
                shutil.rmtree(path_to_file)
            logging.info("SUM BITBUCKET END upload_new_file_to_repo operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
            return get_file_link(project_key, repo_slug, filename)
        else:
            return {'status': 'error', 'message': path_to_file + ' doesnt exist'}

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''
