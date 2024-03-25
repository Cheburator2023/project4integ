from app import app
from app import upload
from app.config import *

import os, requests, shutil
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] not in nexus_NOT_ALLOWED_EXTENSIONS

# list of files from repo
@app.route('/nexus/<string:repository>/components')
def get_content_from_repo(repository):
    url = nexus_base_url + '/components?repository=' + repository
    r = requests.get(url, stream=True, headers={'Authorization': 'Basic ' + nexus_authorization}, verify=False)
    if r.status_code == 200:
        return r.json()
    else:
        return {'message': 'Get repo content request failed!'}#, 'error_info': r.json()}

# Get file from repo
@app.route('/nexus/<string:repository>/<string:dir>/<string:filename>')
def get_file_from_repo(repository, dir, filename):
    url = 'https://' + nexus_hostname + ':' + str(nexus_port) + '/repository/' + repository + '/' + dir + '/' + filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    r = requests.get(url, stream=True, headers={'Authorization': 'Basic ' + nexus_authorization}, verify=False)
    if r.status_code == 200:
        with open(filepath, 'wb') as f:
            for chunk in r:
                f.write(chunk)
        res = send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return res
            #{"status": "ok"}
    else:
        return {'message': 'download failed'}

# Upload file to repo via body
@app.route('/nexus/<string:repository>/<string:dir>/upload_file/<string:filename>', methods=['POST'])
def upload_file_to_repo(repository, dir, filename):
    # Upload file to the temp dir on integration service:
    upload_state = upload.upload_file(filename)
    if not upload_state:
        return upload_state
    filepath = os.path.join(app.config['UPLOAD_FOLDER'] + '/' + filename, filename)
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename
    url = nexus_base_url + '/components?repository=' + repository

    os.system('curl -k -X POST "' + url + '" -H  "accept: application/json" -H "Authorization:Basic "' + nexus_authorization + \
                    ' -H  "Content-Type: multipart/form-data" -F "raw.directory=' + dir + '" -F "raw.asset1=@' + \
                  filepath + '" -F "raw.asset1.filename=' + filename + '"')
    if app.config['UPLOAD_FOLDER']:
        shutil.rmtree(path_to_file)
    # return {"message": r.status_code, "filename": filename, "filepath": filepath, "r.text": r.text}
    url = 'https://' + nexus_hostname + ':' + str(nexus_port) + '/repository/' + repository + '/' + dir + '/' + filename
    # return {"message": "ok"}
    return {'file_link': url}

##############################################
# OLD and replaced methods
##############################################

# Upload file to repo via FORM
@app.route('/nexus/repos/<string:repository>/components/upload_file', methods=['GET', 'POST'])
def upload_file_to_repo_form(repository):
    if request.method == 'POST':
        file = request.files['file']
        dir = request.form['dir']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'] + '/' + filename, filename)
            os.mkdir(app.config['UPLOAD_FOLDER'] + '/' + filename)
            if os.path.exists(app.config['UPLOAD_FOLDER'] + '/' + filename):
                file.save(filepath)

            url = nexus_base_url + '/components?repository=' + repository
            # BUG? https://issues.sonatype.org/browse/NEXUS-21946
            # request_data = {
            #     "raw.directory": "dir1",
            #     # "raw.asset1": "@" + filename + ";type=text/plain",
            #     # "raw.asset1": filepath,
            #     "raw.asset1.filename": 'bitbucket.txt'
            # }
            # files = {filename: open(filepath, 'rb')}
            # file_json = {
            #     "raw.directory": "dir1",
            #     "raw.asset1": open(filepath, 'rb'),
            #     "raw.asset1.filename": filename
            # }
            # files = {'bitbucket.txt': open("/home/user/tmp/bitbucket.txt/bitbucket.txt", 'rb')}

            # headers = {'Content-Type': 'multipart/form-data', 'accept': 'application/json',
            #            'Authorization': 'Basic YWRtaW46WWpkc3FZdHJjZWMx'}
            # headers = {'accept': 'application/json',
            #            'Authorization': 'Basic YWRtaW46WWpkc3FZdHJjZWMx'}
            # r = requests.post(url, files=file_json, headers=headers)
            # os.system('curl -u admin:YjdsqYtrcec1 -X POST "' + url + '" -H  "accept: application/json" \
            # -H  "Content-Type: multipart/form-data" -F "raw.directory=' + dir + '" -F "raw.asset1=@' + \
            #           filepath + '" -F "raw.asset1.filename=' + filename + '"')
            os.system('curl -k -X POST "' + url + '" -H  "accept: application/json" -H "Authorization:Basic "' + nexus_authorization + \
                        ' -H  "Content-Type: multipart/form-data" -F "raw.directory=' + dir + '" -F "raw.asset1=@' + \
                      filepath + '" -F "raw.asset1.filename=' + filename + '"')
            if app.config['UPLOAD_FOLDER']:
                shutil.rmtree(path_to_file)
        # return {"message": r.status_code, "filename": filename, "filepath": filepath, "r.text": r.text}
        url = 'https://' + nexus_hostname + ':' + str(nexus_port) + '/repository/' + repository + '/' + dir + '/' + filename
        # return {"message": "ok"}
        return {'file_link': url}

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
      <p><input type=text name=dir>
         <input type=submit value=Upload>
    </form>
    '''

