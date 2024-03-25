import json
import unittest
from io import StringIO

import requests

OUTPUT_FILENAME1 = 'file1.py'
OUTPUT_FILENAME2 = 'file2.py'
PROJECT_KEY = 'MODEL61-V1'
REPO_SLUG = 'model61-v1'
SERVICE_BASE_URL = 'http://d5drpc-apc004ln:5777'
RESULT_BASE_URL = 'https://d5drpc-apc004ln:10001'


def project_create(project_name):
    print(f"Creating project: {project_name}")


def repo_create(repo_name):
    print(f"Creating repo: {repo_name}")


def upload_file(file_name):
    print(f"Uploading file {file_name}")
    url = f'{SERVICE_BASE_URL}/bitbucket/{PROJECT_KEY}/{REPO_SLUG}/upload_file/{file_name}'
    data = StringIO("print('Hello world!')\r\nprint('Original file 1')\r\n")
    req = requests.Request('POST', url, data=data.read())
    prepared = req.prepare()
    session = requests.Session()
    resp = session.send(prepared, verify=False)
    print(f'Upload file on bitbucket status_code: {resp.status_code}')


def remove_file_on_bitbucket(file_name):
    print(f"Removing file {file_name}")
    url = f'{SERVICE_BASE_URL}/bitbucket/{PROJECT_KEY}/{REPO_SLUG}/{file_name}/remove'
    req = requests.Request('GET', url)
    prepared = req.prepare()
    session = requests.Session()
    resp = session.send(prepared, verify=False)
    print(f'Remove file on bitbucket status_code: {resp.status_code}')
    session.close()


class BitbucketTest(unittest.TestCase):
    def setUp(self) -> None:
        # project_create(self.project_key)
        # repo_create(self.repo_slug)
        upload_file(OUTPUT_FILENAME1)
        # session.close()

    def test_upload_multiple_files(self):
        print("Uploading multiple files")
        url = f"{SERVICE_BASE_URL}/bitbucket/{PROJECT_KEY}/{REPO_SLUG}/upload_multiple_files"

        output_file1 = StringIO("print('Hello world!')\r\nprint('File 1')\r\n")
        output_file2 = StringIO("print('Hello world!')\r\nprint('File 2')\r\n")

        multiple_files = [
            ['file', [OUTPUT_FILENAME1, output_file1.read()]],
            ['file', [OUTPUT_FILENAME2, output_file2.read()]]
        ]
        resp = requests.post(url, files=multiple_files, verify=False)
        print(resp.content)
        result = {
            'files': {
                'replaced': [f'{RESULT_BASE_URL}/projects/{PROJECT_KEY}/repos/{REPO_SLUG}/browse/{OUTPUT_FILENAME1}?raw'],
                'uploaded': [f'{RESULT_BASE_URL}/projects/{PROJECT_KEY}/repos/{REPO_SLUG}/browse/{OUTPUT_FILENAME2}?raw']
            }
        }
        assert json.loads(resp.content) == result

    def tearDown(self) -> None:
        remove_file_on_bitbucket(OUTPUT_FILENAME1)
        remove_file_on_bitbucket(OUTPUT_FILENAME2)


if __name__ == "__main__":
    unittest.main()
