#!/usr/bin/env sh
set -ex

# This script expects the following env vars to bbe present:
# CIRCLE_BRANCH
# DEV_RANCHER_ENDPOINT
# DEV_RANCHER_BEARER_TOKEN
# DEV_RANCHER_CLUSTER_PROJECT_ID
# DEV_RANCHER_PROJECT

RANCHER_ENDPOINT="https://elbecerro.unicef.io/v3"


if [ "$CIRCLE_BRANCH" = "develop" ]; then
    RANCHER_ENDPOINT="https://elbecerro.unicef.io/v3"
    RANCHER_BEARER_TOKEN=$DEV_RANCHER_BEARER_TOKEN
    RANCHER_CLUSTER_PROJECT_ID=$DEV_RANCHER_CLUSTER_PROJECT_ID
    RANCHER_PROJECT="etools-dev"
    for workload in 'web-dev' 'worker-dev' 'beater-dev' 'worker-vision-dev' ;
        do
             RANCHER_UPGRADE_URL="${RANCHER_ENDPOINT}/project/${RANCHER_CLUSTER_PROJECT_ID}/workloads/deployment:${RANCHER_PROJECT}:$workload"
             pod_upgrade_body=$(curl -s "${RANCHER_UPGRADE_URL}" -X GET -H "Authorization: Bearer ${RANCHER_BEARER_TOKEN}" 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'content-type: application/json' -H 'accept: application/json' 2>&1 | sed  "s/\"cattle\.io\/timestamp\"\:\"[0-9T:Z-]*\"/\"cattle\.io\/timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"/g")
             curl "$RANCHER_UPGRADE_URL" -X PUT -H "Authorization: Bearer ${RANCHER_BEARER_TOKEN}" -H 'Connection: keep-alive' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'content-type: application/json' -H 'accept: application/json' --data-binary "$pod_upgrade_body" --compressed
        done
    # check if this will work
    RANCHER_UPGRADE_URL="${RANCHER_ENDPOINT}/project/${RANCHER_CLUSTER_PROJECT_ID}/workloads/job:${RANCHER_PROJECT}:$workload"
    pod_upgrade_body=$(curl -s "${RANCHER_UPGRADE_URL}" -X GET -H "Authorization: Bearer ${RANCHER_BEARER_TOKEN}" 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'content-type: application/json' -H 'accept: application/json' 2>&1 | sed  "s/\"cattle\.io\/timestamp\"\:\"[0-9T:Z-]*\"/\"cattle\.io\/timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"/g")
    curl "$RANCHER_UPGRADE_URL" -X PUT -H "Authorization: Bearer ${RANCHER_BEARER_TOKEN}" -H 'Connection: keep-alive' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'content-type: application/json' -H 'accept: application/json' --data-binary "$pod_upgrade_body" --compressed


elif [ "$CIRCLE_BRANCH" = "staging" ]; then
    echo "staging"
fi