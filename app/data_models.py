TRANSIT_MESSAGE_SCHEMA = {
    "type": "object",
    "required": [
        "reason",
        "involvedObject",
        "variables",
        "exportOptions"
    ],
    "properties": {
        "exportOptions": {
            "type": "object"
        },
        "reason": {
            "type": "string"
        },
        "involvedObject": {
            "type": "object",
            "required": [
                "apiVersion",
                "kind",
                "name",
                "namespace"
            ],
            "properties": {
                "apiVersion": {
                    "type": "string"
                },
                "kind": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                },
                "namespace": {
                    "type": "string"
                }
            }
        },
        "dataPIM": {
            "type": "object",
            "required": [
                "rqId",
                "modelName"
            ],
            "properties": {
                "rqId": {
                    "type": "string"
                },
                "modelName": {
                    "type": "string"
                }
            }
        },
        "variables": {
            "type": "object",
            "required": [
                "modeldev_name",
                "developing_end_date",
                "developing_start_date",
                "developing_model_datamart_not_split",
                "plan_date_integration",
                "validation_datamart_attributes",
                "model_id",
                "model_image_nexus_link",
                "monitoring_datamart_attributes"
            ],
            "properties": {
                "modeldev_name": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "developing_end_date": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "developing_start_date": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "developing_model_datamart_not_split": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "plan_date_integration": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "validation_datamart_attributes": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "model_id": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "model_image_nexus_link": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                },
                "monitoring_datamart_attributes": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    }
}

SEND_MESSAGE_SCHEMA = {
    "type": "object",
    "required": [
        "command",
        "modelAlias",
        "service"
    ],
    "properties": {
        "command": {
            "type": "string"
        },
        "modelAlias": {
            "type": "string"
        },
        "service": {
            "type": "object",
            "required": [
                "containerCfgPimNexusAddr",
                "epic",
                "imagePimNexusAddr",
                "modelDesc",
                "modelName",
                "modelVersion",
                "rootModelId",
                "usingMode",
            ],
            "properties": {
                "containerCfgPimNexusAddr": {
                    "type": "string"
                },
                "epic": {
                    "type": ["string", "null"]
                },
                "imagePimNexusAddr": {
                    "type": "string"
                },
                "modelDesc": {
                    "type": "string"
                },
                "modelName": {
                    "type": "string"
                },
                "modelVersion": {
                    "type": "integer"
                },
                "rootModelId": {
                    "type": "integer"
                },
                "usingMode": {
                    "type": "string"
                },
            }
        }
    }
}

REPO_CREATE_S3_SCHEMA = {
    "type": "object",
    "required": [
        "name",
    ],
    "properties": {
        "name": {"$ref": "#/definitions/nonEmptyString"},
    },
    "definitions": {
        "nonEmptyString": {
            "type": "string",
            "minLength": 1
        }
    }
}

PROJECT_CREATE_S3_SCHEMA = {
    "type": "object",
    "required": [
        "name",
    ],
    "properties": {
        "name": {"$ref": "#/definitions/nonEmptyString"},
    },
    "definitions": {
        "nonEmptyString": {
            "type": "string",
            "minLength": 1
        }
    }
}

DOWNLOAD_URL_SCHEMA = {
    "type": "object",
    "required": [
        "url",
        "project",
        "repo"
    ],
    "properties": {
        "url": {
            "type": "string"
        },
        "project": {
            "type": "string"
        },
        "repo": {
            "type": "string"
        },
        "name": {
            "type": "string"
        }
    }
}

BITBUCKET_PROJECT_CREATE_SCHEMA = {
    "type": "object",
    "required": [
        "key",
        "name",
        "description"
    ],
    "properties": {
        "key": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "description": {
            "type": "string"
        }
    }
}

BITBUCKET_REPO_CREATE_SCHEMA = {
    "type": "object",
    "required": [
        "name",
        "scmId",
        "forkable"
    ],
    "properties": {
        "name": {
            "type": "string"
        },
        "scmId": {
            "type": "string"
        },
        "forkable": {
            "type": "boolean"
        }
    }
}

TEAMCITY_MODEL_BUILD_START = {
    "type": "object",
    "required": [
        "alias",
        "ID",
        "messageName",
        "processInstanceId",
        "stage",
        "lang"
    ],
    "properties": {
        "alias": {
            "type": "string"
        },
        "ID": {
            "type": "string"
        },
        "messageName": {
            "type": "string"
        },
        "processInstanceId": {
            "type": "string"
        },
        "stage": {
            "type": "string",
            "enum": [
                "build",
                "deploy",
                "test",
                "destroy"
            ]
        },
        "lang": {
            "type": "string"
        }
    }
}

