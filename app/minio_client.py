import io
import json
import os
import re
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from functools import lru_cache
from itertools import chain
from typing import List

from dateutil import relativedelta
from flask import Request
from minio import Minio
from minio.commonconfig import CopySource
from minio.deleteobjects import DeleteObject
from minio.error import S3Error
from urllib3 import PoolManager
from urllib3.exceptions import MaxRetryError

from app import app
from app.config import BUCKET_NAME, BUCKET_URL, BUCKET_ACCESS_KEY, BUCKET_SECRET_KEY, BUCKET_REGION, MULTIPART_SIZE, \
    SECURE_S3, SSL_CERT_FILE, IGNORE_SSL_VERIFICATION, VERSIONING, VERSIONING_CLEAN_RULES
from app.error_handling import ConnectionToMinioError, MinioEmptyFileError, ObjectExistsError, ObjectNotExistsError, \
    NotEmptyRepoError, NotEmptyProjectError, NotSupportedMethodError, VersioningCleanRulesError
from app.utils import convert_to_bytes, get_version_date_time, str_to_bool, str_to_datetime, VERSION_DATE_TIME_FORMAT

EMPTY_NAME = '.empty'  # пустой файл, что бы можно было создать каталог проекта/репозитория
TEMP_SUFFIX = "_temp_"  # приставка для временных файлов
VERSION_SUFFIX = '_sumbkp_'  # суффикс для версий файлов
TEMP_FILES_PATTERN = re.compile(f".*{TEMP_SUFFIX}\\d{{20}}$")  # file_name.txt_temp_20221102180834683768
VERSION_FILES_PATTERN = re.compile(f".*{VERSION_SUFFIX}\\d{{20}}$")  # file_name.txt_sumbkp_20221102180834683768
ROOT_FOLDER_NAME = 'SUM_MODELS'  # Каталог хранения всех проектов
TEMP_STORE_PERIOD = 6  # период хранения версий в месяцах
VERSION_STORE_COUNT = 10  # количество хранимых версий


class Size(IntEnum):
    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30


def get_version_name(object_name: str = '') -> str:
    """
    Возвращает имя версионируемого файла
    Parameters:
        object_name (str): Имя файла

    Returns:
        Имя исходного файла + суффикс версии + текущая дата и время
    """
    return f"{object_name}{VERSION_SUFFIX}{get_version_date_time()}"


def get_temp_name(object_name: str) -> str:
    return f"{object_name}{TEMP_SUFFIX}{get_version_date_time()}"


def concat_version_name(object_name, version):
    return f'{object_name}{VERSION_SUFFIX}{version}'


def split_file_name_version(elem: str) -> (str, str):
    """split file name and version value from input element"""
    file_name_pos = elem.rfind(VERSION_SUFFIX)
    file_name = elem[:file_name_pos]
    version_pos = file_name_pos + len(VERSION_SUFFIX)
    version_value = elem[version_pos:]
    return file_name, version_value


