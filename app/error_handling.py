import time
import traceback
from functools import wraps, partial


def try_except(func, error_message):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except Exception as exp:
            print(error_message, exp)
            try:
                res = func(*args, **kwargs)
            except Exception as exp:
                print(error_message, exp)
                return 'Error'
        return res
    return wrapper


def logged(func=None, *, is_print_params=True, is_print_results=True):
    if func is None:
        return partial(logged,
                       is_print_params=is_print_params,
                       is_print_results=is_print_results)
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            param_log_msg = '' if not is_print_params else f'with args {args}, kwargs {kwargs}'
            print(f'[{time.asctime()}] func {func.__name__} will be called {param_log_msg}')
        except Exception:
            print(f'[{time.asctime()}] func {func.__name__} will be called')
        res = func(*args, **kwargs)
        try:
            results_log_msg = '' if not is_print_results else f', return {res}'
            print(f'[{time.asctime()}] func {func.__name__} was called {results_log_msg}')
        except Exception:
            print(f'[{time.asctime()}] func {func.__name__} was called')
        return res
    return wrapper


class BitbucketFileDoestNotExist(Exception):
    def __init__(self, message, status, url=''):
        super().__init__(message, status)
        self.message = message
        self.status = status
        self.url = url

    @classmethod
    def create(cls, url):
        return cls(message='',
                   status='',
                   url=url)

    def get_message(self):
        return f"url {self.url}, doesn't exist"

    def get_status(self):
        return "Attach file to story operation failed"

    def print_log(self):
        traceback.print_tb(self.__traceback__)
        print(self)

    def __str__(self):
        return self.get_status() + ', ' + self.get_message()


class JiraUploadManyFilesAsZipError(Exception):
    def __str__(self):
        return "JiraUploadManyFilesAsZipError"


class JiraUploadFileAsZipError(Exception):
    def __str__(self):
        return "JiraUploadFileAsZipError"


class CreateZipAchiveError(Exception):
    def __str__(self):
        return "CreateZipAchiveError"


class ConnectionToMinioError(Exception):
    pass


class MinioEmptyFileError(Exception):
    pass


class ShellCommandError(Exception):
    pass


class ObjectExistsError(Exception):
    pass


class ObjectNotExistsError(Exception):
    pass


class NotEmptyRepoError(Exception):
    """Репозиторий не пуст"""
    pass


class NotEmptyProjectError(Exception):
    """Не пустой проект"""
    pass


class NotSupportedMethodError(Exception):
    """Не поддерживаемый метод"""
    pass


class VersioningCleanRulesError(Exception):
    """Если не задано правило удаления версий"""
    pass


class CreatingKafkaProducerError(Exception):
    message = 'Something went wrong in the process of creating a kafka producer'

    def __str__(self):
        return self.message


class NoBrokersAvailableError(CreatingKafkaProducerError):
    message = 'May be a kafka broker is not available'


class WrongSecurityProtocolError(CreatingKafkaProducerError):
    message = 'May be a problem with the wrong security protocol'


class WrongSSLCertificateError(CreatingKafkaProducerError):
    message = 'May be a problem with the wrong ssl certificate'


class UnrecognizedBrokerVersionError(CreatingKafkaProducerError):
    message = 'May be a problem with the wrong broker version'
