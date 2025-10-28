import json
import logging
from typing import Dict

from flask import request, Response
from jsonschema import ValidationError, SchemaError, validate

from app import app
from app.config import BASE_URL, VERSIONING
from app.data_models import PROJECT_CREATE_S3_SCHEMA, REPO_CREATE_S3_SCHEMA, DOWNLOAD_URL_SCHEMA
from app.downloader import download_file_reader, download_saver
from app.error_handling import ConnectionToMinioError, MinioEmptyFileError, ObjectExistsError, ObjectNotExistsError, \
    NotEmptyRepoError, NotEmptyProjectError, NotSupportedMethodError, VersioningCleanRulesError
from app.minio_client import get_minio_client
from app.redis_cache import Cache, CacheStatus
from app.utils import join_url


@app.route('/s3/<string:project_key>', methods=['GET'])
def get_project_link_s3(project_key: str) -> Response:
    """Сгенерировать ссылку на проект"""
    s3bucket = get_minio_client()
    try:
        s3_object_count = s3bucket.count_objects_by_path(project_key)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )

    if s3_object_count:
        return app.response_class(
            response=json.dumps({'href': f"{BASE_URL}/{project_key}"}),
            status=200,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "error", "message": "noting to show"}),
        status=404,
        mimetype="application/json"
    )


@app.route('/s3/projects', methods=['GET'])
def list_projects_s3() -> Response:
    """Получить список проектов"""
    s3bucket = get_minio_client()
    try:
        projects_names = s3bucket.list_projects_names()
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )
    if projects_names:
        return app.response_class(
            response=json.dumps(projects_names),
            status=200,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "error", "message": "no repos"}),
        status=404,
        mimetype="application/json"
    )


@app.route('/s3/repos', methods=['GET'])
def list_all_repos_s3() -> Response:
    """Получить список репозиториев независимо от проекта"""
    s3bucket = get_minio_client()
    items = []
    try:
        for project_name in s3bucket.list_projects_names():
            repos = s3bucket.list_repo_names(project_name)
            for repo_name in repos:
                items.append(f'{project_name}/{repo_name}')
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )

    if items:
        return app.response_class(
            response=json.dumps(items),
            status=200,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({'status': "error", 'message': 'no repos'}),
        status=400,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/repos', methods=['GET'])
def list_repos_s3(project_key: str) -> Response:
    """Получить список репозиториев в проекте"""
    s3bucket = get_minio_client()
    try:
        items = s3bucket.list_repo_names(project_key)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )
    if items:
        return app.response_class(
            response=json.dumps(items),
            status=200,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps(
            {'status': 'error', 'message': f'no repo in {project_key}'}),
        status=400,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/files', methods=['GET'])
def list_files_in_repo_s3(project_key: str, repo_slug: str) -> Response:
    """Получить список файлов хранимых в репозитории"""
    s3bucket = get_minio_client()
    try:
        objects = s3bucket.list_objects_names(project_key, repo_slug)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )
    if objects:
        return app.response_class(
            response=json.dumps(objects),
            status=200,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({'status': 'error', 'message': f'no files in repo: {project_key}/{repo_slug}'}),
        status=400,
        mimetype="application/json"
    )


# getFileLink for download. Required method
@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>/get-file-link', methods=['GET'])
def get_file_link_s3(project_key: str, repo_slug: str, filename: str) -> Dict:
    """Возвращает ссылку на скачиваемый объект
    """
    s3bucket = get_minio_client()
    file_name = join_url([project_key, repo_slug, filename])
    file_object = s3bucket.stat_object(file_name)
    if not file_object:
        return app.response_class(
            response=json.dumps({'status': 'error', 'message': f'file not exists'}),
            status=404,
            mimetype="application/json"
        )
    file_link = join_url([BASE_URL, project_key, repo_slug, filename])
    return app.response_class(
        response=json.dumps({'file_link': file_link}),
        status=200,
        mimetype="application/json"
    )


