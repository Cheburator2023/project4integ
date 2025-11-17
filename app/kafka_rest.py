import json
import random
import ssl
import time
import typing
import logging
from ssl import SSLError

import kafka
import requests
from flask import request
from jsonschema import ValidationError, SchemaError, validate
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable, UnrecognizedBrokerVersion

from app import app
from app.config import *
from app.data_models import TRANSIT_MESSAGE_SCHEMA, SEND_MESSAGE_SCHEMA
from app.error_handling import NoBrokersAvailableError, UnrecognizedBrokerVersionError, WrongSSLCertificateError, \
    CreatingKafkaProducerError
from app.redis_cache import Cache, CacheStatus
from app.utils import remove_cyrillic, calc_hexdigest


def get_kafka_producer() -> KafkaProducer:
    try:
        producer = KafkaProducer(bootstrap_servers=kafka_bootstrap_servers,
                                 value_serializer=lambda m: json.dumps(m).encode(kafka_json_dumps_encode),
                                 ssl_check_hostname=kafka_ssl_check_hostname,
                                 security_protocol=kafka_security_protocol,
                                 ssl_cafile=kafka_ssl_cafile,
                                 ssl_certfile=kafka_ssl_certfile,
                                 ssl_keyfile=kafka_ssl_keyfile,
                                 ssl_password=kafka_ssl_password,
                                 )
        return producer
    except NoBrokersAvailable as e:
        raise NoBrokersAvailableError from e
    except UnrecognizedBrokerVersion as e:
        raise UnrecognizedBrokerVersionError from e
    except SSLError as e:
        raise WrongSSLCertificateError from e
    except Exception as e:
        raise CreatingKafkaProducerError from e


def send_message_to_kafka(msg) -> typing.Dict[str, str]:
    # try to create producer object
    producer = None
    attempt = kafka_retries
    while True:
        try:
            producer = get_kafka_producer()
            break
        except Exception as e:
            logging.exception(str(e))

        attempt -= 1

        if attempt <= 0:
            logging.error(f"Failed to connect to kafka in {kafka_retries} attempts")
            return {'status': 'error', 'message': 'can not connect to kafka'}

        sleep_time = random.randint(kafka_retries_min_time, kafka_retries_max_time)
        logging.warning(f"retry connection to kafka in {sleep_time} seconds")
        time.sleep(sleep_time)

    if producer is None:
        return {'status': 'error', 'message': 'can not create kafka producer'}

    try:
        # для совместимости работы с другими библиотеками необходимо указывать пустой ключ key
        producer.send(topic_to_kafka, msg, key=bytes())
        producer.flush()
        producer.close()
        try:
            logging.info("JSON from SUM for send to Kafka")
            logging.debug("message is :{}".format(json.dumps(msg)))
        except Exception as e:
            logging.debug(e)
        return {'status': 'ok', 'message': 'ok'}
    except Exception as exp:
        logging.exception(exp)
        producer.close()
        return {
            'status': 'error',
            'message': 'send operation failed: {}'.format(exp)
        }


def get_message_from_kafka():
    # try to create consumer object
    try:
        consumer = KafkaConsumer(topic_from_kafka,
                                 bootstrap_servers=kafka_bootstrap_servers,
                                 value_deserializer=lambda m: json.loads(m),
                                 group_id=kafka_consumer_group_id,
                                 consumer_timeout_ms=kafka_consumer_timeout_ms,
                                 auto_offset_reset=kafka_consumer_auto_offset_reset,
                                 enable_auto_commit=kafka_consumer_enable_auto_commit,
                                 auto_commit_interval_ms=kafka_consumer_auto_commit_interval_ms,
                                 ssl_check_hostname=kafka_ssl_check_hostname,
                                 security_protocol=kafka_security_protocol,
                                 ssl_cafile=kafka_ssl_cafile,
                                 ssl_certfile=kafka_ssl_certfile,
                                 ssl_keyfile=kafka_ssl_keyfile,
                                 ssl_password=kafka_ssl_password)
    except kafka.errors.UnrecognizedBrokerVersion:
        logging.exception("May be a problem with the wrong security protocol")
        return {'status': 'error', 'message': 'May be a problem with the wrong security protocol'}
    except ssl.SSLError:
        logging.exception("May be a problem with the wrong ssl certificate")
        return {'status': 'error', 'message': 'May be a problem with the wrong ssl certificate'}
    except Exception:
        logging.exception('')
        return {'status': 'error', 'message': 'kafka brocker is not available'}

    # try to get kafka message
    try:
        message = next(consumer)
        consumer.close()
        return {'status': 'ok', 'message': message.value,
                'topic': message.topic, 'offset': message.offset,
                'partition': message.partition}
    except StopIteration as no_messages_exp:
        consumer.close()
        return {'status': 'ok', 'message': 'kafka message queue is empty'}
    except Exception as exp:
        logging.exception(exp)
        consumer.close()
        return {'status': 'error', 'message': 'send operation failed'}


