FROM quay.io/centos/centos:stream8

RUN dnf -y module install python39 && dnf -y install python39 python39-pip 
RUN curl -LsS https://github.com/cloud-bulldozer/kube-burner/releases/download/v0.14.2/kube-burner-0.14.2-Linux-x86_64.tar.gz | tar xz
RUN mkdir /app
ADD kubeburner_plugin.py /app
ADD test_kubeburner_plugin.py /app
ADD requirements.txt /app
ADD configs /app/configs/
WORKDIR /app

RUN pip3 install -r requirements.txt
RUN python3.9 test_kubeburner_plugin.py

ENTRYPOINT ["python3.9", "/app/kubeburner_plugin.py"]
CMD []

LABEL org.opencontainers.image.title="Kube-burner Arcalot Plugin"
LABEL org.opencontainers.image.source="https://github.com/arcalot/arcaflow-plugins/tree/main/python/kube-burner"
LABEL org.opencontainers.image.licenses="Apache-2.0+GPL-2.0-only"
LABEL org.opencontainers.image.vendor="Arcalot project"
LABEL org.opencontainers.image.authors="Arcalot contributors"
LABEL io.github.arcalot.arcaflow.plugin.version="1" 