import json
import os
import random
import shutil
import string
import tempfile
import unittest
from collections import defaultdict
from hashlib import md5
from io import StringIO
from random import choice

from werkzeug.datastructures import FileStorage

from app import app
from app.config import BASE_URL


def generate_file(filename, size):
    with open('%s' % filename, 'wb') as out:
        out.write(os.urandom(size))


class TestAWSErrors(unittest.TestCase):

    def test_project_create_error(self):
        request_data = {
            "nameO": "MODEL2041-LV",
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(result, {'status': 'error', 'message': "'name' is a required property"})

    def test_repo_create_error(self):
        request_data = {
            "nameO": "model2041-lv",
        }

        with app.test_client() as client:
            response = client.post('/s3/MODEL2041-LV/repos/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(result, {'status': 'error', 'message': "'name' is a required property"})

    def test_upload_file_error(self):
        with app.test_client() as client:
            # data = StringIO("print('Hello world!')\r\nprint('Original file 1')\r\n")
            response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_file/simple_file_name.txt',
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(result, {'status': 'error', 'message': 'File not exists'})

    def test_multiple_upload_files_error(self):
        with app.test_client() as client:
            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']):
                response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_multiple_files',
                                       content_type='multipart/form-data')
                result = json.loads(response.data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(result, {'status': 'error', 'message': 'File not exists in request'})


class TestAWS(unittest.TestCase):
    def test_get_project_link(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'href': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV'})

    def test_get_repo_link(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'href': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV/'
                        'model2041-lv'})

    def test_list_projects(self):
        with app.test_client() as client:
            response = client.get('/s3/projects')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['MODEL2041-LV', 'MODEL2041-LV_copy', 'MODEL2045-LV'])

    def test_list_all_repos(self):
        with app.test_client() as client:
            response = client.get('/s3/repos')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['MODEL2041-LV/model2041-lv', 'MODEL2041-LV_copy/model2041-lv_copy'])

    def test_list_repos(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/repos')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['MODEL2041-LV/model2041-lv'])

    def test_list_files_in_repo(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/files')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['5MB.zip', 'example_file1.txt', 'file1.txt', 'file2.txt', 'file_name2.py'])

    def test_get_file_link(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/5MB.zip/get-file-link')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'file_link': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV/'
                             'model2041-lv/5MB.zip'})

    def test_get_file(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/file1.txt')
            result = response.data
            self.assertEqual(response.status_code, 200)
            self.assertEqual(md5(result).hexdigest(), '4ca9a72bfdd80d89f9eb7eff1e94d978')

    def test_project_create(self):
        request_data = {
            "name": "MODEL2045-LV",
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'status': 'ok',
                                      'message': {'bucket_name': 'myfirstbucket', 'object_name': 'MODEL2045-LV/.empty',
                                                  'version_id': None, 'is_dir': None}})

    def test_repo_create(self):
        request_data = {
            "name": "model2041-lv",
        }

        with app.test_client() as client:
            response = client.post('/s3/MODEL2041-LV/repos/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'message': {'bucket_name': 'myfirstbucket',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/model2041-lv/.empty',
                                                  'version_id': None},
                                      'status': 'ok'})

    def test_upload_file(self):
        with app.test_client() as client:
            data = StringIO("print('Hello world!')\r\nprint('Original file 1')\r\n")
            response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_file/simple_file_name.txt', data=data.read(),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'message': {'bucket_name': 'myfirstbucket',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/model2041-lv/simple_file_name.txt',
                                                  'version_id': None},
                                      'status': 'ok',
                                      'uploaded': True}
                             )

    def test_delete_file(self):
        with app.test_client() as client:
            data = StringIO("print('Hello world!')\r\nprint('Original file 1')\r\n")
            response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_file/simple_file_name.txt', data=data.read(),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            result['uploaded'] = True
            result['replaced'] = True
            self.assertEqual(result, {'message': {'bucket_name': 'myfirstbucket',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/model2041-lv/simple_file_name.txt',
                                                  'version_id': None},
                                      'replaced': True,
                                      'status': 'ok',
                                      'uploaded': True})

            response = client.delete('/s3/MODEL2041-LV/model2041-lv/simple_file_name.txt')
            result = json.loads(response.data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {"status": "ok", "message": "Object removed"})

            response = client.delete('/s3/MODEL2041-LV/model2041-lv/simple_file_name.txt')
            self.assertEqual(response.status_code, 204)

    def test_create_repo_copy(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/copy_to/MODEL2041-LV_copy/model2041-lv_copy')

            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertEqual(result, {
                'href': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV_copy'})

    def test_multiple_upload_files(self):
        with app.test_client() as client:
            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                file_name = '5MB.zip'
                file_path = os.path.join(tmp_dir_name, file_name)
                file_size = 1024 * 1024 * 5  # 5Mb
                generate_file(file_path, file_size)

                output_file1 = open(file_path, 'rb')
                output_file2 = open("test_minio.py", 'rb')

                mock_file1 = FileStorage(
                    stream=output_file1,
                    filename=file_name,
                    content_type="application/octet-stream",
                    content_length=os.stat(file_path).st_size

                )
                mock_file2 = FileStorage(
                    stream=output_file2,
                    filename="file_name2.py",
                    content_type="application/octet-stream",
                    content_length=os.stat("test_minio.py").st_size

                )
                files = [mock_file1, mock_file2]
                response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_multiple_files',
                                       # data=multiple_files,
                                       data={'file': files},
                                       content_type='multipart/form-data')
                result = json.loads(response.data)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(result, {'replaced': ['MODEL2041-LV/model2041-lv/5MB.zip',
                                                       'MODEL2041-LV/model2041-lv/file_name2.py'],
                                          'uploaded': [],
                                          'error': []})


class TestHCP(unittest.TestCase):
    def test_get_project_link(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'href': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV'})

    def test_get_repo_link(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'href': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV/'
                        'model2041-lv'})

    def test_list_projects(self):
        with app.test_client() as client:
            response = client.get('/s3/projects')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['MODEL2011-LV',
                                      'MODEL2041-LV',
                                      'MODEL2041-LV_copy',
                                      'folder1',
                                      'new-bucket-4f980c29',
                                      'new-bucket-d9f48000',
                                      's'])

    def test_list_all_repos(self):
        with app.test_client() as client:
            response = client.get('/s3/repos')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['MODEL2041-LV/model2022-lv',
                                      'MODEL2041-LV/model2041-lv',
                                      'MODEL2041-LV_copy/model2041-lv_copy'])

    def test_list_repos(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/repos')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['MODEL2041-LV/model2022-lv', 'MODEL2041-LV/model2041-lv'])

    def test_list_files_in_repo(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/files')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, ['5MB.zip', 'file_name2.py'])

    def test_get_file_link(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/5MB.zip/get-file-link')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'file_link': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV/'
                             'model2041-lv/5MB.zip'})

    def test_get_file(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/5MB.zip')
            result = response.data
            self.assertEqual(response.status_code, 200)
            self.assertEqual(md5(result).hexdigest(), 'd41d8cd98f00b204e9800998ecf8427e')

    def test_project_create(self):
        request_data = {
            "name": "MODEL2041-LV",
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'message': {'bucket_name': 'sum',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/.empty',
                                                  'version_id': None},
                                      'status': 'ok'})

    def test_repo_create(self):
        request_data = {
            "name": "model2022-lv",
        }

        with app.test_client() as client:
            response = client.post('/s3/MODEL2041-LV/repos/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'message': {'bucket_name': 'sum',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/model2022-lv/.empty',
                                                  'version_id': None},
                                      'status': 'ok'})

    def test_upload_file(self):
        with app.test_client() as client:
            data = StringIO("print('Hello world!')\r\nprint('Original file 1')\r\n")
            response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_file/simple_file_name.txt', data=data.read(),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'message': {'bucket_name': 'sum',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/model2041-lv/simple_file_name.txt',
                                                  'version_id': None},
                                      'status': 'ok',
                                      'uploaded': True})

    def test_delete_file(self):
        with app.test_client() as client:
            data = StringIO("print('Hello world!')\r\nprint('Original file 1')\r\n")
            response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_file/simple_file_name.txt', data=data.read(),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            result['uploaded'] = True
            result['replaced'] = True
            self.assertEqual(result, {'message': {'bucket_name': 'sum',
                                                  'is_dir': None,
                                                  'object_name': 'MODEL2041-LV/model2041-lv/simple_file_name.txt',
                                                  'version_id': None},
                                      'replaced': True,
                                      'status': 'ok',
                                      'uploaded': True})

            response = client.delete('/s3/MODEL2041-LV/model2041-lv/simple_file_name.txt')
            result = json.loads(response.data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {"status": "ok", "message": "Object removed"})

            response = client.delete('/s3/MODEL2041-LV/model2041-lv/simple_file_name.txt')
            self.assertEqual(response.status_code, 204)

    def test_create_repo_copy(self):
        with app.test_client() as client:
            response = client.get('/s3/MODEL2041-LV/model2041-lv/copy_to/MODEL2041-LV_copy/model2041-lv_copy')

            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertEqual(result, {
                'href': 'http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3/MODEL2041-LV_copy'})

    def test_multiple_upload_files(self):
        with app.test_client() as client:
            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                file_name = '5MB.zip'
                file_path = os.path.join(tmp_dir_name, file_name)
                file_size = 1024 * 1024 * 5  # 5Mb
                generate_file(file_path, file_size)

                output_file1 = open(file_path, 'rb')
                output_file2 = open("test_minio.py", 'rb')

                mock_file1 = FileStorage(
                    stream=output_file1,
                    filename=file_name,
                    content_type="application/octet-stream",
                    content_length=os.stat(file_path).st_size

                )
                mock_file2 = FileStorage(
                    stream=output_file2,
                    filename="file_name2.py",
                    content_type="application/octet-stream",
                    content_length=os.stat("test_minio.py").st_size

                )
                files = [mock_file1, mock_file2]
                response = client.post('/s3/MODEL2041-LV/model2041-lv/upload_multiple_files',
                                       # data=multiple_files,
                                       data={'file': files},
                                       content_type='multipart/form-data')
                result = json.loads(response.data)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(result, {'replaced': ['MODEL2041-LV/model2041-lv/5MB.zip',
                                                       'MODEL2041-LV/model2041-lv/file_name2.py'],
                                          'uploaded': [],
                                          'error': []})

    def test_rollback(self):
        with app.test_client() as client:
            response = client.get("/s3/MODEL2041-LV/model2041-lv/rollback/file_name2.py/20220722145933114099")
            print(response.status_code)
            print(response.data)

    def test_get_version_object(self):
        with app.test_client() as client:
            response = client.get("/s3/MODEL2041-LV/model2041-lv/file_name2(3).py/20220726113426892780")
            print(response.status_code)
            print(response.data)

    def test_upload_url(self):
        request_data = {
            'url': 'https://file-examples.com/storage/fe8bd9dfd063066d39cfd5a/2017/02/zip_10MB.zip',
            'project': 'project1',
            'repo': 'repo1',
            'name': 'file_object.inf'
        }
        with app.test_client() as client:
            response = client.post("/s3/upload_by_url", data=json.dumps(request_data), content_type='application/json')
            print(response)

    def test_delete_repo(self):
        with app.test_client() as client:
            response = client.delete('/s3/project1/repo1')
            result = json.loads(response.data)
            print(response.status_code)
            print(result)

    def test_delete_project(self):
        with app.test_client() as client:
            response = client.delete('/s3/project1')
            result = json.loads(response.data)
            print(response.status_code)
            print(result)


