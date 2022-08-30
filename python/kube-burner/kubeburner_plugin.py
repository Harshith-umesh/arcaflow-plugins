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


@dataclass
class KubeBurnerCommonInputParams:
    """
    This is the data structure for the common input parameters for kube-burner workloads.
    """
    waitFor: typing.List[str]
    indexing: bool = field(default="true",metadata={"name": "INDEXING", "description": "Enable/disable indexing"})
    es_server: str = field(default="https://search-perfscale-dev-chmf5l4sh66lvxbnadi4bznl3a.us-west-2.es.amazonaws.com:443",metadata={"name": "Elasticsearch server url", "description": "URL for your elasticsearch endpoint"})
    es_index: str = field(default="ripsaw-kube-burner",metadata={"name": "Elasticsearch index name", "description": "Elasticsearch index to use for indexing the documents"})
    jobIterations: int = field(default="1000",metadata={"name": "TEST_JOB_ITERATIONS", "description": "This variable configures the number of pod-density jobs iterations to perform"})
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
    podNodeSelector: str = field(default="{node-role.kubernetes.io/worker: }",metadata={"name": "POD_NODE_SELECTOR", "description": "nodeSelector for pods created by the kube-burner workloads"})
    podReadyThreshold: str = field(default="5000ms",metadata={"name": "POD_READY_THRESHOLD", "description": "Pod ready latency threshold (only applies to node-density and pod-density workloads)."})
    namespacedIterations: bool = field(default="false",metadata={"name": "NameSpacedIterations", "description": "Number of namespace iterations"})


@dataclass
class KubeBurnerPodDensityInputParams:
    """
    This is the data structure for the input parameters for kube-burner pod density workload.
    """

    pod_density_params: KubeBurnerCommonInputParams
    podReadyThreshold: str = field(default="5000ms",metadata={"name": "POD_READY_THRESHOLD", "description": "Pod ready latency threshold (only applies to node-density and pod-density workloads)."})
   


@dataclass
class KubeBurnerClusterDensityInputParams:
    """
    This is the data structure for the input parameters for kube-burner cluster density workload.
    """

    cluster_density_params: KubeBurnerCommonInputParams   


