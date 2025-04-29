import json
import unittest
from unittest.mock import patch, Mock
import app.repo as repo
from app import app

def mock_response(status=200, json_data=None, text_data=None):
    response = Mock()
    response.status_code = status
    if text_data:
        response.return_value = text_data
    else:
        response.json.return_value = json_data or {}
    return response

class TestAuth(unittest.TestCase):
    @patch('app.repo.requests.get')
    def test_auth_success(self, mock_get):
        token = 'token'

        mock_get.return_value = mock_response(json_data={"access_token": token})

        result = repo.auth()
        self.assertEqual(token, result)  # add assertion here

    @patch('app.repo.requests.get')
    def test_auth_error(self, mock_get):
        mock_get.return_value = mock_response(404, {"error": {"code":"404-1", "message":"Учетная запись не зарегистрирована в системе 1655_17"}})

        with self.assertRaises(repo.NotAuthenticatedError) as cm:
            repo.auth()

        self.assertEqual(cm.exception.__str__(), "Учетная запись не зарегистрирована в системе 1655_17")

    @patch('app.repo.requests.get')
    def test_auth_no_access_token(self, mock_get):
        mock_get.return_value = mock_response(json_data={"no_token": "stub"})

        with self.assertRaises(repo.NotAuthenticatedError) as cm:
            repo.auth()

        self.assertEqual(cm.exception.__str__(), "Response is empty or access_token is not set")

