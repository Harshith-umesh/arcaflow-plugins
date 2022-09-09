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
from common_functions import uuidgen, get_prometheus_creds, label_node_with_label, unlabel_nodes_with_label, find_running_pod_numbers
from kubeburner_schema import KubeBurnerIndexerInputParams, KubeBurnerCommonInputParams, KubeBurnerPodDensityInputParams, KubeBurnerClusterDensityInputParams, KubeBurnerNodeDensityInputParams, KubeBurnerNodeDensityHeavyInputParams, KubeBurnerNodeDensityCniInputParams, KubeBurnerOutput, WorkloadError, kube_burner_cluster_density_input_schema, kube_burner_pod_density_input_schema, kube_burner_cluster_density_input_schema, kube_burner_output_schema


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
    config['global']['writeToFile'] = params.writeToFile

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
                return "error", WorkloadError(f"{error} reading pod-density.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open pod-density.yml")

    config['global']['writeToFile'] = params.writeToFile
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
def RunKubeBurnerClusterDensity(params: KubeBurnerCommonInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Cluster Density Workload ...")
    
    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()

    try:
        with open("workloads/cluster-density/cluster-density.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading cluster-density.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open cluster-density.yml")

    config['global']['writeToFile'] = params.writeToFile
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


@plugin.step(
    id="nodedensity",
    name="Kube-Burner Node Density Workload",
    description="Kube-burner Workload which stresses the cluster by creating sleep pods. Creates a single namespace with a number of Deployments proportional to the calculated number of pod.",
    outputs={"success": KubeBurnerOutput, "error": WorkloadError},
)
def RunKubeBurnerNodeDensity(params: KubeBurnerNodeDensityInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Node Density Workload ...")
    
    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()
    label="node-density=enabled"
    podNodeSelector="{node-density: enabled}"
    test_type="regular"
    labelled_worker_names = label_node_with_label(label,params.NODE_COUNT)
    TEST_JOB_ITERATIONS= find_running_pod_numbers(labelled_worker_names,params.NODE_COUNT,params.PODS_PER_NODE,test_type)


    try:
        with open("workloads/node-density/node-density.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading node-density.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open node-density.yml")

    config['global']['writeToFile'] = params.writeToFile
    config['global']['indexerConfig']['esServers'].append(params.es_server) 
    config['global']['indexerConfig']['defaultIndex'] = params.es_index
    config['global']['indexerConfig']['enabled'] = params.indexing
    config['global']['measurements'][0]['esIndex'] = params.es_index
    config['global']['measurements'][0]['thresholds'][0]['threshold'] = params.podReadyThreshold
    config['jobs'][0]['jobIterations'] = TEST_JOB_ITERATIONS
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
    config['jobs'][0]['objects'][0]['inputVars']['nodeSelector'] = podNodeSelector

    with open('workloads/node-density/node-density-config.yml', 'w') as yaml_file:
        yaml_file.write( yaml.dump(config, default_flow_style=False))

    try:
        cmd=['./kube-burner', 'init', '-c','workloads/node-density/node-density-config.yml', '--uuid='+str(uuid), '-u='+str(prom_url),  '--token='+str(prom_token), '-m=metrics_profiles/metrics.yaml']
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")

    unlabel_nodes_with_label(label, labelled_worker_names)
    print("==>> Kube Burner Node Density Workload complete!")    
    return "success", KubeBurnerOutput(uuid,output)


@plugin.step(
    id="nodedensityheavy",
    name="Kube-Burner Node Density Heavy Workload",
    description="Kube-burner Workload which creates a single namespace with a number of applications proportional to the calculated number of pods / 2. This application consists on two deployments (a postgresql database and a simple client that generates some CPU load) and a service that is used by the client to reach the database.  ",
    outputs={"success": KubeBurnerOutput, "error": WorkloadError},
)
def RunKubeBurnerNodeDensityHeavy(params: KubeBurnerNodeDensityHeavyInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Node Density Heavy Workload ...")
    
    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()
    label="node-density=enabled"
    podNodeSelector="{node-density: enabled}"
    test_type="heavy"
    labelled_worker_names = label_node_with_label(label,params.NODE_COUNT)
    TEST_JOB_ITERATIONS= find_running_pod_numbers(labelled_worker_names,params.NODE_COUNT,params.PODS_PER_NODE,test_type)


    try:
        with open("workloads/node-density-heavy/node-density-heavy.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading node-density-heavy.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open node-density-heavy.yml")

    config['global']['writeToFile'] = params.writeToFile
    config['global']['indexerConfig']['esServers'].append(params.es_server) 
    config['global']['indexerConfig']['defaultIndex'] = params.es_index
    config['global']['indexerConfig']['enabled'] = params.indexing
    config['global']['measurements'][0]['esIndex'] = params.es_index
    config['jobs'][0]['jobIterations'] = TEST_JOB_ITERATIONS
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
    config['jobs'][0]['objects'][0]['inputVars']['nodeSelector'] = podNodeSelector
    config['jobs'][0]['objects'][1]['inputVars']['nodeSelector'] = podNodeSelector

    with open('workloads/node-density-heavy/node-density-heavy-config.yml', 'w') as yaml_file:
        yaml_file.write( yaml.dump(config, default_flow_style=False))

    try:
        cmd=['./kube-burner', 'init', '-c','workloads/node-density-heavy/node-density-heavy-config.yml', '--uuid='+str(uuid), '-u='+str(prom_url),  '--token='+str(prom_token), '-m=metrics_profiles/metrics.yaml']
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")

    unlabel_nodes_with_label(label, labelled_worker_names)
    print("==>> Kube Burner Node Density Heavy Workload complete!")    
    return "success", KubeBurnerOutput(uuid,output)


@plugin.step(
    id="nodedensitycni",
    name="Kube-Burner Node Density CNI Workload",
    description="Kube-burner Workload which creates a single namespace with a number of applications equals to job_iterations. This application consists on two deployments (a node.js webserver and a simple client that curls the webserver) and a service that is used by the client to reach the webserver.",
    outputs={"success": KubeBurnerOutput, "error": WorkloadError},
)
def RunKubeBurnerNodeDensityCni(params: KubeBurnerNodeDensityCniInputParams ) -> typing.Tuple[str, typing.Union[KubeBurnerOutput, WorkloadError]]:

    print("==>> Running Kube Burner Node Density CNI Workload ...")
    
    uuid = uuidgen()
    prom_url , prom_token = get_prometheus_creds()
    label="node-density=enabled"
    podNodeSelector="{node-density: enabled}"
    test_type="cni"
    labelled_worker_names = label_node_with_label(label,params.NODE_COUNT)
    TEST_JOB_ITERATIONS= find_running_pod_numbers(labelled_worker_names,params.NODE_COUNT,params.PODS_PER_NODE,test_type)

    try:
        with open("workloads/node-density-cni/node-density-cni.yml", "r") as input:
            try:
                config = yaml.safe_load(input)
            except yaml.YAMLError as error:
                return "error", WorkloadError(f"{error} reading node_density-cni.yml")
    except EnvironmentError as error:
            return "error", WorkloadError(f"{error} while trying to open node_density-cni.yml")

    config['global']['writeToFile'] = params.writeToFile
    config['global']['indexerConfig']['esServers'].append(params.es_server) 
    config['global']['indexerConfig']['defaultIndex'] = params.es_index
    config['global']['indexerConfig']['enabled'] = params.indexing
    config['global']['measurements'][0]['esIndex'] = params.es_index
    config['jobs'][0]['jobIterations'] = TEST_JOB_ITERATIONS
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
    config['jobs'][0]['objects'][0]['inputVars']['nodeSelector'] = podNodeSelector
    config['jobs'][0]['objects'][1]['inputVars']['nodeSelector'] = podNodeSelector

    with open('workloads/node-density-cni/node-density-cni-config.yml', 'w') as yaml_file:
        yaml_file.write( yaml.dump(config, default_flow_style=False))

    try:
        cmd=['./kube-burner', 'init', '-c','workloads/node-density-cni/node-density-cni-config.yml', '--uuid='+str(uuid), '-u='+str(prom_url),  '--token='+str(prom_token), '-m=metrics_profiles/metrics.yaml']
        process_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        return "error", WorkloadError(error.returncode,"{} failed with return code {}:\n{}".format(error.cmd[0],error.returncode,error.output))

    output = process_out.decode("utf-8")

    unlabel_nodes_with_label(label, labelled_worker_names)
    print("==>> Kube Burner Node Density CNI Workload complete!")    
    return "success", KubeBurnerOutput(uuid,output)

if __name__ == "__main__":
    sys.exit(plugin.run(plugin.build_schema(
        RunKubeBurnerIndexer,
        RunKubeBurnerPodDensity,
        RunKubeBurnerClusterDensity,
        RunKubeBurnerNodeDensity,
        RunKubeBurnerNodeDensityHeavy,
        RunKubeBurnerNodeDensityCni
    )))
