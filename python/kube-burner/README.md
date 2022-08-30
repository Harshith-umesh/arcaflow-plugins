# Kube-burner workload plugin for Arcaflow

arca-kube-burner is a workload plugin of the [kube-burner](https://github.com/cloud-bulldozer/kube-burner) benchmark tool
using the [Arcaflow python SDK](https://github.com/arcalot/arcaflow-plugin-sdk-python).

Kube-burner indexer is a tool which can collect prometheus metrics for a given time period. An elasticsearch server URL and index need to be provided to where the indexer will write the data to.
Which metrics to collect is defined in the [metrics config file](configs/metrics.yaml).
Please refer to the [example config](configs/indexer_example.yml) to see the necessary input parameters. collection_time parameter defines the time duration for which to collect the prometheus metrics. 

Documentation for Pod Density and Cluster Density wokrlods can be found here: [Workloads Documentation](https://github.com/cloud-bulldozer/e2e-benchmarking/blob/master/workloads/kube-burner/README.md)

### Note: The plugin should be able to access the kubeconfig of your kubernetes/openshift cluster and kube-burner binary must be downloaded locally.

## To test:

In order to run the [kube-burner plugin](kube-burner-plugin.py) run the following steps:

1. Clone this repository
2. Create a `venv` in the current directory with `python3 -m venv $(pwd)/venv`
3. Activate the `venv` by running `source venv/bin/activate`
4. Run `pip install -r requirements.txt`
5. To run kube-burner indexer `./kubeburner_plugin.py -f workloads/indexer_example.yaml -s indexer`
6. To run kube-burner pod-density workload `./kubeburner_plugin.py -f workloads/pod-density/pod_density_example.yml -s poddensity`
7. To run kube-burner cluster-density workload `./kubeburner_plugin.py -f workloads/cluster-density/cluster_density_example.yml -s clusterdensity`