class TestCreate(unittest.TestCase):
    request_data = {
        "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
        "model_name": "Тест Repo",
        "model_id": "075bde6c-6f89-42f0-9c34-5ffb7175e65e",
        "model_desc": "Тест Repo описание",
        "ds_department": "Моделирование РБ",
    }

    @patch('app.repo.requests.post')
    @patch('app.repo.requests.get')
    def test_create_success(self, mock_get, mock_post):
        token = 'token'

        mock_get.return_value = mock_response(json_data={"access_token": token})
        mock_post.return_value = mock_response(json_data={
            "repo-domain-model-2" : {},
            "message": "Репозиторий успешно создан",
            "success": True,
        })

        with app.test_client() as client:
            response = client.post('/repo/create', data=json.dumps(self.request_data), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            self.assertEqual({'model_repo_is_created': True}, result)
            mock_post.assert_called_once()
            url, kwargs = mock_post.call_args
            headers = kwargs.get("headers")
            self.assertIsNotNone(headers)
            self.assertEqual('Bearer ' + token, headers.get("Authorization"))
            self.assertEqual('Моделирование РБ', headers.get("CreateOnBehalf"))

    @patch('app.repo.requests.get')
    def test_create_not_authenticated(self, mock_get):
        mock_get.return_value = mock_response(json_data={"no_token": "stub"})

        with app.test_client() as client:
            response = client.post('/repo/create', data=json.dumps(self.request_data), content_type='application/json')
            self.assertEqual(401, response.status_code)

    def test_create_bad_request(self):
        with app.test_client() as client:
            response = client.post('/repo/create', data=json.dumps({
            }), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("general_model_id is not set", result.get("message"))

            response = client.post('/repo/create', data=json.dumps({
                "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
            }), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("model_name is not set", result.get("message"))

            response = client.post('/repo/create', data=json.dumps({
                "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
                "model_name": "Тест Repo",
            }), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("model_id is not set", result.get("message"))

            response = client.post('/repo/create', data=json.dumps({
                "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
                "model_name": "Тест Repo",
                "model_id": "075bde6c-6f89-42f0-9c34-5ffb7175e65e",
            }), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("model_desc is not set", result.get("message"))

            response = client.post('/repo/create', data=json.dumps({
                "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
                "model_name": "Тест Repo",
                "model_id": "075bde6c-6f89-42f0-9c34-5ffb7175e65e",
                "model_desc": "Тест Repo описание",
            }), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("ds_department is not set", result.get("message"))

    @patch('app.repo.requests.post')
    @patch('app.repo.requests.get')
    def test_create_error_with_message(self, mock_get, mock_post):
        token = 'token'
        response_code = 412
        reponse_error_message = "Репозиторий с указанным \"version-id\" уже существует"

        mock_get.return_value = mock_response(json_data={"access_token": token})
        mock_post.return_value = mock_response(response_code, json_data={
            "error": {"code":"412-2", "message":reponse_error_message}
        })

        with app.test_client() as client:
            response = client.post('/repo/create', data=json.dumps(self.request_data), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response_code, response.status_code)
            self.assertEqual(f"Error response from Repo service: {reponse_error_message}", result.get("message"))

    @patch('app.repo.requests.post')
    @patch('app.repo.requests.get')
    def test_create_error_broken_response(self, mock_get, mock_post):
        token = 'token'

        mock_get.return_value = mock_response(json_data={"access_token": token})
        mock_post.return_value = mock_response(503, text_data='error')

        with app.test_client() as client:
            response = client.post('/repo/create', data=json.dumps(self.request_data), content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(500, response.status_code)
            self.assertEqual("Parameter success was not set in Repo service response", result.get("message"))


class TestStatus(unittest.TestCase):
    request_data = {
        "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
        "model_id": "075bde6c-6f89-42f0-9c34-5ffb7175e65e",
    }

    @patch('app.repo.requests.get')
    def test_status_success_true(self, mock_get):
        token = 'token'

        mock_get.side_effect = [mock_response(json_data={"access_token": token}), mock_response(json_data={
            "result-list" : [{}, {}, {}],
        })]

        with app.test_client() as client:
            response = client.get('/repo/status', query_string=self.request_data, content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            self.assertEqual({'model_repo_is_created': True}, result)
            url, kwargs = mock_get.call_args
            headers = kwargs.get("headers")
            self.assertIsNotNone(headers)
            self.assertEqual('Bearer ' + token, headers.get("Authorization"))

    @patch('app.repo.requests.get')
    def test_status_success_false(self, mock_get):
        token = 'token'

        mock_get.side_effect = [mock_response(json_data={"access_token": token}), mock_response(json_data={
            "result-list": [],
        })]

        with app.test_client() as client:
            response = client.get('/repo/status', query_string=self.request_data, content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(200, response.status_code)
            self.assertEqual({'model_repo_is_created': False}, result)
            url, kwargs = mock_get.call_args
            headers = kwargs.get("headers")
            self.assertIsNotNone(headers)
            self.assertEqual('Bearer ' + token, headers.get("Authorization"))

    @patch('app.repo.requests.get')
    def test_status_not_authenticated(self, mock_get):
        mock_get.return_value = mock_response(json_data={"no_token": "stub"})

        with app.test_client() as client:
            response = client.get('/repo/status', query_string=self.request_data, content_type='application/json')
            self.assertEqual(401, response.status_code)

    def test_status_bad_request(self):
        with app.test_client() as client:
            response = client.get('/repo/status', query_string={
            }, content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("general_model_id is not set", result.get("message"))

            response = client.get('/repo/status', query_string={
                "general_model_id": "7dd3e442-c19b-4f4b-9339-923f9e440602",
            }, content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(400, response.status_code)
            self.assertEqual("model_id is not set", result.get("message"))

    @patch('app.repo.requests.get')
    def test_status_error_with_message(self, mock_get):
        token = 'token'
        response_code = 401
        reponse_error_message = "Неверный токен доступа или время жизни токена истекло. Повторите аутентификацию или обновите токен для текущей сессии"

        mock_get.side_effect = [mock_response(json_data={"access_token": token}), mock_response(response_code, json_data={
            "error": {"code": "401", "message": reponse_error_message}
        })]

        with app.test_client() as client:
            response = client.get('/repo/status', query_string=self.request_data, content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(response_code, response.status_code)
            self.assertEqual(f"Error response from Repo service: {reponse_error_message}", result.get("message"))

    @patch('app.repo.requests.get')
    def test_create_error_broken_response(self, mock_get):
        token = 'token'

        mock_get.side_effect = [mock_response(json_data={"access_token": token}), mock_response(503, text_data='error')]

        with app.test_client() as client:
            response = client.get('/repo/status', query_string=self.request_data, content_type='application/json')
            result = json.loads(response.data)
            self.assertEqual(500, response.status_code)
            self.assertEqual("Parameter result-list was not set in Repo service response", result.get("message"))


if __name__ == '__main__':
    unittest.main()