# download object. Required method
@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>', methods=['GET'])
def get_file_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Скачивается объект из s3 хранилища
    Required method
    """
    s3bucket = get_minio_client()
    file_name = join_url([project_key, repo_slug, filename])
    try:
        file_object = s3bucket.get_object(file_name)
    except ObjectNotExistsError:
        logging.warning("Can't get object")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Object is not exists"}),
            status=404,
            mimetype="application/json"
        )
    except Exception as e:
        logging.warning("Unexpected error")
        logging.warning(e)
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=404,
            mimetype="application/json"
        )
    return app.response_class(
        response=file_object,
        status=200,
        mimetype="application/octet-stream"
    )


# project create. Required method
@app.route('/s3/projects/create', methods=['POST'])
def project_create_s3() -> Response:
    """Создание проекта
    Required method
    """
    request_data = request.get_json()
    try:
        validate(request_data, PROJECT_CREATE_S3_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.exception(f"Validation error in repo_create_s3: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    project_name = request_data['name']
    s3bucket = get_minio_client()
    try:
        object_info = s3bucket.create_project(project_name)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or create project"}),
            status=504,
            mimetype="application/json"
        )
    except ObjectExistsError:
        logging.exception(f"Project exists")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "project exists"}),
            status=409,
            mimetype="application/json"
        )
    result = {'status': 'ok', 'message': object_info.as_dict()}
    return app.response_class(
        response=json.dumps(result),
        status=200,
        mimetype="application/json"
    )


# repo create. Required method
@app.route('/s3/<string:project_key>/repos/create', methods=['POST'])
def repo_create_s3(project_key: str) -> Response:
    """Создание репозитория
    Required method
    """
    request_data = request.get_json()
    try:
        validate(request_data, REPO_CREATE_S3_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.exception(f"Validation error in repo_create_s3: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    repo_name = request_data.get('name')
    s3bucket = get_minio_client()
    try:
        object_info = s3bucket.create_repo(project_key, repo_name)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or create repo"}),
            status=504,
            mimetype="application/json"
        )
    except ObjectExistsError:
        logging.exception(f"Repo exists")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "repo exists"}),
            status=409,
            mimetype="application/json"
        )
    result = {'status': 'ok', 'message': object_info.as_dict()}
    return app.response_class(
        response=json.dumps(result),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/upload_multiple_files', methods=['POST'])
def upload_multiple_files_s3(project_key: str, repo_slug: str) -> Response:
    """Множественная загрузка файлов в репозиторий
    """
    s3bucket = get_minio_client()
    try:
        old_items = s3bucket.list_objects_names(project_key, repo_slug)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )
    old_items_names = old_items
    file_status = {"replaced": [], "uploaded": [], "error": []}
    if not request.files.getlist('file'):
        return app.response_class(
            response=json.dumps({"status": "error", "message": "File not exists in request"}),
            status=400,
            mimetype="application/json"
        )
    for file_object in request.files.getlist('file'):
        file_name = file_object.filename
        if not file_name:
            logging.info('No filename error')
            file_status['error'].append(file_name)
            continue
        try:
            object_info = s3bucket.upload_file_object(project_key, repo_slug, file_object, file_name)
        except ConnectionToMinioError:
            return app.response_class(
                response=json.dumps({"status": "error", "message": "Can't connect to minio server or upload objects"}),
                status=504,
                mimetype="application/json"
            )
        upload_state = {'status': 'ok', 'message': object_info.as_dict()}
        if upload_state.get('status') == 'error':
            file_status['error'].append(file_name)
            logging.debug(json.dumps(upload_state.get('message')))
            continue
        if file_name in old_items_names:
            file_status['replaced'].append(file_name)
        else:
            file_status['uploaded'].append(file_name)
    return app.response_class(
        response=json.dumps(file_status),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>/remove', methods=['GET'])
def remove_file_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Удаление файла из репозитория
    """
    object_name = f'{project_key}/{repo_slug}/{filename}'
    s3bucket = get_minio_client()
    old_items_names = s3bucket.list_objects_names(project_key, repo_slug)
    if filename not in old_items_names:
        return app.response_class(
            response=json.dumps({"status": "ok", "message": "Object removed"}),
            status=204,
            mimetype="application/json"
        )
    try:
        s3bucket.remove_object(object_name=object_name)
    except Exception as e:
        logging.exception(f"Can't connect to minio server or remove file: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or remove file"}),
            status=504,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Object removed"}),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>/<string:version>', methods=['DELETE'])
