#!/usr/bin/env python3

import re
import sys
import typing
from dataclasses import dataclass, field
from typing import List,Dict
from arcaflow_plugin_sdk import plugin,schema
import subprocess
import datetime
import yaml

@dataclass
class KubeBurnerIndexerInputParams:
    """
    This is the data structure for the input parameters for kube-burner indexer.
    """
    collection_time: int = field(metadata={"name": "Time", "description": "Duration for which to collect the prometheus metrics"})
    es_server: str = field(default="https://search-perfscale-dev-chmf5l4sh66lvxbnadi4bznl3a.us-west-2.es.amazonaws.com:443",metadata={"name": "Elasticsearch server url", "description": "URL for your elasticsearch endpoint"})
    es_index: str = field(default="ripsaw-kube-burner",metadata={"name": "Elasticsearch index name", "description": "Elasticsearch index to use for indexing the documents"})
    job_name: str = field(default="kube-burner-indexer",metadata={"name": "Indexer job name", "description": "Name of the job for which metrics are being indexed"})
    writeToFile: bool = field(default="false",metadata={"name": "Write to file", "desscription": "Whether to dump collected metrics to files locally"})

@dataclass
class KubeBurnerCommonInputParams:
    """
    This is the data structure for the common input parameters for kube-burner workloads.
    """
    waitFor: typing.List[str] = field(default_factory=list,metadata={"name": "Wait for ", "desscription":"Wait for the resources of this list to be ready"})
    writeToFile: bool = field(default="false",metadata={"name": "Write to file", "desscription": "Whether to dump collected metrics to files locally"})
    indexing: bool = field(default="true",metadata={"name": "INDEXING", "description": "Enable/disable indexing"})
    es_server: str = field(default="https://search-perfscale-dev-chmf5l4sh66lvxbnadi4bznl3a.us-west-2.es.amazonaws.com:443",metadata={"name": "Elasticsearch server url", "description": "URL for your elasticsearch endpoint"})
    es_index: str = field(default="ripsaw-kube-burner",metadata={"name": "Elasticsearch index name", "description": "Elasticsearch index to use for indexing the documents"})
    qps: int = field(default="20",metadata={"name": "QPS", "description": "Queries/sec"})
    burst: int = field(default="20",metadata={"name": "BURST", "description": "Maximum number of simultaneous queries"})
    podWait: bool = field(default="false",metadata={"name": "POD_WAIT", "description": "Wait for pods to be ready in each iteration"})
    cleanup: bool = field(default="true",metadata={"name": "CLEANUP", "description": "Delete old namespaces for the selected workload before starting benchmark"})
    waitWhenFinished: bool = field(default="true",metadata={"name": "WAIT_WHEN_FINISHED", "description": "Wait after benchmark finishes"})
    verifyObjects: bool = field(default="true",metadata={"name": "VERIFY_OBJECTS", "description": "Verify objects created by kube-burner"})
    errorOnVerify: bool = field(default="true",metadata={"name": "ERROR_ON_VERIFY", "description": "Make kube-burner pod to hang when verification fails"})
    maxWaitTimeout: str = field(default="1h",metadata={"name": "MAX_WAIT_TIMEOUT", "description": "Kube-burner will time out when the pods deployed take more that this value to be ready"})
    preLoadImages: bool = field(default="true",metadata={"name": "PRELOAD_IMAGES", "description": "Preload kube-buner's benchmark images in the cluster"})
    preLoadPeriod: str = field(default="2m",metadata={"name": "PRELOAD_PERIOD", "description": "How long the preload stage will last"})
    podReadyThreshold: str = field(default="5000ms",metadata={"name": "POD_READY_THRESHOLD", "description": "Pod ready latency threshold (only applies to node-density and pod-density workloads)."})
    namespacedIterations: bool = field(default="false",metadata={"name": "NameSpacedIterations", "description": "Number of namespace iterations"})