@dataclass
class KubeBurnerOutput:
    """
    This is the data structure for output returned by the kube-burner indexer.
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
kube_burner_output_schema = plugin.build_object_schema(KubeBurnerOutput)

def uuidgen():
    cmd=['uuidgen']
    uuid = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    uuid = uuid.decode("utf-8")
    uuid=uuid.strip()
    return uuid

def get_prometheus_creds():
    cmd=['oc', 'get', 'route', '-n', 'openshift-monitoring', 'prometheus-k8s', '-o', 'jsonpath="{.spec.host}"' ]
    prom_url= subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    prom_url = prom_url.decode("utf-8")
    prom_url = prom_url.strip('\"')
    prom_url="https://"+prom_url

    cmd=['oc', '-n', 'openshift-monitoring', 'sa', 'get-token', 'prometheus-k8s']
    prom_token= subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    prom_token = prom_token.decode("utf-8")

    return prom_url,prom_token


@plugin.step(
    id="indexer",
    name="Kube-Burner Indexer Workload",
    description="Collect and index Prometheus metrics for a specified time period",
    outputs={"success": KubeBurnerOutput, "error": WorkloadError},
)
def RunKubeBurnerIndexer(params: KubeBurnerIndexerInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Indexer to collect metrics over the last {} minutes ...".format(params.collection_time))
    
    try:
        with open("workloads/indexer/kubeburner_indexer.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading kubeburner_indexer.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open kubeburner_indexer.yml")

    config['global']['indexerConfig']['esServers'].append(params.es_server) 
    config['global']['indexerConfig']['defaultIndex'] = params.es_index

    with open('workloads/indexer/kubeburner_indexer.yml', 'w') as yaml_file:
        yaml_file.write( yaml.dump(config, default_flow_style=False))

    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()

    current_time = datetime.datetime.now() 
    time_duration = current_time - datetime.timedelta(minutes=params.collection_time)
    start_ts = str(int(time_duration.timestamp()))
    current_ts= str(int(datetime.datetime.now().timestamp()))

    try:
        cmd=['./kube-burner', 'index', '-c','workloads/indexer/kubeburner_indexer.yml', '--uuid='+str(uuid), '-u='+str(prom_url), '--job-name', params.job_name, '--token='+str(prom_token), '-m=metrics_profiles/indexer_metrics.yaml', '--start',start_ts, '--end', current_ts]
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")

    print("==>> Kube Burner Indexing complete! Metrics stored at elasticsearch server {} on index {} with UUID {} and jobName: {}".format(params.es_server,params.es_index,uuid,params.job_name))    
    return "success", KubeBurnerOutput(uuid,output)

@plugin.step(
    id="poddensity",
    name="Kube-Burner Pod Density Workload",
    description="Kube-burner Workload which stresses the cluster by creating sleep pods",
    outputs={"success": KubeBurnerOutput, "error": WorkloadError},
)
def RunKubeBurnerPodDensity(params: KubeBurnerPodDensityInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Pod Density Workload ...")
    
    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()

    try:
        with open("workloads/pod-density/pod-density.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading pod_density.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open pod_density.yml")

    config['global']['indexerConfig']['esServers'].append(params.es_server) 
    config['global']['indexerConfig']['defaultIndex'] = params.es_index
    config['global']['indexerConfig']['enabled'] = params.indexing
    config['global']['measurements'][0]['esIndex'] = params.es_index
    config['global']['measurements'][0]['thresholds'][0]['threshold'] = params.podReadyThreshold
    config['jobs'][0]['jobIterations'] = params.jobIterations
    config['jobs'][0]['qps'] = params.qps
    config['jobs'][0]['burst'] = params.burst
    config['jobs'][0]['namespacedIterations'] = params.namespacedIterations
    config['jobs'][0]['namespace'] = uuid
    config['jobs'][0]['podWait'] = params.podWait
    config['jobs'][0]['cleanup'] = params.cleanup
    config['jobs'][0]['waitFor'] = params.waitFor
    config['jobs'][0]['waitWhenFinished'] = params.waitWhenFinished
    config['jobs'][0]['verifyObjects'] = params.verifyObjects
    config['jobs'][0]['errorOnVerify'] = params.errorOnVerify
    config['jobs'][0]['maxWaitTimeout'] = params.maxWaitTimeout
    config['jobs'][0]['preLoadImages'] = params.preLoadImages
    config['jobs'][0]['preLoadPeriod'] = params.preLoadPeriod
    config['jobs'][0]['objects'][0]['inputVars']['nodeSelector'] = params.podNodeSelector

    with open('workloads/pod-density/pod-density-config.yml', 'w') as yaml_file:
        yaml_file.write( yaml.dump(config, default_flow_style=False))

    try:
        cmd=['./kube-burner', 'init', '-c','workloads/pod-density/pod-density-config.yml', '--uuid='+str(uuid), '-u='+str(prom_url),  '--token='+str(prom_token), '-m=metrics_profiles/metrics.yaml']
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")

    print("==>> Kube Burner Pod Density Workload complete!")    
    return "success", KubeBurnerOutput(uuid,output)

@plugin.step(
    id="clusterdensity",
    name="Kube-Burner Cluster Density Workload",
    description="Kube-burner Workload which stresses the cluster by creating different resources",
    outputs={"success": KubeBurnerOutput, "error": WorkloadError},
)
def RunKubeBurnerClusterDensity(params: KubeBurnerClusterDensityInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Cluster Density Workload ...")
    
    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()

    try:
        with open("workloads/cluster-density/cluster-density.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading cluster_density.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open cluster_density.yml")

    config['global']['indexerConfig']['esServers'].append(params.es_server) 
    config['global']['indexerConfig']['defaultIndex'] = params.es_index
    config['global']['indexerConfig']['enabled'] = params.indexing
    config['global']['measurements'][0]['esIndex'] = params.es_index
    config['jobs'][0]['jobIterations'] = params.jobIterations
    config['jobs'][0]['qps'] = params.qps
    config['jobs'][0]['burst'] = params.burst
    config['jobs'][0]['namespacedIterations'] = params.namespacedIterations
    config['jobs'][0]['namespace'] = uuid
    config['jobs'][0]['podWait'] = params.podWait
    config['jobs'][0]['cleanup'] = params.cleanup
    config['jobs'][0]['waitFor'] = params.waitFor
    config['jobs'][0]['waitWhenFinished'] = params.waitWhenFinished
    config['jobs'][0]['verifyObjects'] = params.verifyObjects
    config['jobs'][0]['errorOnVerify'] = params.errorOnVerify
    config['jobs'][0]['maxWaitTimeout'] = params.maxWaitTimeout
    config['jobs'][0]['preLoadImages'] = params.preLoadImages
    config['jobs'][0]['preLoadPeriod'] = params.preLoadPeriod
    config['jobs'][0]['objects'][1]['inputVars']['nodeSelector'] = params.podNodeSelector
    config['jobs'][0]['objects'][2]['inputVars']['nodeSelector'] = params.podNodeSelector

    with open('workloads/cluster-density/cluster-density-config.yml', 'w') as yaml_file:
        yaml_file.write( yaml.dump(config, default_flow_style=False))

    try:
        cmd=['./kube-burner', 'init', '-c','workloads/cluster-density/cluster-density-config.yml', '--uuid='+str(uuid), '-u='+str(prom_url),  '--token='+str(prom_token), '-m=metrics_profiles/metrics.yaml']
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")

    print("==>> Kube Burner Cluster Density Workload complete!")    
    return "success", KubeBurnerOutput(uuid,output)

if __name__ == "__main__":
    sys.exit(plugin.run(plugin.build_schema(
        RunKubeBurnerIndexer,
        RunKubeBurnerPodDensity,
        RunKubeBurnerClusterDensity
    )))