def delete_version(project_key: str, repo_slug: str, filename: str, version: str):
    """Удаление определенной версии файла в репозитории"""
    s3bucket = get_minio_client()
    object_path = "/".join([project_key, repo_slug, filename])
    try:
        s3bucket.remove_object(object_path, version)
    except ConnectionToMinioError:
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or upload objects"}),
            status=504,
            mimetype="application/json"
        )
    except NotSupportedMethodError as e:
        logging.exception(f"Method not supported in none versioning mode: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Method not supported in none versioning mode"}),
            status=405,
            mimetype="application/json"
        )
    except Exception as e:
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Object removed"}),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>/versions', methods=['DELETE'])
def remove_old_files_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Удаление устаревших версий файлов в репозитории """
    object_name = f'{project_key}/{repo_slug}'
    s3bucket = get_minio_client()
    try:
        s3bucket.remove_old_versions(object_name, filename)
    except ConnectionToMinioError:
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or upload objects"}),
            status=504,
            mimetype="application/json"
        )
    except NotSupportedMethodError as e:
        logging.exception(f"Method not supported in none versioning mode: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Method not supported in none versioning mode"}),
            status=405,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception(f"Unexpected error: {str(e)}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Object removed"}),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>', methods=['DELETE'])
def delete_object_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Удаление файла из репозитория с помощью метода DELETE"""
    object_name = f'{project_key}/{repo_slug}/{filename}'
    s3bucket = get_minio_client()
    old_items_names = s3bucket.list_objects_names(project_key, repo_slug)
    if filename not in old_items_names:
        return app.response_class(
            response=json.dumps({"status": "ok", "message": "Object removed"}),
            status=204,
            mimetype="application/json"
        )
    try:
        s3bucket.remove_object(object_name=object_name)
    except Exception as e:
        logging.exception(f"Can't connect to minio server or remove file: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or remove file"}),
            status=504,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Object removed"}),
        status=200,
        mimetype="application/json"
    )


# repo copy. Required method
@app.route('/s3/<string:project_key>/<string:repo_slug>/copy_to/<string:project_new_key>/<string:repo_new_slug>',
           methods=['GET'])
def create_repo_copy_s3(project_key: str, repo_slug: str, project_new_key: str, repo_new_slug: str):
    """Создание копии репозитория с новым project_name и новым repo_slug
    Required method
    """
    s3bucket = get_minio_client()
    try:
        objects = s3bucket.list_objects_names(project_key, repo_slug, True)
    except Exception as e:
        logging.exception(f"Can't connect to minio server or remove file: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or remove file"}),
            status=504,
            mimetype="application/json"
        )
    if not objects:
        logging.exception(f"no source project/repo {project_key}/{repo_slug}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": f"no source project/repo {project_key}/{repo_slug}"}),
            status=504,
            mimetype="application/json"
        )

    try:
        new_objects = s3bucket.list_objects_names(project_new_key, repo_new_slug, True)
    except Exception as e:
        logging.exception(f"Can't connect to minio server or remove file: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or remove file"}),
            status=504,
            mimetype="application/json"
        )
    if len(new_objects) > 0:
        logging.exception(f"Destination path {project_new_key}/{repo_new_slug} is not empty")
        return app.response_class(
            response=json.dumps({"status": "error", "message": f"Destination path {project_new_key}/{repo_new_slug} "
                                                               f"is not empty"}),
            status=400,
            mimetype="application/json"
        )
    for object_name in objects:
        try:
            s3bucket.copy_object(f'{project_key}/{repo_slug}/{object_name}',
                                 f'{project_new_key}/{repo_new_slug}/{object_name}')
        except Exception as e:
            logging.warning(e)

    return app.response_class(
        response=json.dumps({'href': f"{BASE_URL}/{project_new_key}"}),
        status=200,
        mimetype="application/json"
    )


