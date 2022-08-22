#!/usr/bin/env python3

import re
import sys
import typing
from dataclasses import dataclass, field
from typing import List,Dict
from arcaflow_plugin_sdk import plugin,schema
import subprocess
import datetime


@dataclass
class KubeBurnerIndexerInputParams:
    """
    This is the data structure for the input parameters for kube-burner indexer.
    """
    collection_time: int = field(metadata={"name": "Time", "description": "Duration for which to collect the prometheus metrics"})
    es_server: str = field(default="https://search-perfscale-dev-chmf5l4sh66lvxbnadi4bznl3a.us-west-2.es.amazonaws.com:443",metadata={"name": "Elasticsearch server url", "description": "URL for your elasticsearch endpoint"})
    es_index: str = field(default="ripsaw-kube-burner",metadata={"name": "Elasticsearch index name", "description": "Elasticsearch index to use for indexing the documents"})

@dataclass
class KubeBurnerIndexerOutput:
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
kube_burner_indexer_output_schema = plugin.build_object_schema(KubeBurnerIndexerOutput)


@plugin.step(
    id="kubeburnerindexer",
    name="Kube-Burner Indexer Workload",
    description="Collect and index Prometheus metrics for a specified time period",
    outputs={"success": KubeBurnerIndexerOutput, "error": WorkloadError},
)
def RunKubeBurnerIndexer(params: KubeBurnerIndexerInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerIndexerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Indexer to collect metrics over the last {} minutes ...".format(params.collection_time))
    
    cmd="uuidgen"
    uuid = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    uuid = uuid.decode("utf-8")
    print(uuid)

    cmd='oc get route -n openshift-monitoring prometheus-k8s -o jsonpath="{.spec.host}"'
    prom_url= subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    prom_url = prom_url.decode("utf-8")
    prom_url="https://"+prom_url
    print(prom_url)

    cmd='oc -n openshift-monitoring sa get-token prometheus-k8s'
    prom_token= subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    prom_token = prom_token.decode("utf-8")
    print(prom_token)

    current_time = datetime.datetime.now() 
    time_duration = current_time - datetime.timedelta(minutes=params.collection_time)
    start_ts = int(time_duration.timestamp())  
    current_ts= int(datetime.datetime.now().timestamp())
    print(current_ts,start_ts)


    try:
        cmd=['./kube-burner', 'index', '-c','configs/kubeburner_indexer.yml', '--uuid='+str(uuid), '-u='+str(prom_url), '--job-name', 'kube-burner-indexer', '--token='+str(prom_token), '-m=configs/metrics.yml', '--start',start_ts, '--end', current_ts]
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")


    print("==>> Kube Burner Indexing complete!")
    
    return "success", KubeBurnerIndexerOutput(uuid,output)
    



if __name__ == "__main__":
    sys.exit(plugin.run(plugin.build_schema(
        RunKubeBurnerIndexer
    )))
