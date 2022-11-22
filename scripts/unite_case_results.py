import argparse
import os
import json
import sys
from glob import glob

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from jobs_launcher.core.config import SESSION_REPORT, TEST_REPORT_NAME_COMPARED, SCREENS_COLLECTION_KEY, VIDEO_KEY, AUDIO_KEY


KEYS_TO_COPY = [
    "min_server_latency", "max_server_latency", "median_server_latency",
    "server_trace_archive",
    "firstinstance_server", "secondinstance_server",
    "iperf_server",
    "used_memory_server",
    "android_log", "second_client_log",
    "used_memory_second_client",
    "second_client_configuration",
    "latency_tool_log_server"
]


def get_test_status(test_status_one, test_status_two):
    test_statuses = (test_status_one, test_status_two)
    statuses = ("skipped", "observed", "error", "failed", "passed")

    for status in statuses:
        if status in test_statuses:
            return status


def format_script_info(script_info):
    client_keys = None
    server_keys = None
    second_client_keys = None
    other_info = []

    for line in script_info:
        if line is None:
            continue

        if line.startswith("Client keys:"):
            client_keys = line
        elif line.startswith("Server keys:"):
            server_keys = line
        elif line.startswith("Second client keys:"):
            second_client_keys = line
        elif line:
            other_info.append(line)

    result = []

    if client_keys:
        result.append(server_keys)
        result.append("")
        result.append(client_keys)
    elif server_keys:
        result.append(server_keys)

    if second_client_keys:
        result.append("")
        result.append(second_client_keys)

    if client_keys or server_keys or second_client_keys:
        result.append("")

    result.extend(other_info)

    return result


