from app import app
from app.config import *

import uuid
from kubernetes import client
from kubernetes import config

config.load_incluster_config()


class Kubernetes:
    def __init__(self):

        # Init Kubernetes
        self.core_api = client.CoreV1Api()
        self.batch_api = client.BatchV1Api()

    def create_namespace(self, namespace):

        namespaces = self.core_api.list_namespace()
        all_namespaces = []
        for ns in namespaces.items:
            all_namespaces.append(ns.metadata.name)

        if namespace in all_namespaces:
            app.logger.info(f"Namespace {namespace} already exists. Reusing.")
        else:
            namespace_metadata = client.V1ObjectMeta(name=namespace)
            self.core_api.create_namespace(
                client.V1Namespace(metadata=namespace_metadata)
            )
            app.logger.info(f"Created namespace {namespace}.")

        return namespace

    @staticmethod
    def create_container(image, name, pull_policy, command, args, env, volume_mounts, resources):

        container = client.V1Container(
            env=env,
            image=image,
            name=name,
            image_pull_policy=pull_policy,
            command=command,
            args=args,
            volume_mounts=volume_mounts,
            resources=resources
        )


        app.logger.info(
            f"Created container with name: {container.name}, "
            f"image: {container.image} and args: {container.args}"
        )

        return container

    @staticmethod
    def create_pod_template(pod_name, container, image_pull_secrets, volume, service_account_name):
        pod_template = client.V1PodTemplateSpec(
            spec=client.V1PodSpec(image_pull_secrets=[client.V1LocalObjectReference(image_pull_secrets)],
                                  restart_policy="Never",
                                  containers=[container],
                                  volumes=[volume],
                                  service_account_name=service_account_name),
            metadata=client.V1ObjectMeta(name=pod_name, labels={"pod_name": pod_name}),
        )

        return pod_template

    @staticmethod
    def create_job(job_name, pod_template):
        metadata = client.V1ObjectMeta(name=job_name, labels={"job_name": job_name})

        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=client.V1JobSpec(backoff_limit=0, template=pod_template),
        )

        return job


def run_k8s_job(env):
    job_id = uuid.uuid4()
    pod_id = job_id

    # Kubernetes instance
    k8s = Kubernetes()

    # STEP1: CREATE A CONTAINER
    env = [client.V1EnvVar(name=k, value=v) for k,v in env.items()]
    volume_mounts = [client.V1VolumeMount(name=k8s_ssh_keys, read_only=True, mount_path=k8s_ssh_path)]
    resources = client.V1ResourceRequirements(
        limits={"cpu": k8s_resources_limits_cpu, "memory": k8s_resources_limits_memory},
        requests={"cpu": k8s_resources_requests_cpu, "memory": k8s_resources_requests_memory})
    shuffler_container = k8s.create_container(k8s_image, k8s_container_name,
                                              k8s_pull_policy, k8s_command,
                                              k8s_args, env, volume_mounts, resources)

    # STEP2: CREATE A POD TEMPLATE SPEC
    volume = client.V1Volume(
        name=k8s_ssh_keys,
        secret=client.V1SecretVolumeSource(
            secret_name=k8s_ssh_keys,
            items=[client.V1KeyToPath(key="id_rsa", path="id_rsa"),
                   client.V1KeyToPath(key="id_rsa.pub", path="id_rsa.pub"),
                   client.V1KeyToPath(key="known_hosts", path="known_hosts")]
        )

    )
    pod_name = f'validation-job-pod-{pod_id}'
    pod_spec = k8s.create_pod_template(pod_name,
                                       shuffler_container,
                                       k8s_image_pull_secrets,
                                       volume,
                                       k8s_service_account_name)

    # STEP3: CREATE A JOB
    job_name = f"validation-job-{job_id}"
    job = k8s.create_job(job_name, pod_spec)

    # STEP4: CREATE NAMESPACE
    # k8s.create_namespace(k8s_namespace)

    # STEP5: EXECUTE THE JOB
    batch_api = client.BatchV1Api()
    batch_api.create_namespaced_job(k8s_namespace, job)

