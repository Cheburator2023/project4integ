from app import app
import os
import logging
from flask import Flask, request, redirect, url_for, send_from_directory, abort
from werkzeug.utils import secure_filename
from datetime import datetime
from app import utils

NOT_ALLOWED_EXTENSIONS = set(['exe', 'ppk'])

def test():
    return {'message': 'TEST!!!'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] not in NOT_ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file_form():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.mkdir(app.config['UPLOAD_FOLDER'] + '/' + filename)
            if os.path.exists(app.config['UPLOAD_FOLDER'] + '/' + filename):
                file.save(os.path.join(app.config['UPLOAD_FOLDER'] + '/' + filename, filename))
                return {"message": "ok"}
            else:
                return {'message': 'Upload folder' + app.config['UPLOAD_FOLDER'] + ' does not exist'}
        else:
            return {'message': 'Upload operation failed! Not allowed extension or some other problem with file'}

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Upload file to the temp dir on IS:
def upload_file(filename, rnd_sfx=''):
    logging.info("SUM UPLOAD START upload_file operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    #rnd_sfx = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    if "/" in filename:
        # Return 400 BAD REQUEST
        abort(400, "no subdirectories directories allowed")
    path_to_file = app.config['UPLOAD_FOLDER'] + '/' + filename + rnd_sfx
    #os.mkdir(app.config['UPLOAD_FOLDER'] + '/' + filename)
    try:
        os.mkdir(path_to_file)
    except FileExistsError:
        logging.warning("Directory {} already exist. Let's use this dir.".format(path_to_file))
        pass

    if os.path.exists(path_to_file):
        try:
            with open(path_to_file + '/' + filename, "wb") as fp:
                fp.write(request.data)
        except:
            return {'error': 'error in write operation'}
    logging.info("SUM UPLOAD END upload_file operation: {}".format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
    return True


def upload_file_stream(filename, file_stream, path):
    logging.info(f"SUM UPLOAD START upload_file_stream operation: {utils.get_current_datetime()}")
    if "/" in filename:
        abort(400, "no subdirectories directories allowed")
    if os.path.exists(path):
        try:
            file_stream.save(f"{path}/{filename}")
        except Exception as e:
            logging.exception(e)
            return {'error': 'error in write operation'}
    logging.info(f"SUM UPLOAD END upload_file_stream operation: {utils.get_current_datetime()}")
    return True

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5877, debug=True)