class BaseMinioClass(ABC):
    def __init__(self, minio_url: str, access_key: str, secret_key: str, bucket_name: str, region: str,
                 multipart_size: int, secure=False, http_client=None):
        self.client = None
        self.minio_url = minio_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region = region
        self.multipart_size = multipart_size
        self.secure = secure
        self.http_client = http_client

    def __call__(self) -> 'BaseMinioClass':
        self.client = Minio(self.minio_url, access_key=self.access_key, secret_key=self.secret_key, region=self.region,
                            secure=self.secure, http_client=self.http_client)
        return self

    def put_object(self, object_name: str, content, content_length: int) -> 'ObjectInfo':
        """Загрузить объект в s3 хранилище

        object_name: имя объекта
        content: Объект имеющий вызываемую функцию read(), возвращающую объект байтов
        content_length: если объем content неизвестен то задается значением -1 и необходимо указать part_size (минимальное значение 5MB)
        """
        part_size = 0
        if content_length == 0:
            content_length = -1
            part_size = self.multipart_size
        # default minimum for uploading object is 5Mb. If more, then use self.multipart_size
        if content_length > 5 * Size.MB:
            part_size = self.multipart_size
        try:
            result = self.client.put_object(self.bucket_name, f'{ROOT_FOLDER_NAME}/{object_name}', content,
                                            content_length, part_size=part_size)
        except MaxRetryError as e:
            logging.exception(e)
            raise ConnectionToMinioError
        except S3Error as e:
            logging.exception(e)
            raise ObjectExistsError
        else:
            return ObjectInfo(result)

    def put_or_replace_object(self, object_name: str, content, content_length: int) -> 'ObjectInfo':
        """Загрузить объект (актуально для HCP для выключенного версионирования), если существует объект, то перед
        загрузкой объект удаляется. Загрузка происходит с помощью метода 'put_object'
        """
        return self.put_object(object_name, content, content_length)

    def create_project(self, project_name: str) -> 'ObjectInfo':
        """Создание проекта

        project_name: имя проекта

        При создании каталога, необходимо разместить хоть какой-то файл. В данном случае размещается пустой файл с
        именем '.empty'. Получается 'ROOT_FOLDER_NAME/project_name/.empty'. Перед загрузкой происходит проверку на
        существование уже по этому адресу объектов
        """
        project_path = f'{project_name}'
        object_path = f'{project_name}/{EMPTY_NAME}'
        if self.stat_object(object_path) or self.stat_object(project_path):
            raise ObjectExistsError
        empty_file = io.BytesIO()
        return self.put_object(object_path, empty_file, 0)

    def create_repo(self, project_name: str, repo_name: str) -> 'ObjectInfo':
        """Создание репозитория

        project_name: имя проекта
        repo_name: имя репозитория/модели
        Поведение как у create_project, только большая вложенность каталогов.
        'ROOT_FOLDER_NAME/project_name/repo_name/.empty'
        """
        repo_path = f'{project_name}/{repo_name}'
        object_path = f'{project_name}/{repo_name}/{EMPTY_NAME}'
        if self.stat_object(object_path) or self.stat_object(repo_path):
            raise ObjectExistsError
        empty_file = io.BytesIO()
        return self.put_object(object_path, empty_file, 0)

    def list_repo_names(self, project_key: str):
        """Получить список имен репозиториев в проекте

        project_name: имя проекта
        возвращается список из имен репозиториев в проекте 'project_name'
        """
        repos_dir = f'{ROOT_FOLDER_NAME}/{project_key}/'
        repo_list = self.client.list_objects(self.bucket_name, prefix=repos_dir)
        repo_names = []
        for obj in repo_list:
            if obj.is_dir:
                object_name = obj.object_name[len(repos_dir):]
                repo_name = object_name.strip("/")
                if not repo_name:
                    continue
                repo_names.append(repo_name)
        return repo_names

    def list_projects_names(self):
        """Получить список имен проектов

        """
        projects_dir = f'{ROOT_FOLDER_NAME}/'
        project_list = self.client.list_objects(self.bucket_name, prefix=projects_dir)
        project_names = []
        for obj in project_list:
            if obj.is_dir:
                object_name = obj.object_name[len(projects_dir):]
                object_name = object_name.strip('/')
                if not object_name:
                    continue
                project_names.append(object_name)
        return project_names

    def count_objects_by_path(self, path):
        """Подсчитывает количество объектов по указаному пути

        path: путь где необходимо подсчитать количество объектов
        """
        objects_dir = f"{ROOT_FOLDER_NAME}/{path}/"
        object_list = self.client.list_objects(self.bucket_name, prefix=objects_dir)
        return len([obj for obj in object_list])

    def list_objects_names(self, project_key: str, repo_slug: str, list_empty=False):
        """Получить список объектов в репозитории

        project_key: имя проекта
        repo_slug: имя репозитория
        """
        objects_dir = f"{ROOT_FOLDER_NAME}/{project_key}/{repo_slug}/"
        object_list = self.client.list_objects(self.bucket_name, prefix=objects_dir)
        object_names = []
        for obj in object_list:
            if not obj.is_dir:
                file_name_long = obj.object_name[len(objects_dir):]
                file_name = file_name_long.strip("/")
                if not list_empty and file_name == EMPTY_NAME:
                    continue
                object_names.append(file_name)
        return object_names

    def remove_objects(self, objects_names: List[str]):
        """Удаление объектов по их именам"""
        errors = self.client.remove_objects(
            self.bucket_name,
            [DeleteObject(f'{ROOT_FOLDER_NAME}/{object_name}') for object_name in objects_names],
        )
        for error in errors:
            logging.debug(f"error occurred when deleting object {error}")

    def remove_repo(self, project_key: str, repo_key: str):
        """Удаление репозитория

        project_key: Имя проекта
        repo_key: Имя репо
        Прежде чем удалить сам репозиторий происходит проверка о наличии в репозитории файлов. Если объекты есть, то
        возвращается ошибка, что репозиторий не пуст"""
        items = self.list_objects_names(project_key, repo_key)
        if len(items) == 0:  # if 0 then {EMPTY_NAME} file exists, remove it
            self.remove_object(f'{project_key}/{repo_key}/{EMPTY_NAME}')
        else:
            raise NotEmptyRepoError

    def remove_project(self, project_key: str):
        """Удаление проекта

        project_key: имя проекта"""
        items = self.list_repo_names(project_key)
        if len(items) > 0:
            raise NotEmptyProjectError
        status = self.stat_object(f'{project_key}/{EMPTY_NAME}')
        if status:  # if file exists, then remove it
            self.remove_object(f'{project_key}/{EMPTY_NAME}')

    def rename_object(self, object_path: str, object_name: str, new_object_name: str):
        """Переименование проекта

        object_path: путь к объект
        object_name: оригинальное имя объекта
        new_object_name: новое имя объекта
        """
        old_object_name_path = f'{object_path}/{object_name}'
        new_object_name_path = f'{object_path}/{new_object_name}'

        self.copy_object(old_object_name_path, new_object_name_path)
        self.remove_object(old_object_name_path)

    def copy_object(self, object_path_from: str, object_path_to: str, version_id=None) -> 'ObjectInfo':
        """Копирование объекта на новое место

        object_path_from: путь к оригиналу
        object_path_to: путь назначения
        """
        try:
            result = self.client.copy_object(
                self.bucket_name,
                f'{ROOT_FOLDER_NAME}/{object_path_to}',
                CopySource(self.bucket_name, f'{ROOT_FOLDER_NAME}/{object_path_from}', version_id=version_id)
            )
        except S3Error as e:
            logging.exception(e)
            raise ObjectExistsError
        except Exception as e:
            logging.exception(e)
            raise e
        else:
            return ObjectInfo(result)

    def stat_object(self, object_name: str, version_id=None):
        """Получить информацию об объекте

        object_name: путь к объекту"""
        try:
            object_stat = self.client.stat_object(self.bucket_name, f'{ROOT_FOLDER_NAME}/{object_name}',
                                                  version_id=version_id)
        except Exception as e:
            if hasattr(e, 'code'):
                logging.debug(f"Object {object_name} do not exist")
                return None
            logging.debug(e)
            return None
        if not object_stat:
            return None
        return ObjectInfo(object_stat)

    def remove_object(self, object_name: str, version_id=None):
        """Удаление объекта
        object_name: путь к объекту"""
        self.client.remove_object(self.bucket_name, object_name=f'{ROOT_FOLDER_NAME}/{object_name}',
                                  version_id=version_id)

    @abstractmethod
    def get_object(self, object_name: str, version_id=None):
        """Получение объекта по его пути

        object_name: путь к объекту
        version_id: версия объекта"""
        ...

    @abstractmethod
    def get_object_version_list(self, object_path: str, object_name: str):
        """Получить список версий для объекта внешняя"""
        ...

    @abstractmethod
    def list_object_versions(self, object_path: str, object_name: str):
        """Получить список версий для объекта внутренняя """
        ...

    @abstractmethod
    def remove_old_versions(self, object_path: str, object_name: str):
        """Удаление старых версий объектов"""
        ...

    @abstractmethod
    def rollback(self, object_path: str, object_name: str, version_id: str) -> 'ObjectInfo':
        """Откат файла до версии"""
        ...

    @abstractmethod
    def upload_file_object(self, project_key: str, repo_slug: str, file_object: Request, filename: str) -> 'ObjectInfo':
        """Загрузка объекта"""
        ...

    @abstractmethod
    def remove_doubles_versions(self, project_key: str, repo_slug: str):
        """Удаление копий версий объекта"""
        # только для не нативного (MinioClientForeignVersioning) версионирования
        ...

    @abstractmethod
    def clean_versions(self):
        """Удаление устаревших версий объектов в соответсвии с переменными TEMP_STORE_PERIOD и VERSION_STORE_COUNT"""
        ...