@dataclass
class KubeBurnerPodDensityInputParams(KubeBurnerCommonInputParams):
    """
    This is the data structure for the input parameters for kube-burner pod-density workload.
    """

    podReadyThreshold: str = field(default="5000ms",metadata={"name": "POD_READY_THRESHOLD", "description": "Pod ready latency threshold (only applies to node-density and pod-density workloads)."})
    podNodeSelector: str = field(default="{node-role.kubernetes.io/worker: }",metadata={"name": "POD_NODE_SELECTOR", "description": "nodeSelector for pods created by the kube-burner workloads"})
    jobIterations: int = field(default="1000",metadata={"name": "TEST_JOB_ITERATIONS", "description": "This variable configures the number of pod-density jobs iterations to perform"})



@dataclass
class KubeBurnerClusterDensityInputParams(KubeBurnerCommonInputParams):
    """
    This is the data structure for the input parameters for kube-burner cluster-density workload.
    """

    podNodeSelector: str = field(default="{node-role.kubernetes.io/worker: }",metadata={"name": "POD_NODE_SELECTOR", "description": "nodeSelector for pods created by the kube-burner workloads"})
    jobIterations: int = field(default="1000",metadata={"name": "TEST_JOB_ITERATIONS", "description": "This variable configures the number of pod-density jobs iterations to perform"})

@dataclass
class KubeBurnerCommonNodeDensityInputParams():
    """
    This is the data structure for common input parameters of kube-burner node-density* workload.
    """

    NODE_COUNT: int = field(metadata={"name": "NODE_COUNT", "description": "Number of worker nodes to deploy the pods on"})
    PODS_PER_NODE: int = field(default="245",metadata={"name": "PODS_PER_NODE", "description": "the maximum number of pods to deploy on each labeled node."})
   

@dataclass
class KubeBurnerNodeDensityInputParams(KubeBurnerCommonInputParams, KubeBurnerCommonNodeDensityInputParams):
    """
    This is the data structure for the input parameters for kube-burner node-density workload.
    """

    #NODE_COUNT: int = field(metadata={"name": "NODE_COUNT", "description": "Number of worker nodes to deploy the pods on"})
    #PODS_PER_NODE: int = field(default="245",metadata={"name": "PODS_PER_NODE", "description": "the maximum number of pods to deploy on each labeled node."})
   

@dataclass
class KubeBurnerNodeDensityHeavyInputParams(KubeBurnerCommonInputParams, KubeBurnerCommonNodeDensityInputParams):
    """
    This is the data structure for the input parameters for kube-burner node-density-heavy density workload.
    """

    #NODE_COUNT: int = field(metadata={"name": "NODE_COUNT", "description": "Number of worker nodes to deploy the pods on"})
    #PODS_PER_NODE: int = field(default="245",metadata={"name": "PODS_PER_NODE", "description": "the maximum number of pods to deploy on each labeled node."})
   

@dataclass
class KubeBurnerNodeDensityCniInputParams(KubeBurnerCommonInputParams, KubeBurnerCommonNodeDensityInputParams):
    """
    This is the data structure for the input parameters for kube-burner node-density-cni density workload.
    """

    #NODE_COUNT: int = field(metadata={"name": "NODE_COUNT", "description": "Number of worker nodes to deploy the pods on"})
    #PODS_PER_NODE: int = field(default="245",metadata={"name": "PODS_PER_NODE", "description": "the maximum number of pods to deploy on each labeled node."})
   

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

kube_burner_indexer_input_schema = plugin.build_object_schema(KubeBurnerIndexerInputParams)
kube_burner_pod_density_input_schema = plugin.build_object_schema(KubeBurnerPodDensityInputParams)
kube_burner_cluster_density_input_schema = plugin.build_object_schema(KubeBurnerPodDensityInputParams)
kube_burner_node_density_input_schema = plugin.build_object_schema(KubeBurnerNodeDensityInputParams)
kube_burner_node_density_heavy_input_schema = plugin.build_object_schema(KubeBurnerNodeDensityHeavyInputParams)
kube_burner_node_density_cni_input_schema = plugin.build_object_schema(KubeBurnerNodeDensityCniInputParams)
kube_burner_output_schema = plugin.build_object_schema(KubeBurnerOutput)