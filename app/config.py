import os
from distutils.util import strtobool
from typing import List

from app.namespace_storage import get_namespace_map


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, default)
    try:
        value = strtobool(str(value))
    except ValueError:
        value = default
    return bool(value)


logging_level = os.environ.get("logging_level", "INFO")
logs_directory = os.environ.get("logs_directory", "/app/logs")

###### NEXUS #################
nexus_hostname = os.environ.get('nexus_hostname')
nexus_port = os.environ.get('nexus_port')
nexus_base_url = 'https://' + nexus_hostname + ':' + str(nexus_port) + '/service/rest/v1'
nexus_authorization = os.environ.get('nexus_authorization')

###### BITBUCKET ##############
bitbucket_hostname = os.environ.get('bitbucket_hostname')
bitbucket_hostname_ssh = os.environ.get('bitbucket_hostname_ssh')
bitbucket_port = os.environ.get('bitbucket_port')
bitbucket_port_ssh = os.environ.get('bitbucket_port_ssh')
bitbucket_ssh_url = os.environ.get('bitbucket_ssh_url',
                                   f'{bitbucket_hostname_ssh}:{bitbucket_port_ssh}')
bitbucket_user = os.environ.get('bitbucket_user')
bitbucket_base_url = 'https://' + bitbucket_hostname + ':' + str(bitbucket_port)
bitbucket_base_url_api = 'https://' + bitbucket_hostname + ':' + str(bitbucket_port) + '/rest/api/1.0'
bitbucket_authorization = os.environ.get('bitbucket_authorization')
###############################


###### JIRA ###################
jira_hostname = os.environ.get('jira_hostname')
jira_port = os.environ.get('jira_port')
jira_base_url = 'https://' + jira_hostname + ':' + str(jira_port) + '/rest/api/latest'
## DK
#jira_authorization = 'dnRiMjI0NDQ5QHJlZ2lvbi52dGIucnU6WWpkc3FHZmhqa20zMw=='
## TUZ_SUM_SERVICE_JIRA:
jira_authorization = os.environ.get('jira_authorization')
###############################


##### MLFLOW #################
mlflow_hostname = os.environ.get('mlflow_hostname')
mlflow_port = os.environ.get('mlflow_port')
mlflow_base_url = 'http://' + mlflow_hostname + ':' + str(mlflow_port) + '/api/2.0/mlflow'

# for connect to test mlflow2
mlflow_test_port = os.environ.get('mlflow_test_port')
mlflow_test_base_url = 'http://' + mlflow_hostname + ':' + str(mlflow_test_port) + '/api/2.0/mlflow'
##############################


##### TEAMCITY ###############
teamcity_hostname = os.environ.get('teamcity_hostname')
teamcity_port = os.environ.get('teamcity_port')
teamcity_base_url = 'http://' + teamcity_hostname + ':' + str(teamcity_port)
teamcity_base_url_api = 'http://' + teamcity_hostname + ':' + str(teamcity_port) + '/app/rest'
teamcity_authorization = os.environ.get('teamcity_authorization')

camunda_hostname = os.environ.get('camunda_hostname')
camunda_port = os.environ.get('camunda_port')
camunda_base_url = 'http://' + camunda_hostname + ':' + str(camunda_port)
camunda_base_url_api = 'http://' + camunda_hostname + ':' + str(camunda_port) + '/engine-rest'
camunda_authorization = os.environ.get('camunda_authorization')
##############################


###### KAFKA ##################
def parse(s: str) -> List[str]:
    return s.replace(' ', '').split(',')


kafka_bootstrap_servers: List[str] = parse(os.environ.get('kafka_bootstrap_servers',
                                                          '127.0.0.1:9092'))
topic_to_kafka = os.environ.get("topic_to_kafka", "test_out_topic")
topic_from_kafka = os.environ.get("topic_from_kafka", "test_in_topic")

kafka_security_protocol = os.environ.get('kafka_security_protocol', 'PLAINTEXT')
kafka_ssl_cafile = os.environ.get('kafka_ssl_cafile', None)
kafka_ssl_certfile = os.environ.get('kafka_ssl_certfile', None)
kafka_ssl_keyfile = os.environ.get('kafka_ssl_keyfile', None)
kafka_ssl_password = os.environ.get('kafka_ssl_password', None)
kafka_ssl_check_hostname = os.environ.get('kafka_ssl_check_hostname', False)
kafka_retries: int = int(os.environ.get('kafka_retries', 3))
kafka_retries_min_time: int = int(os.environ.get('kafka_retries_min_time', 1))
kafka_retries_max_time: int = int(os.environ.get('kafka_retries_max_time', 2))

kafka_json_dumps_encode = os.environ.get('kafka_json_dumps_encode', 'utf-8')

kafka_consumer_timeout_ms = float(os.environ.get('kafka_consumer_timeout_ms', 15000))
kafka_consumer_group_id = os.environ.get('kafka_group_id', 'testGroup')
kafka_consumer_auto_offset_reset = os.environ.get('kafka_auto_offset_reset', 'earliest')
kafka_consumer_enable_auto_commit = os.environ.get('kafka_enable_auto_commit', True)
kafka_consumer_auto_commit_interval_ms = int(os.environ.get('kafka_auto_commit_interval_ms', 1000))
###############################