class MinioClientNoneVersioning(BaseMinioClass):

    def get_object(self, object_name: str, version_id=None):
        object_path = f'{ROOT_FOLDER_NAME}/{object_name}'
        try:
            return self.client.get_object(self.bucket_name, object_path)
        except S3Error as e:
            logging.exception(e)
            raise ObjectNotExistsError

    def get_object_version_list(self, object_path: str, object_name: str):
        raise NotSupportedMethodError

    def list_object_versions(self, object_path: str, object_name: str):
        raise NotSupportedMethodError

    def remove_old_versions(self, object_path: str, object_name: str):
        raise NotSupportedMethodError

    def rollback(self, object_path: str, object_name: str, version_id: str) -> 'ObjectInfo':
        raise NotSupportedMethodError

    def upload_file_object(self, project_key: str, repo_slug: str, file_object: Request, filename: str) -> 'ObjectInfo':
        file_path = f'{project_key}/{repo_slug}/{filename}'
        data = file_object.stream
        length = file_object.content_length
        if length is None:
            raise MinioEmptyFileError
        return self.put_or_replace_object(file_path, data, length)

    def remove_doubles_versions(self, project_key: str, repo_slug: str):
        raise NotSupportedMethodError

    def clean_versions(self):
        raise NotSupportedMethodError


