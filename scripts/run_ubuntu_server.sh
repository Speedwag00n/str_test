#!/bin/bash
FILE_FILTER=$1
TESTS_FILTER=$2
IP_ADDRESS=$3
COMMUNICATION_PORT=$4
SCREEN_RESOLUTION=$5
SERVER_GPU_NAME="none"
SERVER_OS_NAME="none"
GAME_NAME=$6
COLLECT_TRACES=${7:-False}
RETRIES=1
EXECUTION_TYPE="server"

python3.9 prepare_xmls.py --os_name "Ubuntu"
python3.9 prepare_test_cases.py --os_name "Ubuntu"

python3.9 -m pip install -r ./requirements-ubuntu.txt

python3.9 ../jobs_launcher/executeTests.py --test_filter $TESTS_FILTER --file_filter $FILE_FILTER --tests_root ../jobs --work_root ../Work/Results --work_dir StreamingSDK --cmd_variables clientTool "../StreamingSDK" serverTool "../StreamingSDK" executionType $EXECUTION_TYPE ipAddress $IP_ADDRESS communicationPort $COMMUNICATION_PORT retries $RETRIES serverGPUName $SERVER_GPU_NAME serverOSName $SERVER_OS_NAME gameName $GAME_NAME collectTraces $COLLECT_TRACES screenResolution $SCREEN_RESOLUTION