###### REDIS ###################
redis_host = os.getenv("redis_host", "127.0.0.1")
redis_port = int(os.getenv("redis_port", "6379"))
redis_healhcheck_interval = int(os.getenv("redis_healhcheck_interval", "30"))
kafka_message_ttl = int(os.getenv("kafka_message_ttl", "43200"))
redis_pim_namespace = 'pim_messages'
redis_sum_namespace = 'sum_messages'
# redis password for conneciton
redis_password = os.getenv("redis_password", None)
redis_username = os.getenv("redis_username", None)
################################


###### CELERY ##################
celery_result_backend = 'redis://redis:6379/1'
celery_broker_url = 'redis://redis:6379/0'
celery_timezone = 'UTC'
celery_schedule = 60000.0  # in seconds
###############################


###### S3/minio ##################
BUCKET_NAME = os.environ.get('s3_bucket_name')
BUCKET_URL = os.environ.get('s3_bucket_url')
BUCKET_ACCESS_KEY = os.environ.get('s3_bucket_access_key')
BUCKET_SECRET_KEY = os.environ.get('s3_bucket_secret_key')
BUCKET_REGION = os.environ.get('s3_bucket_region')
MULTIPART_SIZE = os.environ.get("s3_multipart_size", "5 GB")
SECURE_S3 = get_env_bool("secure_s3", True)
SSL_CERT_FILE = os.environ.get("ssl_cert_file", '/etc/ssl/certs/ca-bundle.crt')
IGNORE_SSL_VERIFICATION = get_env_bool("ignore_ssl_verification", False)
VERSIONING = os.environ.get("versioning", "No")  # Possible values (No, HCPNo, Native, HCP, Foreign) Native for minio, ceph
VERSIONING_CLEAN_RULES = int(os.environ.get("versioning_clean_rules", 0))  # 0 не удалять 1 только версии старше определенного периода 2 - удалять до определенного количества 3 - 1 и 2 режим вместе

###### k8s jobs ##################
k8s_image = os.environ.get("k8s_image")
k8s_container_name = os.environ.get("k8s_container_name")
k8s_service_account_name = os.environ.get("k8s_service_account_name")
k8s_namespace = os.environ.get("k8s_namespace")
k8s_pull_policy = os.environ.get("k8s_pull_policy")
k8s_image_pull_secrets = os.environ.get("k8s_image_pull_secrets")
k8s_command = [os.environ.get("k8s_command", "/bin/sh")]
k8s_args: List[str] = os.environ.get("k8s_args", "run_validation.sh").split()
k8s_ssh_keys = os.environ.get("k8s_ssh_keys")
k8s_ssh_path = os.environ.get("k8s_ssh_path", "/.ssh")

k8s_callback_url = os.environ.get('k8s_callback_url')

k8s_resources_limits_cpu = os.environ.get("k8s_resources_limits_cpu")
k8s_resources_limits_memory = os.environ.get("k8s_resources_limits_memory")
k8s_resources_requests_cpu = os.environ.get("k8s_resources_requests_cpu")
k8s_resources_requests_memory = os.environ.get("k8s_resources_requests_memory")
###############################


###### Integration Service URL ##################
BASE_URL = os.environ.get('base_is_url', "http://integration-ds1-lpad01-sumd-system.apps.ds1-lpad01.corp.dev.vtb/s3")


##### namespaces #################
NAMESPACES = get_namespace_map()

# TSLG Configuration
tslg_agent_host = os.environ.get('TSLG_AGENT_HOST', 'tslg-agent-svc-main.dk1-sumd01-sumd-core.svc.cluster.local')
tslg_agent_port = int(os.environ.get('TSLG_AGENT_PORT', '5170'))
tslg_reconnection_delay_ms = int(os.environ.get('TSLG_RECONNECTION_DELAY_MS', '2000'))
tslg_connection_ttl_ms = int(os.environ.get('TSLG_CONNECTION_TTL_MS', '2000'))
tslg_client_version = os.environ.get('TSLG_CLIENT_VERSION', '1.0.0')

# TSLG Advanced Settings
tslg_enable_trace_fields = get_env_bool('TSLG_ENABLE_TRACE_FIELDS', True)
tslg_max_buffer_size = int(os.environ.get('TSLG_MAX_BUFFER_SIZE', '500'))
tslg_socket_timeout_ms = int(os.environ.get('TSLG_SOCKET_TIMEOUT_MS', '5000'))
tslg_console_output = get_env_bool('TSLG_CONSOLE_OUTPUT', True)
tslg_enable_full_context = get_env_bool('TSLG_ENABLE_FULL_CONTEXT', True)
tslg_buffer_flush_interval_ms = int(os.environ.get('TSLG_BUFFER_FLUSH_INTERVAL_MS', '100'))
tslg_max_connection_attempts = int(os.environ.get('TSLG_MAX_CONNECTION_ATTEMPTS', '10'))

# TSLG Data Sanitization
tslg_sanitize_sensitive_data = get_env_bool('TSLG_SANITIZE_SENSITIVE_DATA', True)

# TSLG Log Level Configuration
tslg_log_level = os.environ.get('TSLG_LOG_LEVEL', 'info')

# Application Logging Configuration
app_name = os.environ.get('APP_NAME', 'integration')
project_code = os.environ.get('PROJECT_CODE', 'sum')
ris_code = os.environ.get('RIS_CODE', '1661')

# Kubernetes Settings
kubernetes_namespace = os.environ.get('KUBERNETES_NAMESPACE', 'dk1-sumd01-sumd-core')
pod_ip = os.environ.get('POD_IP', '10.244.1.25')
node_name = os.environ.get('NODE_NAME', 'dk1-sumd01-node-05')
pod_name = os.environ.get('POD_NAME', 'integration-7c8b5d9f6-abc123')