class MinioClientHCPNoneVersioning(MinioClientNoneVersioning):

    def put_or_replace_object(self, object_name: str, content, content_length: int) -> 'ObjectInfo':
        if self.stat_object(object_name):
            self.remove_object(object_name)
        return self.put_object(object_name, content, content_length)


class MinioClientNativeVersioning(BaseMinioClass):

    def remove_repo(self, project_key: str, repo_key: str):
        # удалять все версии файлов в репозитории
        items = self.list_objects_names(project_key, repo_key)
        if len(items) > 0:  # if 0 then {EMPTY_NAME} file exists, remove it
            raise NotEmptyRepoError
        delete_object_list = map(
            lambda x: DeleteObject(x.object_name, x.version_id),
            self.client.list_objects(self.bucket_name, prefix=f'{ROOT_FOLDER_NAME}/{project_key}/{repo_key}',
                                     recursive=True, include_version=True)
        )
        errors = self.client.remove_objects(self.bucket_name, delete_object_list)
        for error in errors:
            logging.debug(f"error occurred when deleting object {error}")

    def remove_project(self, project_key: str):
        # удалять все версии проектов в репозитории
        items = self.list_repo_names(project_key)
        if len(items) > 0:
            raise NotEmptyProjectError
        delete_object_list = map(
            lambda x: DeleteObject(x.object_name, x.version_id),
            self.client.list_objects(self.bucket_name, prefix=f'{ROOT_FOLDER_NAME}/{project_key}',
                                     recursive=True, include_version=True)
        )
        errors = self.client.remove_objects(self.bucket_name, delete_object_list)
        for error in errors:
            logging.debug(f"error occurred when deleting object {error}")

    def get_object(self, object_name: str, version_id=None):
        object_path_with_suffix = f'{ROOT_FOLDER_NAME}/{object_name}'
        try:
            return self.client.get_object(self.bucket_name, object_path_with_suffix, version_id=version_id)
        except S3Error as e:
            logging.exception(e)
            raise ObjectNotExistsError

    def get_object_version_list(self, object_path: str, object_name: str):
        objects_dir = f"{ROOT_FOLDER_NAME}/{object_path}/{object_name}"
        object_list = self.client.list_objects(self.bucket_name, prefix=objects_dir, include_version=True)
        object_versions = []
        for obj in object_list:
            if not (obj.is_dir and str_to_bool(obj.is_latest)):
                file_name = obj.object_name[len(objects_dir) - len(object_name):]
                if file_name == EMPTY_NAME:
                    continue
                version_info = {
                    "version_id": obj.version_id,
                    "last_modified": obj.last_modified.strftime(VERSION_DATE_TIME_FORMAT),
                    "is_latest": str_to_bool(obj.is_latest),
                }
                object_versions.append(version_info)
        return object_versions

    def list_object_versions(self, object_path: str, object_name: str) -> List[dict]:
        objects_dir = f"{ROOT_FOLDER_NAME}/{object_path}/{object_name}"
        object_list = self.client.list_objects(self.bucket_name, prefix=objects_dir, include_version=True)
        object_versions = []
        for obj in object_list:
            if not obj.is_dir:
                file_name = obj.object_name[len(objects_dir) - len(object_name):]
                if file_name == EMPTY_NAME:
                    continue
                version_info = {
                    "version_id": obj.version_id,
                    "last_modified": obj.last_modified.replace(tzinfo=None),
                    "is_latest": str_to_bool(obj.is_latest),
                }
                object_versions.append(version_info)
        return object_versions

    def remove_old_versions(self, object_path: str, object_name: str):
        versions = self.list_object_versions(object_path, object_name)
        months = relativedelta.relativedelta(months=TEMP_STORE_PERIOD)  # Время хранения версий файлов в 1 месяц
        current_date = datetime.now()
        items = []
        for item in versions:
            if (current_date - months) > item['last_modified'] and not item['is_latest']:
                items.append(item)
        for item in items:
            name = '/'.join([object_path, object_name])
            self.remove_object(name, version_id=item['version_id'])
            logging.debug(f"object {name} was removed")

    def rollback(self, object_path: str, object_name: str, version_id: str) -> 'ObjectInfo':
        full_object_path = f'{object_path}/{object_name}'
        info = self.stat_object(full_object_path, version_id=version_id)
        if not info:
            raise FileNotFoundError("original file not exists")
        return self.copy_object(full_object_path, full_object_path, version_id=version_id)

    def upload_file_object(self, project_key: str, repo_slug: str, file_object: Request, filename: str) -> 'ObjectInfo':
        file_path = f'{project_key}/{repo_slug}/{filename}'
        data = file_object.stream
        length = file_object.content_length
        if length is None:
            raise MinioEmptyFileError
        return self.put_or_replace_object(file_path, data, length)

    def remove_doubles_versions(self, project_key: str, repo_slug: str):
        raise NotSupportedMethodError

    def clean_versions(self):
        if VERSIONING_CLEAN_RULES not in (0, 1, 2, 3):
            raise VersioningCleanRulesError

        if VERSIONING_CLEAN_RULES == 0:
            return

        @dataclass
        class ObjectVersionInfo:
            version_id: str
            last_modified: datetime
            deleted: bool = False

        def prepare_items():
            root_folder = f'{ROOT_FOLDER_NAME}/'
            object_versions = defaultdict(list)
            object_list = self.client.list_objects(self.bucket_name, prefix=root_folder, recursive=True,
                                                   include_version=True)
            for obj in object_list:
                if not obj.is_dir:
                    if obj.object_name.endswith(EMPTY_NAME) or obj.object_name.endswith('/') or str_to_bool(
                            obj.is_latest):
                        continue
                    file_name = obj.object_name[len(root_folder):]
                    version_info = ObjectVersionInfo(
                        version_id=obj.version_id,
                        last_modified=obj.last_modified.replace(tzinfo=None),
                    )
                    object_versions[file_name].append(version_info)
            return object_versions

        def remove_doubles(object_versions):
            for object_name in object_versions:
                versions = sorted(object_versions[object_name], key=lambda item: item.last_modified, reverse=True)
                for object_info in versions[VERSION_STORE_COUNT:]:
                    if not object_info.deleted:
                        object_version = object_info.version_id
                        self.remove_object(object_name, version_id=object_version)
                        logging.debug(f"object: {object_name} with version: {object_version} was removed")
                        object_info.deleted = True

        def remove_old(object_versions):
            months = relativedelta.relativedelta(months=TEMP_STORE_PERIOD)  # Время хранения версий файлов в 1 месяц
            current_date = datetime.now()
            for object_name in object_versions:
                for object_info in object_versions[object_name]:
                    if not object_info.deleted and (current_date - months) > object_info.last_modified:
                        object_version = object_info.version_id
                        self.remove_object(object_name, version_id=object_version)
                        logging.debug(f"object: {object_name} with version: {object_version} was removed")
                        object_info.deleted = True

        # 0b0  - not init
        # 0b1  - remove_old
        # 0b10 - remove_doubles
        # 0b11 - remove_old and remove_doubles
        objects = prepare_items()
        if VERSIONING_CLEAN_RULES and 0b1:
            remove_old(objects)
        if VERSIONING_CLEAN_RULES and 0b10:
            remove_doubles(objects)


