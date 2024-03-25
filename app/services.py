import binascii
import json
import os
import random
import sys

import requests
import time
import shutil
import traceback
from typing import List, Tuple

from app import app
from app.config import *
from app.error_handling import *


FIVE_MB = 5 * 1024 * 1024
NINE_AND_HALF_MB = 9.5 * 1024 * 1024


class cd:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        try:
            self.save_cwd = os.getcwd()
        except Exception as exp:
            self.save_cwd = '/home/user/tmp'
            app.logger.warning('handled exception os.getcwd, wrote in save_cwd "/home/user/tmp", traceback:')
            traceback.print_tb(exp.__traceback__)
            app.logger.warning((type(exp), exp))
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.save_cwd)


@logged(is_print_results=False)
#def download_file_from_bitbucket(project_key: str, repo_slug: str, filename: str) -> dict:
def download_file_from_bitbucket(url):
    #url = 'https://' + bitbucket_hostname + ':' + str(bitbucket_port) + '/projects/' + project_key + '/repos/' + \
    #      repo_slug + '/raw/' + filename
    r = requests.get(url, stream=True, headers={'Authorization': 'Basic ' + bitbucket_authorization}, verify=False)
    if r.status_code == 200:
        file_contents = b''
        for chunk in r:
            file_contents += chunk
        return {'byte_content': file_contents, 'meta': r}
    else:
        raise BitbucketFileDoestNotExist.create(url)


@logged(is_print_params=False)
def upload_file_to_jira(issue_key: str, filename: str, byte_content: bytes) -> requests.Response:
    url = jira_base_url + '/issue/' + issue_key + '/attachments'

    boundary = binascii.hexlify(os.urandom(16)).decode('ascii')
    separator = '\r\n'
    prefix = f'--{boundary}{separator}'
    prefix += f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(filename)}" {separator}'
    prefix += separator
    suffix = separator + f'--{boundary}--{separator}'

    prefix = prefix.encode('utf-8')
    suffix = suffix.encode('utf-8')
    data = b''.join([prefix, byte_content, suffix])

    headers = dict()
    headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    headers['X-Atlassian-Token'] = 'no-check'
    headers['Content-Length'] = str(len(data))
    headers['Authorization'] = 'Basic ' + jira_authorization

    r = requests.post(url, data=data, headers=headers)
    return r


@logged(is_print_params=False)
def upload_many_files_to_jira(issue_key: str, files: dict) -> dict:
    res = {}
    for filename, byte_content in files.items():
        try:
            r = upload_file_to_jira(issue_key, filename, byte_content)
            res[filename] = r.json()
        except Exception as exp:
            traceback.print_tb(exp.__traceback__)
            app.logger.warning((type(exp), exp))
            res[filename] = 'an error occured while sending the file'
    return res


@logged
def edit_issue(issue_key: str, field_name: str, data: str, flag='a') -> requests.Response:
    url = jira_base_url + '/issue/' + issue_key

    headers = dict()
    headers['Content-Type'] = 'application/json'
    headers['X-Atlassian-Token'] = 'no-check'
    headers['Authorization'] = 'Basic ' + jira_authorization

    assert flag in ('a', 'r'), f'a value of the flag should be "a", or "r", your value is {flag}'

    if flag == 'a':
        '''append'''
        old_data = requests.get(url, headers=headers).json()['fields']['description']
        old_data = '' if isinstance(old_data, type(None)) else old_data
        new_data = old_data + data
        data = json.dumps({"fields": {field_name: new_data}})
        r = requests.put(url, data=data, headers=headers)
    elif flag == 'r':
        '''rewrite'''
        data = json.dumps({"fields": {field_name: data}})
        r = requests.put(url, data=data, headers=headers)
    return r


@logged
def _make_archive(dir_path: str) -> str:
    with cd(app.config['UPLOAD_FOLDER']):
        shutil.make_archive(os.path.basename(dir_path), 'zip', dir_path)
        zip_path = dir_path + '.zip'
    return zip_path


@logged(is_print_params=False)
def create_zip_archive(files: dict) -> str:
    archive_name = f'archive {time.asctime()}'.replace(' ', '_').replace(':', '_')
    archive_path = app.config['UPLOAD_FOLDER'] + '/' + archive_name
    try:
        os.mkdir(archive_path)
        for filename, byte_content in files.items():
            file_path = os.path.join(archive_path, filename)
            with open(file_path, 'wb') as f:
                f.write(byte_content)
        zip_path = _make_archive(archive_path)
        return zip_path
    except Exception as exp:
        traceback.print_tb(exp.__traceback__)
        app.logger.warning((type(exp), exp))
        raise CreateZipAchiveError
    finally:
        shutil.rmtree(archive_path)


