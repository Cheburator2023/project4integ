FROM nexus-ci.corp.dev.vtb/sumd-docker-lib/sum-validation:2.1

#RUN yum install -y jq git curl

COPY validation-pipeline /validation-pipeline
RUN chmod -R 777 /validation-pipeline && chmod +x /validation-pipeline/*

WORKDIR /validation-pipeline