class MinioClientNativeHCPVersioning(MinioClientNativeVersioning):
    """
    Для версионирования с помощью HCP.
    Удалять возможно только оригинальный файл, версии файлов удалять невозможно
    разница между MinioClientNativeHCPVersioning и MinioClientNativeVersioning в методах remove_repo, remove_project и
    remove_old_versions так как у HCP нет возможности удалять старые версии объектов. Версии объектов удаляются вместе
    с самим файлом. В остальном классы совпадают.
    """

    def remove_repo(self, project_key: str, repo_key: str):
        # удалять все версии файлов в репозитории
        items = self.list_objects_names(project_key, repo_key)
        if len(items) > 0:  # if 0 then {EMPTY_NAME} file exists, remove it
            raise NotEmptyRepoError
        delete_object_list = map(
            lambda x: DeleteObject(x.object_name),
            chain(
                self.client.list_objects(self.bucket_name, f'{ROOT_FOLDER_NAME}/{project_key}/{repo_key}/{EMPTY_NAME}'),
                self.client.list_objects(self.bucket_name, f'{ROOT_FOLDER_NAME}/{project_key}/{repo_key}'),
            )
        )
        errors = self.client.remove_objects(self.bucket_name, delete_object_list)
        for error in errors:
            logging.debug(f"error occurred when deleting object {error}")
            print(error.code, error.message, error.name, error.version_id)

    def remove_project(self, project_key: str):
        # удалять все версии проектов в репозитории
        items = self.list_repo_names(project_key)
        if len(items) > 0:
            raise NotEmptyProjectError
        delete_object_list = map(
            lambda x: DeleteObject(x.object_name, x.version_id),
            chain(
                self.client.list_objects(self.bucket_name, f'{ROOT_FOLDER_NAME}/{project_key}/{EMPTY_NAME}'),
                self.client.list_objects(self.bucket_name, f'{ROOT_FOLDER_NAME}/{project_key}'),
            )
        )
        errors = self.client.remove_objects(self.bucket_name, delete_object_list)
        for error in errors:
            logging.debug(f"error occurred when deleting object {error}")

    def remove_old_versions(self, object_path: str, object_name: str):
        raise NotSupportedMethodError

    def clean_versions(self):
        raise NotSupportedMethodError


