#!/usr/bin/env python3

import re
import sys
import typing
from dataclasses import dataclass, field
from typing import List,Dict,Optional,Annotated
from arcaflow_plugin_sdk import plugin,schema,annotations
import subprocess
import datetime
import yaml


@dataclass
class IndexerConfig:
    Type: str = field(
        metadata={
            "id": "type",
            "name": "Type",
            "description": "Type of indexer",
        }
    )
    esServers: List[str] = field(
        metadata={
            "name": "ESServers",
            "description": "List of ES instances",
        }
    )
    defaultIndex: str = field(
        metadata={
            "name": "DefaultIndex",
            "description": "Default index to send the prometheus metrics into",
        }
    )
    port: Optional[int] = field(
        default=None,
        metadata={
            "name": "Port",
            "description": "indexer port",
        }
    )
    insecureSkipVerify: bool = field(
        default=False,
        metadata={
            "name": "InsecureSkipVerify",
            "description": "TLS certificate verification",
        }
    )
    enabled: bool = field(
        default=False,
        metadata={
            "name": "Enabled",
            "description": "Enable indexing",
        }
    )


@dataclass
class LatencyThreshold:
    conditionType: str = field(
        metadata={
            "name": "ConditionType",
            "description": "ConditionType",
        }
    )
    metric: str = field(
        metadata={
            "name": "Metric",
            "description": "Metric type",
        }
    )
    threshold: Annotated[int, schema.units(schema.UNIT_TIME)] = field(
        metadata={
            "name": "Threshold",
            "description": "Accepted threshold",
        }
    )

@dataclass
class Measurements:
    name: str = field(
        metadata={
            "name": "Name",
            "description": "The name of the measurement",
        }
    )
    thresholds: Optional[LatencyThreshold]  = field(
        default=None,
        metadata={
            "name": "LatencyThreshold",
            "description": "Holds the thresholds configuration",
        }
    )
    esIndex: str = field(
        metadata={
            "name": "ESIndex",
            "description": "The ElasticSearch index used to index the metrics",
        }
    )

@dataclass
class GlobalConfig:
    writeToFile: bool = field(
        default=False,
        metadata={
            "name": "WriteToFile",
            "description": "Whether to dump collected metrics to files",
        }
    )
    indexerConfig: IndexerConfig = field(
        metadata={
            "name": "IndexerConfig",
            "description": "Holds the indexer configuration.",
        }
    )
    measurements: Optional[List[Measurements]] = field(
        default= None,
        metadata={
            "name": "Measurements",
            "description": "List of measurements",
        }
    )
    metricsDirectory: Optional[str] = field(
        default= None,
        metadata={
            "name": "MetricsDirectory",
            "description": "Directory where collected metrics will be dumped into. It will be created if it doesn't exist previously",
        }
    )
    createTarball: Optional[bool] = field(
        default= False,
        metadata={
            "name": "CreateTarball",
            "description": "Create metrics tarball, it has no effect if writeToFile is not enabled",
        }
    )
    requestTimeout: Optional[str] = field(
        default= "15s",
        metadata={
            "name": "RequestTimeout",
            "description": "Client-go request timeout",
        }
    )


@dataclass
class Object:
    objectTemplate: str = field(
        metadata={
            "name": "ObjectTemplate",
            "description": "path to a valid YAML definition of a k8s resource",
        }
    )
    replicas: int = field(
        metadata={
            "name": "Replicas",
            "description": "number of replicas to create of the given object",
        }
    )
    kind: Optional[str] = field(
        default=None,
        metadata={
            "name": "Kind",
            "description": "object kind to delete",
        }
    )
    patchType: Optional[str] = field(
        default=None,
        metadata={
            "name": "PatchType",
            "description": "type of patch mode",
        }
    )
    apiVersion: Optional[str] = field(
        default=None,
        metadata={
            "name": "ApiVersion",
            "description": "apiVersion of the object to remove",
        }
    )
    namespaced: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Namespaced",
            "description": "namespaced",
        }
    )
    inputVars: Optional[Dict[str,schema.ANY_TYPE]] = field(
        default=None,
        metadata={
            "name": "InputVars",
            "description": "contains a map of arbitrary input variables that can be introduced by users",
        }
    )
    labelSelector: Optional[str] = field(
        default=None,
        metadata={
            "name": "LabelSelector",
            "description": "objects with this labels will be removed",
        }
    )