TEAMCITY_MODEL_BUILD_STATUS = {
    "type": "object",
    "required": [
        "messageName",
        "processInstanceId",
        "stage",
        "status",
        "statusMessage"
    ],
    "properties": {
        "messageName": {
            "type": "string"
        },
        "processInstanceId": {
            "type": "string"
        },
        "stage": {
            "type": "string",
            "enum": [
                "build",
                "deploy",
                "test",
                "destroy"
            ]
        },
        "status": {
            "type": "string",
            "enum": [
                "ok",
                "error"
            ]
        },
        "statusMessage": {
            "type": "string",
            "enum": [
                "Success",
                "Failure",
                "ClusterFailure",
                "ContainerFailure"
            ]
        },
        "imageSumNexusAddr": {
            "type": "string"
        },
        "message": {
            "type": "string"
        }
    }
}

TEAMCITY_MODEL_PUBLISH_START = {
    "type": "object",
    "required": [
        "alias",
        "ID",
        "messageName",
        "processInstanceId",
        "imageSumNexusAddr",
        "containerCfgBitbucketAddr"
    ],
    "properties": {
        "alias": {
            "type": "string"
        },
        "ID": {
            "type": "string"
        },
        "messageName": {
            "type": "string"
        },
        "processInstanceId": {
            "type": "string"
        },
        "imageSumNexusAddr": {
            "type": "string"
        },
        "containerCfgBitbucketAddr": {
            "type": "string"
        }
    }
}

TEAMCITY_MODEL_PUBLISH_STATUS = {
    "type": "object",
    "required": [
        "messageName",
        "processInstanceId",
        "status",
        "statusMessage",
        "imagePimNexusAddr",
        "containerCfgPimNexusAddr",
        "message"
    ],
    "properties": {
        "messageName": {
            "type": "string",
        },
        "processInstanceId": {
            "type": "string",
        },
        "status": {
            "type": "string",
            "enum": [
                "ok",
                "error"
            ]
        },
        "statusMessage": {
            "type": "string",
            "enum": [
                "Success",
                "Failure"
            ]
        },
        "imagePimNexusAddr": {
            "type": "string"
        },
        "containerCfgPimNexusAddr": {
            "type": "string"
        },
        "message": {
            "type": "string"
        }
    }
}

TEAMCITY_VALIDATION_START = {
    "schema": {
        "type": "object",
        "required": [
            "alias",
            "ID",
            "messageName",
            "processInstanceId"
        ],
        "properties": {
            "alias": {
                "type": "string"
            },
            "ID": {
                "type": "string"
            },
            "messageName": {
                "type": "string"
            },
            "processInstanceId": {
                "type": "string"
            },
            "factors": {
                "type": "string"
            },
            "spr_addr": {
                "type": "string"
            },
            "df_pth_val": {
                "type": "string"
            },
            "df_pth_dev": {
                "type": "string"
            },
            "df_pth_port": {
                "type": "string"
            },
            "path_out": {
                "type": "string"
            },
            "graf_path": {
                "type": "string"
            },
            "seg": {
                "type": "string"
            },
            "mod": {
                "type": "string"
            },
            "tip": {
                "type": "string"
            },
            "por": {
                "type": "string"
            },
            "tests": {
                "type": "string"
            }
        }
    }
}

TEAMCITY_VALIDATION_STATUS = {
    "type": "object",
    "required": [
        "messageName",
        "processInstanceId",
        "status",
        "statusMessage",
        "first_auto_validation_result",
        "first_auto_validation_report",
        "message"
    ],
    "properties": {
        "messageName": {
            "type": "string"
        },
        "processInstanceId": {
            "type": "string"
        },
        "status": {
            "type": "string",
            "enum": [
                "ok",
                "error"
            ]
        },
        "statusMessage": {
            "type": "string",
            "enum": [
                "Success",
                "Failure"
            ]
        },
        "first_auto_validation_result": {
            "type": "string"
        },
        "first_auto_validation_report": {
            "type": "string"
        },
        "message": {
            "type": "string"
        }
    }
}

MLFLOW_RUNS_CREATE = {
    "type": "object",
    "required": [
        "experiment_id",
        "user",
        "start_time"
    ],
    "properties": {
        "experiment_id": {
            "type": "number"
        },
        "user": {
            "type": "string"
        },
        "start_time": {
            "type": "string"
        }
    }
}

MLFLOW_RUNS_UPDATE = {
    "type": "object",
    "required": [
        "run_id",
        "status",
        "end_time"
    ],
    "properties": {
        "run_id": {
            "type": "string"
        },
        "status": {
            "type": "string"
        },
        "end_time": {
            "type": "string"
        }
    }
}

MLFLOW_LOG_BATCH = {
    "type": "object",
    "required": [
        "run_id",
        "metrics",
        "params"
    ],
    "properties": {
        "run_id": {
            "type": "string"
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string"
                    },
                    "value": {
                        "type": "string"
                    },
                    "timestamp": {
                        "type": "string"
                    }
                }
            }
        },
        "params": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "maximum": 255
                    },
                    "value": {
                        "type": "string",
                        "maximum": 500
                    }
                }
            }
        }
    }
}