class MinioClientForeignVersioning(BaseMinioClass):

    def get_object(self, object_name: str, version_id: str = ''):
        object_path_with_suffix = f'{ROOT_FOLDER_NAME}/{object_name}'
        if version_id:
            object_path_with_suffix += f'{VERSION_SUFFIX}{version_id}'
        try:
            return self.client.get_object(self.bucket_name, object_path_with_suffix)
        except S3Error as e:
            logging.exception(e)
            raise ObjectNotExistsError

    def get_object_version_list(self, object_path: str, object_name: str):
        object_list = self.list_object_versions(object_path, object_name)
        object_list.sort()
        object_versions = []
        for obj in object_list:
            object_versions.append(obj)
        return object_versions

    def list_object_versions(self, object_path: str, object_name: str) -> List:
        object_path_with_suffix = f'{ROOT_FOLDER_NAME}/{object_path}/{object_name}{VERSION_SUFFIX}'

        versions = [ObjectInfo(obj) for obj in
                    self.client.list_objects(self.bucket_name, prefix=object_path_with_suffix)]
        if not versions:
            return []

        len_object_path_with_suffix = len(object_path_with_suffix)
        len_version_date_time = len(get_version_date_time())  # длина даты в качестве приставки
        len_object_full_path = len_object_path_with_suffix + len_version_date_time
        # добавил проверку на суффикс и длину файла с суффиксом.
        items = []
        for objects in versions:
            if objects.object_name.startswith(object_path_with_suffix) \
                    and len(objects.object_name) == len_object_full_path:
                items.append(objects.object_name[len_object_path_with_suffix:])
        return items

    def remove_old_versions(self, object_path: str, object_name: str):
        items = self.list_object_versions(object_path, object_name)
        items.sort()
        months = relativedelta.relativedelta(months=TEMP_STORE_PERIOD)  # Время хранения версий файлов в 1 месяц
        current_date = datetime.now()
        items = [item for item in items if
                 current_date - months > str_to_datetime(item, VERSION_DATE_TIME_FORMAT)]  # по дате
        for version_date in items:
            name = '/'.join([object_path, concat_version_name(object_name, version_date)])
            self.remove_object(name)
            logging.debug(f"object {name} was removed")

    def rollback(self, object_path: str, object_name: str, version_id: str):
        orig_file_path = "/".join([object_path, object_name])
        info = self.stat_object(orig_file_path)
        if not info:  # if new object, not exist in repo
            raise FileNotFoundError("original file not exists")

        old_file_name = concat_version_name(object_name, version_id)
        old_version = "/".join([object_path, old_file_name])
        info = self.stat_object(old_version)
        if not info:  # if old object, not exist in repo
            raise FileNotFoundError("version file not exists")

        version_name = get_version_name(object_name)
        self.rename_object(object_path, object_name, version_name)
        self.rename_object(object_path, old_file_name, object_name)

    def upload_file_object(self, project_key: str, repo_slug: str, file_object: Request, filename: str) -> 'ObjectInfo':
        """
        upload new object with temp name, rename exist object with version name, rename temp file with original name
        """
        data = file_object.stream
        length = file_object.content_length
        if length is None:
            raise MinioEmptyFileError
        orig_file_path = "/".join([project_key, repo_slug, filename])
        info = self.stat_object(orig_file_path)
        if not info:  # if new object, not exist in repo, just put object
            result = self.put_object(orig_file_path, data, length)
            return result
        temp_file_name = get_temp_name(filename)  # generate temp name for object
        temp_file_path = "/".join([project_key, repo_slug, temp_file_name])
        version_name = get_version_name(filename)  # generate version name for object
        result = self.put_object(temp_file_path, data, length)
        object_path = f'{project_key}/{repo_slug}'
        self.rename_object(object_path, filename, version_name)  # rename existing object to version_name
        self.rename_object(object_path, temp_file_name, filename)  # rename temp object to original object
        return result

    def remove_doubles_versions(self, project_key: str, repo_slug: str):
        file_names = self.list_objects_names(project_key, repo_slug)

        version_items = defaultdict(list)
        for i, elem in enumerate(file_names):
            match = re.match(VERSION_FILES_PATTERN, elem)
            if match:
                file_name, version_value = split_file_name_version(elem)
                version_items[file_name].append(version_value)
            else:
                match = re.match(TEMP_FILES_PATTERN, elem)
                if not match:
                    version_items[elem].extend([])
        for object_name in version_items:
            versions = sorted(version_items[object_name], reverse=True)
            for version_date in versions[VERSION_STORE_COUNT:]:
                name = '/'.join([project_key, repo_slug, concat_version_name(object_name, version_date)])
                self.remove_object(name)
                logging.debug(f"object {name} was removed")

    def clean_versions(self):
        raise NotSupportedMethodError