def split_and_set_PIM_fields(request_data: dict) -> None:
    try:
        fields = request_data['service']['modelName'].split(' ')
        fields = fields[-1].split('#')
        rqId, modelName, clientId = fields
        request_data['rqId'] = rqId
        request_data['service']['modelName'] = modelName
        request_data['service']['clientId'] = clientId
    except (KeyError, ValueError):
        pass


@app.route('/kafka/send-message', methods=['POST'])
def send_message():
    request_data = request.get_json()
    try:
        validate(request_data, SEND_MESSAGE_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.error(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    logging.info("Sending message to kafka...")
    logging.debug(f"data is: {json.dumps(request_data)}")
    split_and_set_PIM_fields(request_data)
    cache = Cache(redis_pim_namespace, request_data)
    cache.save_cache(CacheStatus.ServiceUnavailable)
    res = send_message_to_kafka(request_data)
    if res.get('status') == 'ok':
        cache.save_cache(CacheStatus.Ok)
    if res.get('status') == 'error':
        return app.response_class(
            response=json.dumps({"status": "error", "message": res.get('message')}),
            status=400,
            mimetype="application/json"
        )
    return res


@app.route('/kafka/get-message', methods=['GET'])
def get_message():
    return get_message_from_kafka()


def concatenate_PIM_fields(data):
    rqId = data["dataPIM"]["rqId"]
    modelName = data["dataPIM"]["modelName"]
    namespace = data["involvedObject"]["namespace"]
    clientId = NAMESPACES.get(namespace, "")
    concat_field = f"Карточка разработки модели {rqId}#{modelName}#{clientId}"
    data["variables"]["modeldev_name"]["value"] = concat_field
    return data


@app.route('/kafka/transit-message', methods=['POST'])
def transit_message_from_kafka_to_sum():
    def kafka_hash_rule(input_data: dict) -> str:
        rq_id = input_data["dataPIM"]["rqId"]
        model_name = input_data["dataPIM"]["modelName"]
        name_space = input_data["involvedObject"]["namespace"]
        reason = input_data["reason"]
        data_for_calc = f'{rq_id}:{model_name}:{name_space}:{reason}'
        return calc_hexdigest(data_for_calc)

    data = request.get_json(force=True)
    logging.info(f"Transit data to SUM...")
    logging.debug(f"Data have type of: {type(data)}")
    if not isinstance(data, dict):
        data = json.loads(data)
    if data is None:
        return app.response_class(
            response=json.dumps(
                {"status": "error", "message": "No data to transit"}
            ),
            status=400,
            mimetype="application/json"
        )
    # Проверка наличия флага до валидации. Если True. Не валидировать, не вызывать camunda.
    if data.get("sumIgnore"):
        logging.info("Got sumIgnore flag. Exit transit-message")
        return app.response_class(
            response=json.dumps({"status": "ok"}),
            status=200,
            mimetype="application/json"
        )
    msg = remove_cyrillic(json.dumps(data))
    logging.info("Got a message from kafka")
    logging.debug(f"Message is: {msg}")
    try:
        validate(data, TRANSIT_MESSAGE_SCHEMA)
    except (ValidationError, SchemaError) as e:
        logging.warning(f"Validation error: {e.message}")
        return app.response_class(
            response=json.dumps({"status": "error", "message": e.message}),
            status=400,
            mimetype="application/json"
        )
    cache = Cache(redis_sum_namespace, data, hash_rule=kafka_hash_rule)
    cache_data = cache.get_by_data()
    if cache_data[0] is not None:
        msg = (
            f"This message was previously sent and added to the cache with "
            f"the status '{cache_data[1]}'"
        )
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=400,
            mimetype="application/json"
        )
    if data["reason"] != "ModelExported":
        msg = f"Validation error. Invalid model reason: {data['reason']}"
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=400,
            mimetype="application/json"
        )
    data = concatenate_PIM_fields(data)
    url = f"{camunda_base_url_api}/process-definition/key/automl.import/start"
    try:
        req = requests.post(
            url, json={"variables": data["variables"]},
            headers={
                "Authorization": f"Basic {camunda_authorization}",
                "Content-Type": 'application/json'
            })
    except requests.exceptions.RequestException as err:
        msg = f"Connection error to the comunda servers: {err}"
        logging.warning(msg)
        cache.save_cache(CacheStatus.ServiceUnavailable)
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=404,
            mimetype="application/json"
        )
    if req.status_code == 200:
        cache.save_cache(CacheStatus.Ok)
        msg = f"Successful sent the message to SUM. '{req.text}'"
        logging.info(msg)
        return app.response_class(
            response=json.dumps({"status": "ok", "message": msg}),
            status=200,
            mimetype="application/json"
        )
    else:
        cache.save_cache(CacheStatus.ServiceUnavailable)
        msg = (
            f"Request error. Status code: {req.status_code}. Message: "
            f"{req.text}"
        )
        logging.warning(msg)
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=404,
            mimetype="application/json"
        )