@dataclass
class Job:
    jobIterations: int = field(
        metadata={
            "name": "JobIterations",
            "description": "how many times to execute the job",
        }
    )
    jobIterationDelay: Optional[Annotated[int, schema.units(schema.UNIT_TIME)]] = field(
        default='0s',
        metadata={
            "name": "JobIterationDelay",
            "description": "how much time to wait between each job iteration",
        }
    )
    jobPause: Optional[Annotated[int, schema.units(schema.UNIT_TIME)]] = field(
        default='0s',
        metadata={
            "name": "JobPause",
            "description": "how much time to pause after finishing the job",
        }
    )
    name: str = field(
        metadata={
            "name": "Name",
            "description": "job name",
        }
    )
    jobType: Optional[str] = field(
        default=None,
        metadata={
            "name": "JobType",
            "description": "type of job",
        }
    )
    qps: int = field(
        metadata={
            "name": "QPS",
            "description": "Max number of queries per second",
        }
    )
    burst: int = field(
        metadata={
            "name": "Burst",
            "description": "Maximum burst for throttle",
        }
    )
    namespace: str = field(
        metadata={
            "name": "Namespace",
            "description": "namespace base name to use",
        }
    )
    waitFor: List[str] = field(
        metadata={
            "name": "WaitFor",
            "description": "list of objects to wait for, if not specified wait for all",
        }
    )
    maxWaitTimeout: Annotated[int, schema.units(schema.UNIT_TIME)] = field(
        metadata={
            "name": "MaxWaitTimeout",
            "description": "maximum wait period",
        }
    )
    waitForDeletion: bool = field(
        default=False,
        metadata={
            "name": "WaitForDeletion",
            "description": "wait for objects to be definitively deleted",
        }
    )
    podWait: bool = field(
        metadata={
            "name": "PodWait",
            "description": "wait for all pods to be running before moving forward to the next iteration",
        }
    )
    waitWhenFinished: bool = field(
        metadata={
            "name": "WaitWhenFinished",
            "description": "Wait for pods to be running when all job iterations are completed",
        }
    )
    cleanup: bool = field(
        metadata={
            "name": "Cleanup",
            "description": "clean up old namespaces",
        }
    )
    namespacedIterations: bool = field(
        metadata={
            "name": "NamespacedIterations",
            "description": "create a namespace per job iteration",
        }
    )
    verifyObjects: bool = field(
        metadata={
            "name": "VerifyObjects",
            "description": "verify object count after running the job",
        }
    )
    errorOnVerify: bool = field(
        metadata={
            "name": "ErrorOnVerify",
            "description": "exit when verification fails",
        }
    )
    preLoadImages: bool = field(
        metadata={
            "name": "PreLoadImages",
            "description": " enables pulling all images before running the job",
        }
    )
    preLoadPeriod: Annotated[int, schema.units(schema.UNIT_TIME)] = field(
        metadata={
            "name": "PreLoadPeriod",
            "description": "determines the duration of the preload stage",
        }
    )
    namespaceLabels: Dict[str,str] = field(
        metadata={
            "name": "NamespaceLabels",
            "description": "add custom labels to namespaces created by kube-burner",
        }
    )
    objects: List[Object] = field(
        metadata={
            "name": "Objects",
            "description": "list of objects",
        }
    )


@dataclass
class KubeBurnerInput:
    Global: GlobalConfig = field(
        metadata={
            "id": "global",
            "name": "GlobalConfig",
            "description": "global job configuration parameters",
        }
    )
    jobs: Optional[Job] = field(
        default=None,
        metadata={
            "name": "Job",
            "description": "Kube-burner job configs",
        }
    )


@dataclass
class KubeBurnerOutput:
    """
    This is the data structure for output returned by kube-burner workloads.
    """
    uuid: str = field(metadata={"name": "UUID", "description": "UUID generated for this workload run"})
    output: str = field(metadata={"name": "Kube burner workload output", "description": "Output generated by the kube burner workload"})


@dataclass
class WorkloadError:
    """
    This is the output data structure in the error case.
    """
    exit_code: int = field(metadata={
        "name": "Exit Code", "description": "Exit code returned by the program in case of a failure"})
    error: str = field(metadata={
        "name": "Failure Error", "description": "Reason for failure"})

kube_burner_input_schema = plugin.build_object_schema(KubeBurnerInput)
kube_burner_output_schema = plugin.build_object_schema(KubeBurnerOutput)