# upload object. Required method
@app.route('/s3/<string:project_key>/<string:repo_slug>/upload_file/<string:filename>', methods=['POST'])
def replace_object_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Загрузка объекта в репозиторий
    Required method
    """
    file_object = request
    s3bucket = get_minio_client()
    try:
        # replace object for hitachi s3. Hitachi can't replace object, firstly need to delete.
        _ = s3bucket.upload_file_object(project_key, repo_slug, file_object, filename)
    except ConnectionToMinioError as e:
        logging.exception(f"Can't connect to minio server and upload objects: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server and upload objects"}),
            status=504,
            mimetype="application/json"
        )
    except MinioEmptyFileError as e:
        logging.exception(f"File not exists error: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "File not exists"}),
            status=400,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Unexpected error"}),
            status=400,
            mimetype="application/json"
        )
    file_link = f'{BASE_URL}/{project_key}/{repo_slug}/{filename}'
    upload_state = {'file_link': file_link}
    return app.response_class(
        response=json.dumps(upload_state),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>/versions', methods=['GET'])
def list_object_versions_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Получить список версий объектов
    Required method
    """
    s3bucket = get_minio_client()
    try:
        object_path = '/'.join([project_key, repo_slug])
        objects = s3bucket.get_object_version_list(object_path, filename)
    except ConnectionToMinioError as e:
        logging.exception(f"Can't connect to minio server and upload objects: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server and upload objects"}),
            status=504,
            mimetype="application/json"
        )
    except MinioEmptyFileError as e:
        logging.exception(f"File not exists error: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "File not exists"}),
            status=400,
            mimetype="application/json"
        )
    except NotSupportedMethodError as e:
        logging.exception(f"Method not supported in none versioning mode: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Method not supported in none versioning mode"}),
            status=405,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Unexpected error"}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps(objects),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>', methods=['GET'])
def get_repo_link_s3(project_key: str, repo_slug: str) -> Response:
    """Получить ссылку на репозиторий"""
    s3bucket = get_minio_client()
    object_path = f"{project_key}/{repo_slug}"
    try:
        s3_object_count = s3bucket.count_objects_by_path(object_path)
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server and list objects")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or list objects"}),
            status=504,
            mimetype="application/json"
        )

    if s3_object_count:
        return app.response_class(
            response=json.dumps({'href': f"{BASE_URL}/{object_path}"}),
            status=200,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "error", "message": 'no repos'}),
        status=400,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/rollback/<string:filename>/<string:version>', methods=['GET'])
def rollback(project_key: str, repo_slug: str, filename: str, version: str):
    """Откат файла на определенную версию
    """
    s3bucket = get_minio_client()
    object_path = "/".join([project_key, repo_slug])
    try:
        s3bucket.rollback(object_path, filename, version)
    except ConnectionToMinioError:
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or upload objects"}),
            status=504,
            mimetype="application/json"
        )
    except FileNotFoundError as e:
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=404,
            mimetype="application/json"
        )
    except NotSupportedMethodError as e:
        logging.exception(f"Method not supported in none versioning mode: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Method not supported in none versioning mode"}),
            status=405,
            mimetype="application/json"
        )
    except Exception as e:
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({'href': BASE_URL + "/" + object_path}),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/<string:filename>/<string:version>', methods=['GET'])
def get_file_version_s3(project_key: str, repo_slug: str, filename: str, version: str) -> Response:
    """Скачать файл определенной версии"""
    s3bucket = get_minio_client()
    file_name = '/'.join([project_key, repo_slug, filename])
    try:
        file_object = s3bucket.get_object(file_name, version_id=version)
    except ObjectNotExistsError:
        logging.warning("Can't get object")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Object is not exists"}),
            status=404,
            mimetype="application/json"
        )
    except Exception as e:
        logging.warning("Unexpected error")
        logging.warning(e)
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=404,
            mimetype="application/json"
        )
    return app.response_class(
        response=file_object,
        status=200,
        mimetype="application/octet-stream"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>/versions/<string:filename>', methods=['GET'])
def get_file_version_list_s3(project_key: str, repo_slug: str, filename: str) -> Response:
    """Получить список версий файла"""
    s3bucket = get_minio_client()
    object_path = '/'.join([project_key, repo_slug])
    try:
        version_list = s3bucket.get_object_version_list(object_path, filename)
    except ConnectionToMinioError:
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or upload objects"}),
            status=504,
            mimetype="application/json"
        )
    except NotSupportedMethodError as e:
        logging.exception(f"Method not supported in none versioning mode: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Method not supported in none versioning mode"}),
            status=405,
            mimetype="application/json"
        )
    except Exception as e:
        logging.warning("Unexpected error")
        logging.warning(e)
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=400,
            mimetype="application/json"
        )
    if not version_list:
        return app.response_class(
            response=json.dumps({"status": "error", "message": 'no versions'}),
            status=404,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps(version_list),
        status=200,
        mimetype="application/json"
    )