def message_remove_on_status(source_list, case_test_status, remove_test_status, message):
    if case_test_status == remove_test_status:
        return [value for value in source_list if value != message]
    else:
        return source_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--target_dir', required=True, metavar="<path>")
    parser.add_argument('--source_dir', required=True, metavar="<path>")
    parser.add_argument('--second_client_dir', required=True, metavar="<path>")

    args = parser.parse_args()

    server_driver_version = None
    first_client_driver_version = None
    second_client_driver_version = None

    for path, dirs, files in os.walk(os.path.abspath(args.target_dir)):
        for file in files:
            if file.endswith(TEST_REPORT_NAME_COMPARED):
                target_file_path = os.path.join(path, file) 

                source_file_path = os.path.join(args.source_dir, os.path.relpath(target_file_path, args.target_dir))

                if os.path.exists(source_file_path):
                    with open(target_file_path, "r") as f:
                        target_file_content = json.load(f)

                    with open(source_file_path, "r") as f:
                        source_file_content = json.load(f)

                    for i in range(len(target_file_content)):
                        for j in range(len(source_file_content)):
                            if target_file_content[i]["test_case"] == source_file_content[j]["test_case"]:
                                source_case = source_file_content[j]
                                break
                        else:
                            raise Exception(f"Can't find test case {target_file_content['test_case']}")

                        for key in KEYS_TO_COPY:
                            if key in source_case:
                                target_file_content[i][key] = source_case[key]

                        target_file_content[i]["test_status"] = get_test_status(target_file_content[i]["test_status"], source_case["test_status"])

                        if "message" in source_case:
                            target_file_content[i]["message"] += source_case["message"]

                        target_file_content[i]["message"] = message_remove_on_status(target_file_content[i]["message"], 
                            target_file_content[i]["test_status"], "error", "Warning! Metrics were calculated with less than 6 blocks")

                        target_file_content[i]["script_info"].extend(source_case["script_info"])

                        target_file_content[i]["script_info"] = format_script_info(target_file_content[i]["script_info"])

                        # Microphone test group: mp4 file is recording on server side
                        if "keys" in source_case and "-microphone true" in source_case["keys"].lower():
                            if VIDEO_KEY in source_case:
                                target_file_content[i][VIDEO_KEY] = source_case[VIDEO_KEY]
                        else:
                            if VIDEO_KEY in source_case:
                                target_file_content[i]["android_" + VIDEO_KEY] = source_case[VIDEO_KEY]

                        if AUDIO_KEY in source_case:
                            target_file_content[i][AUDIO_KEY] = source_case[AUDIO_KEY]

                        if SCREENS_COLLECTION_KEY in source_case:
                            target_file_content[i]["android_" + SCREENS_COLLECTION_KEY] = source_case[SCREENS_COLLECTION_KEY]

                    with open(target_file_path, "w", encoding="utf8") as f:
                        json.dump(target_file_content, f, indent=4, sort_keys=True)

                # get data from second client
                second_client_file_path = os.path.join(args.second_client_dir, os.path.relpath(target_file_path, args.target_dir))

                if os.path.exists(second_client_file_path):
                    with open(target_file_path, "r") as f:
                        target_file_content = json.load(f)

                    with open(second_client_file_path, "r") as f:
                        second_client_file_content = json.load(f)

                    for i in range(len(target_file_content)):
                        for j in range(len(second_client_file_content)):
                            if target_file_content[i]["test_case"] == second_client_file_content[j]["test_case"]:
                                source_case = second_client_file_content[j]
                                break
                        else:
                            raise Exception(f"Can't find test case {target_file_content['test_case']}")

                        for key in KEYS_TO_COPY:
                            if key in source_case:
                                target_file_content[i][key] = source_case[key]

                        target_file_content[i]["test_status"] = get_test_status(target_file_content[i]["test_status"], source_case["test_status"])

                        if "message" in source_case:
                            target_file_content[i]["message"] += source_case["message"]

                        target_file_content[i]["message"] = message_remove_on_status(target_file_content[i]["message"], 
                            target_file_content[i]["test_status"], "error", "Warning! Metrics were calculated with less than 6 blocks")

                        target_file_content[i]["script_info"].extend(source_case["script_info"])

                        target_file_content[i]["script_info"] = format_script_info(target_file_content[i]["script_info"])

                        if VIDEO_KEY in source_case:
                            target_file_content[i]["second_client_" + VIDEO_KEY] = source_case[VIDEO_KEY]

                        if SCREENS_COLLECTION_KEY in source_case:
                            target_file_content[i]["second_client_" + SCREENS_COLLECTION_KEY] = source_case[SCREENS_COLLECTION_KEY]

                    with open(target_file_path, "w", encoding="utf8") as f:
                        json.dump(target_file_content, f, indent=4, sort_keys=True)

            elif file.endswith(SESSION_REPORT):
                target_file_path = os.path.join(path, file) 

                source_file_path = os.path.join(args.source_dir, os.path.relpath(target_file_path, args.target_dir))

                with open(target_file_path, "r") as f:
                    target_file_content = json.load(f)

                if os.path.exists(source_file_path):
                    with open(source_file_path, "r") as f:
                        source_file_content = json.load(f)

                    if "machine_info" in target_file_content:
                        if "driver_version" in target_file_content["machine_info"]:
                            first_client_driver_version = target_file_content["machine_info"]["driver_version"]

                    if "machine_info" in source_file_content:
                        target_file_content["machine_info"] = source_file_content["machine_info"]

                        if "driver_version" in source_file_content["machine_info"]:
                            server_driver_version = source_file_content["machine_info"]["driver_version"]

                    for test_group in target_file_content["results"]:
                        target_group_data = target_file_content["results"][test_group][""]
                        source_group_data = source_file_content["results"][test_group][""]

                        for i in range(len(target_group_data["render_results"])):
                            for j in range(len(source_group_data["render_results"])):
                                if target_group_data["render_results"][i]["test_case"] == source_group_data["render_results"][j]["test_case"]:
                                    source_case = source_group_data["render_results"][j]
                                    break
                            else:
                                raise Exception(f"Can't find test case {target_group_data['render_results'][i]['test_case']}")

                            for key in KEYS_TO_COPY:
                                if key in source_case:
                                    target_group_data["render_results"][i][key] = source_case[key]

                            new_test_status = get_test_status(target_group_data["render_results"][i]["test_status"], source_case["test_status"])
                            old_test_status = target_group_data["render_results"][i]["test_status"]

                            target_group_data[new_test_status] += 1
                            target_group_data[old_test_status] -= 1

                            target_file_content["summary"][new_test_status] += 1
                            target_file_content["summary"][old_test_status] -= 1

                            target_group_data["render_results"][i]["test_status"] = new_test_status

                            if "message" in source_case:
                                target_group_data["render_results"][i]["message"] += source_case["message"]

                            target_group_data["render_results"][i]["message"] = message_remove_on_status(target_group_data["render_results"][i]["message"], 
                                target_group_data["render_results"][i]["test_status"], "error", "Warning! Metrics were calculated with less than 6 blocks")

                            target_group_data["render_results"][i]["script_info"].extend(source_case["script_info"])

                            target_group_data["render_results"][i]["script_info"] = format_script_info(target_group_data["render_results"][i]["script_info"])

                            if VIDEO_KEY in source_case:
                                target_group_data["render_results"][i]["android_" + VIDEO_KEY] = source_case[VIDEO_KEY]

                            if AUDIO_KEY in source_case:
                                target_group_data["render_results"][i][AUDIO_KEY] = source_case[AUDIO_KEY]

                            if SCREENS_COLLECTION_KEY in source_case:
                                target_group_data["render_results"][i]["android_" + SCREENS_COLLECTION_KEY] = source_case[SCREENS_COLLECTION_KEY] 

                # get data from second client
                second_client_file_path = os.path.join(args.second_client_dir, os.path.relpath(target_file_path, args.target_dir))

                if os.path.exists(second_client_file_path):
                    with open(second_client_file_path, "r") as f:
                        second_client_file_content = json.load(f)

                    for test_group in target_file_content["results"]:
                        target_group_data = target_file_content["results"][test_group][""]
                        second_client_group_data = second_client_file_content["results"][test_group][""]

                        if "machine_info" in second_client_file_content:
                            if "driver_version" in second_client_file_content["machine_info"]:
                                second_client_driver_version = second_client_file_content["machine_info"]["driver_version"]

                        for i in range(len(target_group_data["render_results"])):
                            for j in range(len(second_client_group_data["render_results"])):
                                if target_group_data["render_results"][i]["test_case"] == second_client_group_data["render_results"][j]["test_case"]:
                                    source_case = second_client_group_data["render_results"][j]
                                    break
                            else:
                                raise Exception(f"Can't find test case {target_group_data['render_results'][i]['test_case']}")

                            for key in KEYS_TO_COPY:
                                if key in source_case:
                                    target_group_data["render_results"][i][key] = source_case[key]

                            new_test_status = get_test_status(target_group_data["render_results"][i]["test_status"], source_case["test_status"])
                            old_test_status = target_group_data["render_results"][i]["test_status"]

                            target_group_data[new_test_status] += 1
                            target_group_data[old_test_status] -= 1

                            target_file_content["summary"][new_test_status] += 1
                            target_file_content["summary"][old_test_status] -= 1

                            target_group_data["render_results"][i]["test_status"] = new_test_status

                            if "message" in source_case:
                                target_group_data["render_results"][i]["message"] += source_case["message"]

                            target_group_data["render_results"][i]["message"] = message_remove_on_status(target_group_data["render_results"][i]["message"], 
                                target_group_data["render_results"][i]["test_status"], "error", "Warning! Metrics were calculated with less than 6 blocks")

                            target_group_data["render_results"][i]["script_info"].extend(source_case["script_info"])

                            target_group_data["render_results"][i]["script_info"] = format_script_info(target_group_data["render_results"][i]["script_info"])

                            if VIDEO_KEY in source_case:
                                target_group_data["render_results"][i]["second_client_" + VIDEO_KEY] = source_case[VIDEO_KEY]

                            if SCREENS_COLLECTION_KEY in source_case:
                                target_group_data["render_results"][i]["second_client_" + SCREENS_COLLECTION_KEY] = source_case[SCREENS_COLLECTION_KEY] 

                if server_driver_version:
                    target_file_content["machine_info"]["server_driver_version"] = server_driver_version
                else:
                    target_file_content["machine_info"]["server_driver_version"] = None
                if first_client_driver_version:
                    target_file_content["machine_info"]["first_client_driver_version"] = first_client_driver_version
                else:
                    target_file_content["machine_info"]["first_client_driver_version"] = None
                if second_client_driver_version:
                    target_file_content["machine_info"]["second_client_driver_version"] = second_client_driver_version
                else:
                    target_file_content["machine_info"]["second_client_driver_version"] = None

                with open(target_file_path, "w", encoding="utf8") as f:
                    json.dump(target_file_content, f, indent=4, sort_keys=True)


