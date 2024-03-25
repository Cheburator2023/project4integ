# -*- coding: utf-8 -*-
import sys

from app import app
from app.config import *
from app.services import *
from app.error_handling import *

import os, requests, shutil
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

#from requests.packages.urllib3.exceptions import InsecureRequestWarning

#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# hostname_jira = 'task.corp.dev.vtb'
# port_jira = '80'
# base_url_jira = 'http://' + hostname_jira + ':' + str(port_jira) + '/rest/api/latest'
# authorization = 'VFVaX1NVTV9TRVJWSUNFX0pJUkFAcmVnaW9uLnZ0Yi5ydTpaSFRnMTIzaHQ='
# # app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


@app.route('/jira/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(data['user'])
    return 'OK'


def create_issue(project_key, summary, description, issuetype, estimated_time, epic_key=False):
    app.logger.info("SUM JIRA START create_issue operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    url = jira_base_url + '/issue'
    # history creation:
    if epic_key is not False:
        request_data = {
            "fields": {
                "project": {
                    "key": project_key},
                "customfield_10101": epic_key,
                "summary": summary,
                "description": description,
                "issuetype": {"name": issuetype},
                "timetracking": {
                    "originalEstimate": "1m",
                    "remainingEstimate": "1m"},
                "customfield_11600": {"id": "11902"},
                "customfield_16205": [{"key": "54883"}],
                "customfield_16201": [{"key": "55271"}],
                "customfield_15716": [{"key": "54885"}],
                "customfield_15715": [{"key": "54884"}],
                "customfield_16206": [{"key": "54883"}],
                "customfield_11609": "None",
                #"assignee": {"name": "vtb2299999@region.vtb.ru"},
                #"duedate": "2020-08-24"
                "duedate": (datetime.today() + timedelta(estimated_time)).strftime("%Y-%m-%d")
            }
        }
    # epic creation
    else:
        request_data = {
            "fields": {
                "project": {
                    "key": project_key},
                "summary": "SUM " + summary,
                "description": description,
                "issuetype": {"name": issuetype},
                "timetracking": {
                    "originalEstimate": "1m",
                    "remainingEstimate": "1m"},
                "customfield_11600": {"id": "11902"},
                "customfield_10103": "SUM " + summary,
                "customfield_15716": [{"key": "54885"}],
                "customfield_15715":  [{"key" : "54884"}],
                "customfield_16206": [{"key": "54883"}],
                "customfield_11609": "None",
                #"assignee": {"name": "vtb2299999@region.vtb.ru"},
                "duedate": (datetime.today() + timedelta(estimated_time)).strftime("%Y-%m-%d")
            }
        }
    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + jira_authorization})
    app.logger.info("SUM JIRA END create_issue operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    return r


def find_epic_key(project_key, epic_name, story_summary):
    app.logger.info("SUM JIRA START find_epic_key operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    url = jira_base_url + '/search'
    request_data = {
        "jql": "project = " + project_key + " AND summary ~ " + epic_name,
        "startAt": 0,
        "maxResults": 100000,
        "fields": [
            "key",
            "summary",
            "issuetype"
        ]
    }
    r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + jira_authorization})
    epic_key = False
    for i in r.json()["issues"]:
        app.logger.info("We are inside of for loop for story_summary")
        # check for story summary with the same name
        if i["fields"]["summary"] == story_summary:
            app.logger.info("find_epic_key: found issue for this summary")
            return 1
        # remember epic_key
        #if i["fields"]["issuetype"]["name"] == "Epic":
        # check for i["fields"]["issuetype"]["name"] is "Epic" -- but via id. Epic id is 10002
        if i["fields"]["issuetype"]["id"] == "10002":
            epic_key = i["key"]
            app.logger.info("epic_key is :{}".format(epic_key))
    app.logger.info("SUM JIRA END find_epic_key operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    if epic_key:
        return epic_key
    else:
        return 0


# Create story on jira
@app.route('/jira/<string:project_key>/<string:epic_name>/story/create', methods=['POST'])
def create_story(project_key, epic_name):
    app.logger.info("SUM JIRA START create_story operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    if project_key == 'key':
        project_key = "MODELOPS"
    app.logger.info("project_key is {}, epic_name is {}".format(project_key, epic_name))
    if " " in epic_name:
        return {"status": "Wrong Epic name -- there should be no spaces in name"}
    request_data = request.get_json()
    try:
        estimated_time = int(request_data['estimated_time'])
    except:
        estimated_time = 14
    # check if epic not exist
    url = jira_base_url + '/search'
    request_data_jira = {
        "jql": "project = " + project_key + " AND summary ~ " + epic_name,
        "startAt": 0,
        "maxResults": 100000,
        "fields": [
            "key",
            "summary",
            "issuetype"
        ]
    }
    app.logger.info("search request")
    #try:
    r = requests.post(url, json=request_data_jira, headers={'Authorization': 'Basic ' + jira_authorization})
    #    return r
    #except:
    #    return {"status": "Create story request operation failed", "message": "request.post operation failed (Authorization issue?)"}
    if r.status_code == 400:
        return {"status": "Project " + project_key + " does not exist"}
    elif r.status_code == 500:
        return {"status": "Create story request operation failed with status code 500", "message": r.json()}
    elif r.status_code == 200:
        if r.json()["total"] == 0:
            app.logger.info("create epic")
            r = create_issue(project_key, epic_name, request_data["epic_description"], "Epic", estimated_time)
            if r.status_code != 201:
                return {"status": "Create epic " + epic_name + " operation failed", "message": r.json()}
        app.logger.info("find epic_key")
        epic_key = find_epic_key(project_key, epic_name, request_data["story_summary"])
        if epic_key == 0:
            app.logger.info("Epic_key search operation failed")
        elif epic_key == 1:
            return {"status": "Story with the same story summary already exist"}
        app.logger.info("create story")
        try:
            r = create_issue(project_key, request_data["story_summary"], request_data["story_description"] + \
                             '\r\n' + "--------------------" + '\r\n' + "*External links:*" + '\r\n' + '\r\n  '.join(request_data["external_links"]), "Story", estimated_time, epic_key)
        except:
            r = create_issue(project_key, request_data["story_summary"], request_data["story_description"], "Story", estimated_time, epic_key)
        app.logger.info("SUM JIRA END create_story operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
        if r.status_code == 201:
            if 'links' in request_data:
                story_name = r.json()['key']
                files = request_data['links']
                attach_file_result = attach_file_to_issue(story_name, files)
                return {"status": "ok", "message": r.json(), 'file attach status': attach_file_result}
            return {"status": "ok", "message": r.json()}
        else:
            return {"status": "Create story operation failed", "message": r.json()}


# Assign issue to user
@app.route('/jira/issue/<string:issue_key>/assignee', methods=['POST'])
def assign_issue_to_user(issue_key):
    app.logger.info("SUM JIRA START assign_issue_to_user operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    url = jira_base_url + '/issue/' + issue_key + '/assignee'
    # url = 'http://84.201.157.251:8080/rest/api/2/issue/TEST1-7/assignee'
    request_data = request.get_json()
    r = requests.put(url, json=request_data, headers={'Authorization': 'Basic ' + jira_authorization})
    app.logger.info("SUM JIRA END assign_issue_to_user operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    if r.status_code == 204:
        return {'status': 'ok'}
    else:
        return {'message': 'assignee operation failed', "r.text": r.text, "r.status_code": r.status_code}


# Get resolution of the issue
@app.route('/jira/<string:story_key>/resolution')
def issue_resolution(story_key):
    url = jira_base_url + '/issue/' + story_key
    r = requests.get(url, headers={'Authorization': 'Basic ' + jira_authorization})
    if r.status_code == 200:
        try:
            resolution = r.json()['fields']['resolution']['name']
        except:
            resolution = False
        return {'status': "ok", "story_resolution": resolution}
    else:
        return {'status': 'get story resolution operation failed', "r.text": r.json(), "r.status_code": r.status_code}


# Get status of the issue
@app.route('/jira/<string:story_key>/status')
def issue_status(story_key):
    url = jira_base_url + '/issue/' + story_key
    r = requests.get(url, headers={'Authorization': 'Basic ' + jira_authorization})
    if r.status_code == 200:
        try:
            resolution = r.json()['fields']['resolution']['name']
            if resolution == "Выполнено":
                resolution = "Готово"
            elif resolution == "Прекращено":
                resolution = "Отклонено"
        except:
            resolution = False
        return {'status': "ok", "story_status": r.json()['fields']['status']['name'], "story_resolution": resolution}
    else:
        return {'status': 'get story status operation failed', "r.text": r.json(), "r.status_code": r.status_code}


# Get information about issue
@app.route('/jira/<string:story_key>/info')
def issue_info(story_key):
    url = jira_base_url + '/issue/' + story_key
    r = requests.get(url, headers={'Authorization': 'Basic ' + jira_authorization})
    if r.status_code == 200:
        return {'status': "ok", "story_info": r.json()}
    else:
        return {'status': 'get story info operation failed', "r.text": r.json(), "r.status_code": r.status_code}


@logged(is_print_results=False)
def attach_file_to_issue(issue_key: str, files: list):
    """
    request body: [
        {project_key, repo_slug, filename},
        {project_key1, repo_slug1, filename1},
          ...]
    """
    try:
        if len(files) > 1:
            files_contents = {}
            failed_download_files = []
            for idx, file in enumerate(files):
                try:
                    downloaded_file = download_file_from_bitbucket(file)
                except Exception as exp:
                    failed_download_files.append(file)
                    app.logger.exception(f'failed to download file {file} from bitbucket, traceback:')
                    traceback.print_tb(exp.__traceback__)
                    app.logger.debug((type(exp), exp))
                    continue
                #filename = file['filename']
                filename = file.rsplit('/', maxsplit=1)[-1].split('?raw')[0]
                if filename in files_contents.keys():
                    filename = str(idx) + '_' + filename
                files_contents[filename] = downloaded_file['byte_content']
            res = upload_many_files_to_jira_as_zip_archive(issue_key, files_contents)
            if len(failed_download_files) > 0:
                error_message = "\n" + "\n".join((str(i) for i in failed_download_files))
                error_message = "\n" + f'*failed to upload the following files:* {error_message}'
                edit_issue(issue_key, 'description', error_message)
            return {'status': 'ok', 'message': res}
        else:
            file = files[0]
            downloaded_file = download_file_from_bitbucket(file)
            filename = file.rsplit('/', maxsplit=1)[-1].split('?raw')[0]
            if sys.getsizeof(downloaded_file['byte_content']) >= FIVE_MB:
                r = upload_file_to_jira_as_zip_archive(issue_key, filename, downloaded_file['byte_content'])
            else:
                r = upload_file_to_jira(issue_key, filename, downloaded_file['byte_content'])
    except BitbucketFileDoestNotExist as bitbucket_exp:
        app.logger.warning(bitbucket_exp)
        error_message = '\n' + str(bitbucket_exp.url)
        error_message = "\n" + f'*failed to upload the following file:* {error_message}'
        edit_issue(issue_key, 'description', error_message)
        return {"status": bitbucket_exp.get_status(), "message": bitbucket_exp.get_message()}
    except JiraUploadManyFilesAsZipError as jira_many_exp:
        app.logger.warning(jira_many_exp)
        res = upload_many_files_to_jira(issue_key, files_contents)
        return {'status': 'ok', 'message': res}
    except JiraUploadFileAsZipError as jira_single_exp:
        app.logger.warning(jira_single_exp)
        r = upload_file_to_jira(issue_key, filename, downloaded_file['byte_content'])
    except Exception as exp:
        traceback.print_tb(exp.__traceback__)
        app.logger.warning((type(exp), exp))
        return {"status": "Attach file to story operation failed", "message": "Something went wrong"}
    if r.status_code == 200:
        return {"status": "ok", "message": r.json()}
    else:
        try:
            return {"status": "Attach file to story operation failed", "message": r.json()}
        except Exception:
            return {"status": "Attach file to story operation failed", "status_code": r.status_code,
                    "message": r.text}


@app.route('/jira/issue/<string:issue_key>/attach_file', methods=['POST'])
def attach_file_to_issue_controler(issue_key):
    files = request.get_json()
    return attach_file_to_issue(issue_key, files)


############ Deprecated methods ##############

# Get status of the issue
# @app.route('/jira/<string:project_key>/<string:story_summary>/status')
# def issue_status_OLD(project_key, story_summary):
#     url = base_url_jira + '/search'
#     request_data = {
#         "jql": "project = " + project_key + " AND summary ~ '" + issue_summary + "'",
#         "startAt": 0,
#         "maxResults": 100000,
#         "fields": [
#             "key",
#             "summary",
#             "issuetype"
#         ]
#     }
#     r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + authorization})
#     if r.status_code != 200:
#         return {"status": "Story with story_summary " + story_summary + " not found", "message": r.json()}
#     try:
#         issue_key = r.json()["issues"][0]["key"]
#     except:
#         return {"status": "Story with story_summary " + story_summary + " not found", "message": r.json()}
#     url = base_url_jira + '/issue/' + issue_key
#     r = requests.get(url, headers={'Authorization': 'Basic ' + authorization})
#     if r.status_code == 200:
#         return {'status': "ok", "story_status": r.json()['fields']['status']['name']}
#     else:
#         return {'status': 'get story status operation failed', "r.text": r.text, "r.status_code": r.status_code}
#
# # Create issue
# @app.route('/jira/issue/create', methods=['POST'])
# def create_issue_old():
#     url = base_url_jira + '/issue/'
#     request_data = request.get_json()
#     r = requests.post(url, json=request_data, headers={'Authorization': 'Basic ' + authorization})
#     if r.status_code == 201:
#         return r.json()
#     else:
#         return {'message': 'create issue operation failed', "r.text": r.text, "r.status_code": r.status_code}