@app.route("/s3/upload_by_url", methods=['POST'])
def upload_by_url():
    request_data = request.get_json()
    try:
        validate(request_data, DOWNLOAD_URL_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.exception(f"Validation error in upload_by_url: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    url = request_data['url']
    project_name = request_data['project']
    repo_name = request_data['repo']
    object_name = request_data['name']
    # добавить проверку на формат урла и длину наименования

    s3bucket = get_minio_client()
    try:
        reader = download_file_reader(url)
        object_path = '/'.join([project_name, repo_name, object_name])
        download_saver(s3bucket, reader, object_path=object_path)
        # reader.close()  # нужно закрывать если объект не был вычитан полностью
    except ConnectionToMinioError:
        logging.exception(f"Can't connect to minio server")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't connect to minio server or create project"}),
            status=504,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception(e)
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=400,
            mimetype="application/json"
        )

    result = {'status': 'ok', 'message': 'saved'}
    return app.response_class(
        response=json.dumps(result),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>/<string:repo_slug>', methods=['DELETE'])
def delete_repo_s3(project_key: str, repo_slug: str) -> Response:
    """Delete repo from s3"""
    s3bucket = get_minio_client()
    try:
        s3bucket.remove_repo(project_key, repo_slug)
    except NotEmptyRepoError:
        logging.exception(f"Can't remove repo, not empty")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't remove repo, not empty"}),
            status=409,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": f"Unexpected error {str(e)}"}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Repo removed"}),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/<string:project_key>', methods=['DELETE'])
def delete_project_s3(project_key: str) -> Response:
    """Delete project from s3"""
    s3bucket = get_minio_client()
    try:
        s3bucket.remove_project(project_key)
    except NotEmptyProjectError:
        logging.exception(f"Can't remove project, not empty")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Can't remove project, not empty"}),
            status=409,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": f"Unexpected error {str(e)}"}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Project removed"}),
        status=200,
        mimetype="application/json"
    )


@app.route('/s3/clean_versions', methods=['GET'])
def clean_versions_s3() -> Response:
    if VERSIONING.lower() != "native":  # TODO: сделать нормальную проверку
        logging.exception(f"Not supported method if versioning is off")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Not supported method if versioning is off"}),
            status=409,
            mimetype="application/json"
        )

    ttl = 120  # seconds
    cache = Cache("clean_versions", "CLEANING", redis_db=3)
    cache_data = cache.get_by_data()
    if cache_data[1] == CacheStatus.Blocked.value:
        logging.exception(f"Cleaning versions in progress")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Cleaning versions in progress"}),
            status=409,
            mimetype="application/json"
        )
    s3bucket = get_minio_client()
    try:
        cache.save_cache(CacheStatus.Blocked, ttl)
        s3bucket.clean_versions()
    except VersioningCleanRulesError:
        cache.save_cache(CacheStatus.UnexpectedError, ttl)
        logging.exception(f"Versioning clean rules not set or incorrect")
        return app.response_class(
            response=json.dumps({"status": "error", "message": "Versioning clean rules not set or incorrect"}),
            status=409,
            mimetype="application/json"
        )
    except Exception as e:
        cache.save_cache(CacheStatus.UnexpectedError, ttl)
        logging.exception(f"Unexpected error: {str(e)}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": f"Unexpected error {str(e)}"}),
            status=400,
            mimetype="application/json"
        )
    cache.save_cache(CacheStatus.Ok, ttl)
    return app.response_class(
        response=json.dumps({"status": "ok", "message": "Done"}),
        status=200,
        mimetype="application/json"
    )