@app.route("/kafka/sum/cache-resend-message/<string:message_id>", methods=["POST"])
def sum_resend_cached_message(message_id):
    cache = Cache(redis_sum_namespace)
    data = cache.get_by_id(message_id)
    if data is None:
        msg = f"Message with id '{message_id}' not found in cache"
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=404,
            mimetype="application/json"
        )
    data = json.loads(data)
    url = f"{camunda_base_url_api}/process-definition/key/automl.import/start"
    req = requests.post(
        url, json={"variables": data["variables"]},
        headers={
            "Authorization": f"Basic {camunda_authorization}",
            "Content-Type": 'application/json'
        })
    if req.status_code == 200:
        cache.save_cache(CacheStatus.ResentManually)
        msg = f"Successful resent the message to SUM. '{req.text}'"
        logging.info(msg)
        return app.response_class(
            response=json.dumps({"status": "ok", "message": msg}),
            status=200,
            mimetype="application/json"
        )
    else:
        cache.save_cache(CacheStatus.ServiceUnavailable)
        msg = (
            f"Error while resending. Status code: {req.status_code}. Message: "
            f"{req.text}"
        )
        logging.warning(msg)
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=404,
            mimetype="application/json"
        )


@app.route("/kafka/pim/cache-resend-message/<string:message_id>", methods=["POST"])
def pim_resend_cached_message(message_id):
    cache = Cache(redis_pim_namespace)
    data = cache.get_by_id(message_id)
    if data is None:
        msg = f"Message with id '{message_id}' not found in cache"
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=404,
            mimetype="application/json"
        )
    data = json.loads(data)
    res = send_message_to_kafka(data)

    if res['status'] == 'ok':
        cache.save_cache(CacheStatus.ResentManually)
        return app.response_class(
            response=json.dumps(res),
            status=200,
            mimetype="application/json"
        )
    else:
        cache.save_cache(CacheStatus.ServiceUnavailable)
        return app.response_class(
            response=json.dumps(res),
            status=404,
            mimetype="application/json"
        )


@app.route("/kafka/cache-list", methods=["GET"])
def list_cache():
    all_cache = Cache().get_all()
    if not all_cache:
        msg = (
            "Failed to get the list of messages in the cache, maybe there is "
            "no connection to the redis server or cache is empty."
        )
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps(all_cache),
        status=200,
        mimetype="application/json"
    )


@app.route("/kafka/cache-invalidate/<string:message_id>", methods=["DELETE"])
def invalidate_entry_cache(message_id):
    if not Cache().delete_by_id(message_id):
        msg = (
            "Failed to delete cache entry, possibly not connected to redis "
            "server"
        )
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps(
            {
                "status": "ok",
                "message": "The cache is successfully invalidated"
            }
        ),
        status=200,
        mimetype="application/json"
    )


@app.route("/kafka/cache-invalidate", methods=["DELETE"])
def invalidate_cache():
    if not Cache().delete_all():
        msg = (
            "Failed to invalidate the cache, maybe there is no connection "
            "to the redis server"
        )
        return app.response_class(
            response=json.dumps({"status": "error", "message": msg}),
            status=400,
            mimetype="application/json"
        )
    return app.response_class(
        response=json.dumps({
            "status": "ok", "message": "The cache is successfully invalidated"
        }),
        status=200,
        mimetype="application/json"
    )