def rendering_descreption(name: str, files: List[str]) -> str:
    res = '\n' + '-' * 20
    res += f'\n*{name} contents:*'
    for file in files:
        res += '\n' + file
    res += '\n' + '-' * 20
    return res


def remove_if_file_exist(path_to_file: str) -> None:
    if os.path.exists(path_to_file):
        os.remove(path_to_file)


@logged(is_print_params=False, is_print_results=False)
def _split_files(files: dict):
    res = []
    too_large_files = {}
    accum_size = 0
    part_of_files = {}
    # part_of_files['id'] = id(part_of_files)

    for file_name, byte_content in files.items():
        file_size = sys.getsizeof(byte_content)
        if accum_size + file_size < NINE_AND_HALF_MB:
            part_of_files[file_name] = byte_content
            accum_size += file_size
        else:
            if part_of_files not in res and len(part_of_files) > 0:
                res.append(part_of_files)
            part_of_files = {}
            # part_of_files['id'] = id(part_of_files)
            accum_size = 0

            if file_size > NINE_AND_HALF_MB:
                too_large_files[file_name] = byte_content
            else:
                part_of_files[file_name] = byte_content
                accum_size += file_size
                res.append(part_of_files)
    else:
        if part_of_files not in res and len(part_of_files) > 0:
            res.append(part_of_files)

    return res, too_large_files


@logged(is_print_params=False, is_print_results=False)
def _try_to_send_too_large_file(issue_key, filename: str, byte_content: bytes):
    try:
        path_to_zip_archive = create_zip_archive({filename: byte_content})
        with open(path_to_zip_archive, 'rb') as f:
            zip_arch_contents = f.read()
        file_size = sys.getsizeof(zip_arch_contents)
        if file_size >= NINE_AND_HALF_MB:
            error_message = f'\nfile {filename} was not attached, because it is too large(should be less than 10 MB), size after compression {file_size}'
            app.logger.info(error_message)
            edit_issue(issue_key, 'description', error_message)
            res = error_message
        else:
            r = upload_file_to_jira(issue_key, filename, zip_arch_contents)
            res = r.json()
    except Exception as exp:
        traceback.print_tb(exp.__traceback__)
        app.logger.warning((type(exp), exp))
        remove_if_file_exist(locals().get('path_to_zip_archive', ''))
    else:
        os.remove(path_to_zip_archive)
        return res


@logged(is_print_params=False, is_print_results=False)
def upload_many_files_to_jira_as_zip_archive(issue_key: str, files: dict, name=''):
    try:
        path_to_zip_archive = create_zip_archive(files)
        with open(path_to_zip_archive, 'rb') as f:
            zip_arch_contents = f.read()
        if sys.getsizeof(zip_arch_contents) >= NINE_AND_HALF_MB:
            os.remove(path_to_zip_archive)
            list_of_files, too_large_files = _split_files(files)
            res = []
            for idx, files in enumerate(list_of_files):
                json_response = upload_many_files_to_jira_as_zip_archive(issue_key, files, f'part_{idx}__')
                res.append(json_response)
            for filename, byte_content in too_large_files.items():
                json_response = _try_to_send_too_large_file(issue_key, filename, byte_content)
                res.append(json_response)
            return res
        zip_name = str(name) + os.path.basename(path_to_zip_archive)
        r = upload_file_to_jira(issue_key, zip_name, zip_arch_contents)
    except Exception as exp:
        traceback.print_tb(exp.__traceback__)
        app.logger.warning((type(exp), exp))
        remove_if_file_exist(locals().get('path_to_zip_archive', ''))
        raise JiraUploadManyFilesAsZipError
    else:
        os.remove(path_to_zip_archive)
        edit_issue(issue_key, 'description', rendering_descreption(zip_name, files.keys()))
        return r.json()


@logged(is_print_params=False)
def upload_file_to_jira_as_zip_archive(issue_key: str, filename: str, byte_content: bytes) -> requests.Response:
    try:
        path_to_zip_archive: str = create_zip_archive({filename: byte_content})
        with open(path_to_zip_archive, 'rb') as f:
            zip_arch_contents = f.read()
        r = upload_file_to_jira(issue_key, f"{filename}.zip", zip_arch_contents)
    except Exception as exp:
        traceback.print_tb(exp.__traceback__)
        app.logger.warning((type(exp), exp))
        remove_if_file_exist(locals().get('path_to_zip_archive', ''))
        raise JiraUploadFileAsZipError
    else:
        os.remove(path_to_zip_archive)
        return r

