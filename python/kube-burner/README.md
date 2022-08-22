# sysbench workload plugin for Arcaflow

arca-kube-burner is a workload plugin of the [kube-burner](https://github.com/cloud-bulldozer/kube-burner) benchmark tool
using the [Arcaflow python SDK](https://github.com/arcalot/arcaflow-plugin-sdk-python).


## To test:

In order to run the [kube-burner plugin](kube-burner-plugin.py) run the following steps:

1. Clone this repository
2. Create a `venv` in the current directory with `python3 -m venv $(pwd)/venv`
3. Activate the `venv` by running `source venv/bin/activate`
4. Run `pip install -r requirements.txt`
5. Run `./kubeburner_plugin.py -f configs/indexer_example.yaml`