def random_name(length: int = 7) -> str:
    return "".join(random.choices(string.ascii_uppercase, k=1) +
                   random.choices(string.ascii_uppercase + string.digits, k=length - 1))


class TestMinio(unittest.TestCase):
    def setUp(self) -> None:
        self.bucket_name = 'bucketname'

    def test_project_create(self):
        project_name = f"MODEL_{random_name()}"
        request_data = {
            "name": project_name,
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            del result['message']['version_id']
            self.assertEqual(result, {'message': {'bucket_name': self.bucket_name,
                                                  'is_dir': None,
                                                  'object_name': f'{project_name}/.empty',
                                                  # 'version_id': None,
                                                  },
                                      'status': 'ok'})

    def test_repo_create(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')

            response = client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            del result['message']['version_id']
            self.assertEqual(result, {'message': {'bucket_name': self.bucket_name,
                                                  'is_dir': None,
                                                  'object_name': f'{project_name}/{model_name}/.empty',
                                                  # 'version_id': None,
                                                  },
                                      'status': 'ok'})

    def test_get_project_link(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project), content_type='application/json')
            response = client.get(f'/s3/{project_name}')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'href': f'{BASE_URL}/{project_name}'})

    def test_get_repo_link(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')

            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            response = client.get(f'/s3/{project_name}/{model_name}')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {'href': f'{BASE_URL}/{project_name}/{model_name}'})

    def test_list_projects(self):
        project_name_dict = {}

        for i in range(5):
            project_name = f"MODEL_{random_name()}"
            request_data_project = {
                "name": project_name,
            }
            project_name_dict[project_name] = request_data_project

        with app.test_client() as client:
            for project in project_name_dict:
                client.post('/s3/projects/create', data=json.dumps(project_name_dict[project]),
                            content_type='application/json')
            response = client.get('/s3/projects')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)

            for project_name_result in project_name_dict.keys():
                self.assertIn(project_name_result, result)

    def test_list_all_repos(self):
        project_name_dict = dict()
        expected_result = set()
        repo_name_dict = defaultdict(list)
        for i in range(5):
            project_name = f"MODEL_{random_name()}"
            request_data_project = {
                "name": project_name,
            }
            project_name_dict[project_name] = request_data_project
            for j in range(5):
                model_name = f"model_{random_name()}"
                request_data_repo = {
                    "name": model_name
                }
                repo_name_dict[project_name].append(request_data_repo)
                expected_result.add(f"{project_name}/{model_name}")

        with app.test_client() as client:
            for project in project_name_dict:
                client.post('/s3/projects/create', data=json.dumps(project_name_dict[project]),
                            content_type='application/json')
                for repo in repo_name_dict[project]:
                    client.post(f'/s3/{project}/repos/create', data=json.dumps(repo),
                                content_type='application/json')

            response = client.get('/s3/repos')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            for full_repo_name in expected_result:
                self.assertIn(full_repo_name, result)

    def test_list_repos(self):
        project_name = f"MODEL_{random_name()}"
        repo_name_dict = {}
        expected_result = set()
        request_data_project = {
            "name": project_name,
        }
        for j in range(5):
            model_name = f"model_{random_name()}"
            request_data_repo = {
                "name": model_name
            }
            repo_name_dict[model_name] = request_data_repo
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project), content_type='application/json')
            for repo in repo_name_dict:
                client.post(f'/s3/{project_name}/repos/create', data=json.dumps(repo_name_dict[repo]),
                            content_type='application/json')
                expected_result.add(repo)

            response = client.get(f'/s3/{project_name}/repos')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            for full_repo_name in expected_result:
                self.assertIn(full_repo_name, result)

    def test_upload_file(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }

        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                for size in range(1, 11):
                    file_name = f'{size}MB.zip'
                    file_path = os.path.join(tmp_dir_name, file_name)
                    file_size = 1024 * 1024 * size  # 5Mb
                    generate_file(file_path, file_size)
                    output_file = open(file_path, 'rb')
                    response = client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}',
                                           data=output_file.read(),
                                           content_type='application/octet-stream')
                    output_file.close()
                    os.remove(file_path)
                    result = json.loads(response.data)

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(result, {'file_link': f'{BASE_URL}/{project_name}/{model_name}/{file_name}'})

    def test_list_files_in_repo(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }

        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')
            file_names = []
            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                for size in range(1, 11):
                    file_name = f'{size}MB.zip'
                    file_names.append(file_name)
                    file_path = os.path.join(tmp_dir_name, file_name)
                    file_size = 1024 * 1024 * size  # 5Mb
                    generate_file(file_path, file_size)
                    output_file = open(file_path, 'rb')
                    client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}',
                                data=output_file.read(),
                                content_type='application/octet-stream')
                    output_file.close()
                    os.remove(file_path)

            response = client.get(f'/s3/{project_name}/{model_name}/files')
            result = json.loads(response.data)
            result.sort()
            file_names.sort()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, file_names)

    def test_get_file_link(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }

        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            size = 5
            file_name = f'{size}MB.zip'
            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                file_path = os.path.join(tmp_dir_name, file_name)
                file_size = 1024 * 1024 * size  # 5Mb
                generate_file(file_path, file_size)
                output_file = open(file_path, 'rb')
                client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}',
                            data=output_file.read(),
                            content_type='application/octet-stream')
                output_file.close()
                os.remove(file_path)

            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/get-file-link')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(result, {
                'file_link': f'{BASE_URL}/{project_name}/{model_name}/{file_name}'})

    def test_get_file(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        file_name = 'simple_file_name.txt'
        file_content = "print('Hello world!')\r\nprint('Original file 1')\r\n"
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            data = StringIO(file_content)
            client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                        content_type='application/json')

            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}')
            result = response.data
            self.assertEqual(response.status_code, 200)
            self.assertEqual(md5(result).hexdigest(), md5(file_content.encode('utf-8')).hexdigest())

    def test_delete_file(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        file_name = 'simple_file_name.txt'
        file_content = "print('Hello world!')\r\nprint('Original file 1')\r\n"
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            data = StringIO(file_content)
            client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                        content_type='application/json')

            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/remove')
            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertEqual(result, {'status': 'ok', 'message': 'Object removed'})

            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}')
            self.assertEqual(response.status_code, 404)
            result = json.loads(response.data)
            self.assertEqual(result, {"status": "error", "message": "Object is not exists"})

            data = StringIO(file_content)
            client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                        content_type='application/json')

            response = client.delete(f'/s3/{project_name}/{model_name}/{file_name}')
            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertEqual(result, {'status': 'ok', 'message': 'Object removed'})

            response = client.delete(f'/s3/{project_name}/{model_name}/{file_name}')
            self.assertEqual(response.status_code, 204)
            result = response.data
            self.assertEqual(result, b'')

    def test_create_repo_copy(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            response = client.get(f'/s3/{project_name}/{model_name}/copy_to/{project_name}_copy/{model_name}_copy')

            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertEqual(result, {
                'href': f'{BASE_URL}/{project_name}_copy'})

    def test_multiple_upload_files(self):

        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')

            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                file_name1 = '5MB.zip'
                file_path1 = os.path.join(tmp_dir_name, file_name1)
                file_path1 = os.path.normpath(file_path1)
                file_size = 1024 * 1024 * 5  # 5Mb
                generate_file(file_path1, file_size)
                output_file1 = open(file_path1, 'rb')

                file_name2 = "1MB.zip"
                file_path2 = os.path.join(tmp_dir_name, file_name2)
                file_path2 = os.path.normpath(file_path2)
                file_size = 1024 * 1024 * 1
                generate_file(file_path2, file_size)
                output_file2 = open(file_path2, 'rb')

                mock_file1 = FileStorage(
                    stream=output_file1,
                    filename=file_name1,
                    content_type="application/octet-stream",
                    content_length=os.stat(file_path1).st_size

                )
                mock_file2 = FileStorage(
                    stream=output_file2,
                    filename=file_name2,
                    content_type="application/octet-stream",
                    content_length=os.stat(file_path2).st_size

                )
                files = [mock_file1, mock_file2]
                response = client.post(f'/s3/{project_name}/{model_name}/upload_multiple_files',
                                       data={'file': files},
                                       content_type='multipart/form-data')
                output_file1.close()
                output_file2.close()
                os.remove(file_path1)
                os.remove(file_path2)
                shutil.rmtree(tmp_dir_name)
                result = json.loads(response.data)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(result, {'uploaded': [f'{file_name1}',
                                                       f'{file_name2}'],
                                          'replaced': [],
                                          'error': []})

    def test_empty_project_create(self):
        project_name = ""
        request_data = {
            "name": project_name,
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            self.assertEqual(response.status_code, 400)

    def test_empty_repo_create(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = ""
        request_data_repo = {
            "name": model_name
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')

            response = client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                                   content_type='application/json')
            self.assertEqual(response.status_code, 400)

    def test_copy_name_project_create(self):
        project_name = f"MODEL_{random_name()}"
        request_data = {
            "name": project_name,
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            del result['message']['version_id']
            self.assertEqual(result, {'message': {'bucket_name': self.bucket_name,
                                                  'is_dir': None,
                                                  'object_name': f'{project_name}/.empty',
                                                  # 'version_id': None,
                                                  },
                                      'status': 'ok'})
            print(f"{project_name}")
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 409)
            self.assertEqual(result, {'status': 'error', 'message': 'project exists'})

    def test_list_object_versions(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        file_name = 'filename1.txt'
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')
            for i in range(10):
                file_content = f"Original file with content\r\nVersion {i}\r\n"
                data = StringIO(file_content)
                client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                            content_type='application/json')
        with app.test_client() as client:
            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/versions')
            result = json.loads(response.data)
            print(result)
            self.assertEqual(response.status_code, 200)

    def test_rollback_object_versions(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        file_name = 'filename1.txt'
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')
            for i in range(2):
                file_content = f"Original file with content\r\nVersion {i}\r\n"
                data = StringIO(file_content)
                client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                            content_type='application/json')
        with app.test_client() as client:
            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/versions')
            result = json.loads(response.data)
            for i in result:
                version_id = i["version_id"]
                response = client.get(f'/s3/{project_name}/{model_name}/rollback/{file_name}/{version_id}')
                self.assertEqual(response.status_code, 200)
                break

    def test_remove_old_versions(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        file_name = 'filename1.txt'
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')
            for i in range(10):
                file_content = f"Original file with content\r\nVersion {i}\r\n"
                data = StringIO(file_content)
                client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                            content_type='application/json')
        with app.test_client() as client:
            response = client.delete(f'/s3/{project_name}/{model_name}/{file_name}/versions')
            result = json.loads(response.data)
            print(result)

    def test_project_remove(self):
        project_name = f"MODEL_{random_name()}"
        request_data = {
            "name": project_name,
        }
        with app.test_client() as client:
            response = client.post('/s3/projects/create', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            del result['message']['version_id']
            self.assertEqual(200, response.status_code)
            self.assertEqual({'message': {'bucket_name': self.bucket_name,
                                          'is_dir': None,
                                          'object_name': f'{project_name}/.empty',
                                          # 'version_id': None
                                          },
                              'status': 'ok'}, result)

            response = client.delete(f'/s3/{project_name}', content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            self.assertEqual({"status": "ok", "message": "Project removed"}, result)

    def test_repo_remove(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')

            response = client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            del result['message']['version_id']
            self.assertEqual({'message': {'bucket_name': self.bucket_name,
                                          'is_dir': None,
                                          'object_name': f'{project_name}/{model_name}/.empty',
                                          # 'version_id': None,
                                          },
                              'status': 'ok'}, result)

            response = client.delete(f'/s3/{project_name}/{model_name}', content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            self.assertEqual({"status": "ok", "message": "Repo removed"}, result)

            response = client.delete(f'/s3/{project_name}', content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            self.assertEqual({"status": "ok", "message": "Project removed"}, result)

    def test_get_file_version(self):
        project_name = f"MODEL_{random_name()}"
        request_data_project = {
            "name": project_name,
        }
        model_name = f"model_{random_name()}"
        request_data_repo = {
            "name": model_name
        }
        file_name = 'filename1.txt'
        with app.test_client() as client:
            client.post('/s3/projects/create', data=json.dumps(request_data_project),
                        content_type='application/json')
            client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                        content_type='application/json')
            for i in range(10):
                file_content = f"Original file with content\r\nVersion {i}\r\n"
                data = StringIO(file_content)
                client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                            content_type='application/json')
        with app.test_client() as client:
            response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/versions')
            result = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            for i, item in enumerate(result):
                version_id = item['version_id']
                response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/{version_id}')
                self.assertEqual(response.status_code, 200)
                result = response.data
                file_content = f"Original file with content\r\nVersion {i}\r\n".encode('utf-8')
                self.assertEqual(result, file_content)


class TestS3InComplex(unittest.TestCase):
    def setUp(self) -> None:
        self.bucket_name = 'd5-auml-sum'

    def test_step_by_step_minimal(self):
        def create_project(client, name):
            request_data_project = {
                "name": name,
            }
            response = client.post('/s3/projects/create', data=json.dumps(request_data_project),
                                   content_type='application/json')
            result = json.loads(response.data)
            print("create_project:", result)

        def create_repo(client, project_name, name):
            request_data_repo = {
                "name": name
            }
            response = client.post(f'/s3/{project_name}/repos/create', data=json.dumps(request_data_repo),
                                   content_type='application/json')
            result = json.loads(response.data)
            print("create_repo:", result)

        def delete_project(client, project_name):
            response = client.delete(f'/s3/{project_name}', content_type='application/json')
            result = json.loads(response.data)
            print("delete_project", result)

        def delete_repo(client, project_name, model_name):
            response = client.delete(f'/s3/{project_name}/{model_name}', content_type='application/json')
            result = json.loads(response.data)
            print("delete_repo", result)

        def upload_files(client, project_name, model_name):
            with tempfile.TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as tmp_dir_name:
                for size in range(1, 3):
                    file_name = f'ObjectMB.zip'
                    file_path = os.path.join(tmp_dir_name, file_name)
                    file_size = 1024 * size  # Mb
                    generate_file(file_path, file_size)
                    output_file = open(file_path, 'rb')
                    client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=output_file.read(),
                                content_type='application/octet-stream')
                    output_file.close()
                    os.remove(file_path)
            file_name = 'filename1.txt'
            for i in range(3):
                file_content = f"Original file with content\r\nVersion {i}\r\n"
                data = StringIO(file_content)
                client.post(f'/s3/{project_name}/{model_name}/upload_file/{file_name}', data=data.read(),
                            content_type='application/json')

        def delete_files(client, project_name, model_name):
            response = client.get(f'/s3/{project_name}/{model_name}/files')
            result = json.loads(response.data)
            print(result)
            for file_name in set(result):
                response = client.delete(f'/s3/{project_name}/{model_name}/{file_name}')
                if len(response.data) > 0:
                    result = json.loads(response.data)
                    print(result)

        def list_versions(client, project_name, model_name):
            response = client.get(f'/s3/{project_name}/{model_name}/files')
            result = json.loads(response.data)
            versions_dd = defaultdict(list)
            for file_name in set(result):
                response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/versions')
                result = json.loads(response.data)
                for item in result:
                    version_id = item['version_id']
                    versions_dd[file_name].append(version_id)
                    response = client.get(f'/s3/{project_name}/{model_name}/{file_name}/{version_id}')
                    result = response.data
                    print(result)
            return versions_dd

        def repo_copy(client, project_name, model_name):
            response = client.get(f'/s3/{project_name}/{model_name}/copy_to/{project_name}_copy/{model_name}_copy')
            result = json.loads(response.data)
            self.assertEqual(result, {'href': f'{BASE_URL}/{project_name}_copy'})
            print({"status": "ok", "message": "Copy created"})

        def delete_file_version(client, project_name, model_name, object_name, version_id):
            response = client.delete(f'/s3/{project_name}/{model_name}/{object_name}/{version_id}')
            result = json.loads(response.data)
            print(result)

        def rollback_version(client, project_name, model_name, object_name, version_id):
            response = client.get(f'/s3/{project_name}/{model_name}/rollback/{object_name}/{version_id}')
            self.assertEqual(response.status_code, 200)

        project_name = "MODEL_YN9VW1Z"
        model_name = "model_LS8MSTI"

        print("\n" + "*" * 20)
        print("0. начало")
        with app.test_client() as client:
            print("1. создание проекта")
            create_project(client, project_name)
            print("2. создание репозитория")
            create_repo(client, project_name, model_name)
            print("3. загрузка нескольких файлов в репозиторий")
            upload_files(client, project_name, model_name)
            print("4. получение списка версий файлов")
            versions_dict = list_versions(client, project_name, model_name)
            print("5. вывод версий файлов")
            print("!", versions_dict)
            print("6. копирование репозитория")
            repo_copy(client, project_name, model_name)
            print("7. выбираем случайный файл и случайную версию")
            random_object_name = choice([x for x in versions_dict.keys()])
            random_version = choice(versions_dict[random_object_name])
            print("8. откатываемся к случайно версии файла")
            rollback_version(client, project_name, model_name, random_object_name, random_version)
            print("9. получаем текущую версию файлов в репозитории")
            versions_dict = list_versions(client, project_name, model_name)
            print("10. выводим версии файлов в репозитории")
            print("!", versions_dict)

            print("11. удаляем случайную версию файла")
            delete_file_version(client, project_name, model_name, random_object_name, random_version)
            print("12. получаем список версий файлов и выводим их")
            versions_dict = list_versions(client, project_name, model_name)
            print("!", versions_dict)
            print("13. удаляем все файлы")
            delete_files(client, project_name, model_name)

            print("14. удаляем репозиторий")
            delete_repo(client, project_name, model_name)
            print("15. удаляем проект")
            delete_project(client, project_name)

            print("16. удаляем файлы в скопированном проекте")
            delete_files(client, f"{project_name}_copy", f"{model_name}_copy")
            print("17. удаляем копию репозитория")
            delete_repo(client, f"{project_name}_copy", f"{model_name}_copy")
            print("18. удаляем копию проекта")
            delete_project(client, f"{project_name}_copy")
            print("19. завершение")


if __name__ == "__main__":
    unittest.main()