@lru_cache(1)
def get_minio_client() -> BaseMinioClass:
    default_multipart_size = 5 * Size.GB  # maximum multipart upload size value for minio
    if MULTIPART_SIZE:
        try:
            multipart_size = convert_to_bytes(MULTIPART_SIZE)
            logging.info(f"Multipart size set to {multipart_size}")
        except ValueError:
            logging.warning(f"Can't convert MULTIPART_SIZE: '{MULTIPART_SIZE}' value to bytes, use default value: "
                               f"'{default_multipart_size}'")
            multipart_size = default_multipart_size
        if not (5 * Size.MB <= multipart_size <= 5 * Size.GB):
            logging.warning(
                f"Can't use multipart_size more then 5GB and less 5MB, use default value: '{default_multipart_size}'")
            multipart_size = default_multipart_size
    else:
        logging.warning(f"MULTIPART_SIZE variable not init, use default value: '{default_multipart_size}'")
        multipart_size = default_multipart_size

    http_client = None  # custom http connection pool
    if SECURE_S3:
        logging.info(f"Try to init http client with secure protocol")
        if IGNORE_SSL_VERIFICATION:
            cert_reqs = 'CERT_NONE'  # ignore SSL Verification
        else:
            cert_reqs = 'CERT_REQUIRED'
        if os.path.isfile(SSL_CERT_FILE):
            http_client = PoolManager(cert_reqs=cert_reqs, ca_certs=SSL_CERT_FILE)
        else:
            logging.warning(f"Can't find cert file '{SSL_CERT_FILE}'")
            http_client = PoolManager(cert_reqs=cert_reqs)
        logging.info(f"Http client initialised with '{cert_reqs}'")

    # Типы версионирования
    versioning_types = {
        "native": MinioClientNativeVersioning,  # Нативное версионирование s3/minio/ceph
        "hcp": MinioClientNativeHCPVersioning,  # Нативное версионирование HCP
        "foreign": MinioClientForeignVersioning,  # Версионирование с помощью специфичного именования файлов
        "no": MinioClientNoneVersioning,  # Не использовать версионирование, использовать по умолчанию
        "hcpno": MinioClientHCPNoneVersioning,  # Не использовать версионирование на HCP железке
    }
    minio_client = versioning_types.get(VERSIONING.lower())
    if minio_client:
        logging.info(f"Use '{minio_client.__name__}': '{VERSIONING}' versioning")
    else:
        logging.warning("Variable 'VERSIONING' type is not set, use 'MinioClientNoneVersioning' as default")
        minio_client = MinioClientNoneVersioning
    client = minio_client(BUCKET_URL, BUCKET_ACCESS_KEY, BUCKET_SECRET_KEY, BUCKET_NAME, BUCKET_REGION, multipart_size,
                          SECURE_S3, http_client)
    return client()


class ObjectInfo:
    def __init__(self, *args):
        names = ['bucket_name', 'content_type', 'etag', 'fromxml', 'is_delete_marker', 'is_dir', 'is_latest',
                 'last_modified', 'metadata', 'object_name', 'owner_id', 'owner_name', 'size', 'storage_class',
                 'version_id']
        self.object = {name: getattr(*args, name, None) for name in names}

    def _object_info(self) -> str:
        return f"bucket_name: '{self.object['bucket_name']}', " \
               f"object_name: '{self.object['object_name']}', " \
               f"version_id: '{self.object['version_id']}'"

    def __str__(self):
        return self._object_info()

    def __repr__(self):
        return self._object_info()

    def __getitem__(self, item):
        return self.object.get(item)

    def __getattr__(self, item):
        return self.object.get(item)

    def as_dict(self):
        return {
            "bucket_name": self.object['bucket_name'],
            "object_name": self.object['object_name'][len(ROOT_FOLDER_NAME) + 1:],
            "version_id": self.object['version_id'],
            "is_dir": self.object['is_dir']
        }

    def as_json(self):
        dict_value = self.as_dict()
        raw_json = json.JSONEncoder(sort_keys=True).encode(dict_value)
        return raw_json
