import subprocess
from kubeburner_schema import WorkloadError

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

def label_node_with_label(label,node_count):
    
    cmd = ['oc', 'get', 'node', '-o', 'custom-columns=name:.metadata.name', '--no-headers', '-l', 'node-role.kubernetes.io/workload!='',node-role.kubernetes.io/infra!='',node-role.kubernetes.io/worker=']
    worker_nodes =  subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    worker_node_names = worker_nodes.decode("utf-8")
    worker_node_names = worker_node_names.strip()
    worker_node_names = list(worker_node_names.split("\n"))
    no_of_workers= len(worker_node_names)

    if no_of_workers < node_count:
        return "error", WorkloadError(" Not enough worker nodes to label")
    if no_of_workers <= 0:
        return "error", WorkloadError(" No worker nodes present on the cluster")

    if node_count==0:
        node_count=no_of_workers
    
    workers= worker_node_names[0:node_count]
    workers_to_label= " ".join(workers)

    print("labelling worker nodes with label: ",label)
    cmd = ['oc label node '+ workers_to_label+" "+label+' --overwrite']
    subprocess.check_output(cmd, stderr=subprocess.STDOUT,shell=True)
    return workers_to_label

def unlabel_nodes_with_label(label,nodes_to_unlabel):
    print("Removing {} label from worker nodes".format(label))
    label_key = label.split("=")[0]
    label_key=label_key+"-"
    cmd = ['oc label node '+nodes_to_unlabel+' '+label_key+' --overwrite']
    subprocess.check_output(cmd, stderr=subprocess.STDOUT,shell=True)


def find_running_pod_numbers(labelled_worker_node_names,node_count,pods_per_node,test):
    pod_count=0

    cmd = 'kubectl get pods --field-selector=status.phase=Running -o go-template --template=\'{{range .items}}{{.spec.nodeName}}{{"\\n"}}{{end}}\' -A | awk \'{nodes[$1]++ }END{ for (n in nodes) print n":"nodes[n]}\''
    node_pods= subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    node_pods = node_pods.decode("utf-8")
    node_pods= node_pods.strip()
    node_pods=list(node_pods.split("\n"))
    labelled_worker_names=list(labelled_worker_node_names.split(" "))
    for names in node_pods:
        nodes=names.split(":")
        node_name=nodes[0]
        count=int(nodes[1])
        if node_name in labelled_worker_names:
            pod_count+=count


    total_pod_count= pods_per_node * node_count - pod_count

    if total_pod_count <=0:
        return "error", WorkloadError(" No of pods to deploy <= 0")
    

    if test == "cni" or test == "heavy":
        total_pod_count= int(total_pod_count/2)
    print("Number of pods to deploy on nodes: ",total_pod_count)
    return total_pod_count






