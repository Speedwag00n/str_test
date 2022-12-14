import socket
import sys
import os
from time import sleep
import traceback
import json
from instance_state import ClientInstanceState
from actions import ClientActionException
from client_actions import *
import psutil
from utils import *
from subprocess import PIPE, STDOUT
import json
from analyzeLogs import analyze_logs
from streaming_actions import close_streaming, StreamingType

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *
MC_CONFIG = get_mc_config()


# mapping of commands and their implementations
ACTIONS_MAPPING = {
    "execute_cmd": ExecuteCMD,
    "check_window": CheckWindow,
    "check_game": CheckWindow,
    "press_keys_server": PressKeysServer,
    "abort": Abort,
    "retry": Retry,
    "next_case": NextCase,
    "click_server": ClickServer,
    "start_test_actions_client": StartTestActionsClient,
    "start_test_actions_server": StartTestActionsServer,
    "make_screen": MakeScreen,
    "record_video": RecordVideo,
    "move": Move,
    "click": Click,
    "sleep": DoSleep,
    "parse_keys": PressKeys,
    "sleep_and_screen": SleepAndScreen,
    "skip_if_done": SkipIfDone,
    "record_metrics": RecordMetrics,
    "record_audio": RecordMicrophone,
    "start_streaming": StartStreaming,
    "start_latency_tool": StartLatencyTool,
    "open_game": OpenGame
}


# Client controls test case execution. 
# It inits communication, decides to do next case, retry or restart at all the current case.
# Client reads list of actions and executes them one by one.
# It sends actions which must be executed on server to it.
# Also client does screenshots and records video.
def start_client_side_tests(args, case, process, last_log_line, audio_device_name, current_try, error_messages, script_path=None):
    output_path = os.path.join(args.output, "Color")

    screen_path = os.path.join(output_path, case["case"])
    if not os.path.exists(screen_path):
        os.makedirs(screen_path)

    archive_path = os.path.join(args.output, "gpuview")
    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

    archive_name = case["case"]
    game_name = args.game_name

    response = None

    # Connect to server to sync autotests
    main_logger.info("Start trying to connect to server: {}".format(case["case"]))

    while True:
        try:
            sock = socket.socket()
            sock.connect((args.ip_address, int(args.communication_port)))
            sock.send("ready".encode("utf-8"))
            response = sock.recv(1024).decode("utf-8")
            break
        except Exception:
            main_logger.info("Could not connect to server. Try it again")

    params = {}

    try:
        if "client_clumsy_keys" in case:
            start_clumsy(case["client_clumsy_keys"], server_ip=args.ip_address)

        # create state object
        instance_state = ClientInstanceState()

        # Client init communication:
        # 1. Client sends 'ready' to server
        # 2. Server sends 'windows' or 'ubuntu' to client
        # 3. Client starts doing actions

        if response == "windows" or response == "ubuntu":
            # get list of actions for the current game / benchmark
            if response == "windows":
                actions_key = "{}_actions".format(game_name.lower())
            else:
                actions_key = "{}_actions_ubuntu".format(game_name.lower())

            if actions_key in case:
                actions = case[actions_key]
            else:
                # use default list of actions if some specific list of actions doesn't exist
                with open(os.path.abspath(args.common_actions_path), "r", encoding="utf-8") as common_actions_file:
                    actions = json.load(common_actions_file)[actions_key]

            # Replacing record_video command to record_audio
            if "server_keys" in case and "-microphone true" in case["server_keys"].lower():
                for i in range(len(actions)):
                    if "record_video" in actions[i]:
                        if "-audiofile" in case["server_keys"].lower():
                            actions.insert(i+1, actions[i].replace("record_video", "record_audio"))
                        else:
                            actions[i] = actions[i].replace("record_video", "record_audio")

            # build params dict with all necessary variables for test actions
            params["output_path"] = output_path
            params["screen_path"] = screen_path
            params["archive_path"] = archive_path
            params["current_image_num"] = 1
            params["current_try"] = current_try
            params["audio_device_name"] = audio_device_name
            params["args"] = args
            params["case"] = case
            params["game_name"] = game_name
            params["client_type"] = "win_client"
            params["messages"] = error_messages
            if args.streaming_type != StreamingType.AMD_LINK:
                params["transport_protocol"] = getTransportProtocol(args, case)
            params["script_path"] = script_path
            params["process"] = process
            params["case_json_path"] = os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX)

            # execute actions one by one
            for action in actions:
                # skip some actions if it's necessary (e.g. actions to open a game / benchmark)
                if instance_state.commands_to_skip > 0:
                    instance_state.commands_to_skip -= 1
                    continue

                main_logger.info("Current action: {}".format(action))
                main_logger.info("Current state:\n{}".format(instance_state.format_current_state()))

                # split action to command and arguments
                parts = action.split(" ", 1)
                command = parts[0]
                if len(parts) > 1:
                    arguments_line = parts[1]
                else:
                    arguments_line = None

                params["action_line"] = action
                params["command"] = command
                params["arguments_line"] = arguments_line

                # find necessary command and execute itd
                if command in ACTIONS_MAPPING:
                    command_object = ACTIONS_MAPPING[command](sock, params, instance_state, main_logger)
                    command_object.do_action()

                    # Save Streaming process for feature cases
                    # e.g. it's necessary Connection test group where Streaming instance can be alive during few test cases
                    if command == "start_streaming":
                        process = command_object.process
                else:
                    raise ClientActionException("Unknown client command: {}".format(command))

                main_logger.info("Finish action execution\n\n\n")

            process = close_streaming(args, case, process)

            # say server to start next case
            main_logger.info("Send NextCase command")
            command_object = NextCase(sock, params, instance_state, main_logger)
            command_object.do_action()

            if "Latency" in args.test_group and args.game_name == "Empty":
                close_latency_tool(args.execution_type)

            last_log_line = save_logs(args, case, last_log_line, current_try)

            if "Latency" in args.test_group and args.game_name == "Empty":
                latency_log_path = save_latency_tool_logs(args, case, current_try)
            else:
                latency_log_path = None

            with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "r") as file:
                json_content = json.load(file)[0]

            if latency_log_path:
                analyze_latency_tool_logs(json_content, latency_log_path)

            # check that encryption is valid
            if json_content["test_status"] == "observed":
                pass
            elif contains_encryption_errors(error_messages):
                json_content["test_status"] = "error"
            else:
                json_content["test_status"] = "passed"

            json_content["message"] = json_content["message"] + list(error_messages)

            analyze_logs(args.output, json_content, case, execution_type="windows_client", streaming_type=args.streaming_type)

            # execute iperf if it's necessary
            main_logger.info("Send iperf command")
            command_object = IPerf(sock, params, instance_state, main_logger)
            command_object.do_action()

            if "iperf_executed" in params and params["iperf_executed"]:
                logs_path = "tool_logs"
                json_content["iperf_result"] = os.path.join(logs_path, case["case"] + "_iperf.log")

            with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "w") as file:
                json.dump([json_content], file, indent=4)

        else:
            raise Exception("Unknown server answer: {}".format(response))
    except Exception as e:
        instance_state.prev_action_done = False
        main_logger.error("Fatal error. Case will be aborted: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        raise e
    finally:
        if not instance_state.prev_action_done:
            # client or server Streaming SDK instance isn't alive. Retry the current case
            if instance_state.non_workable_client or instance_state.non_workable_server:
                command_object = Retry(sock, params, instance_state, main_logger)
                command_object.do_action()
            else:
                # some case failed on client at all during execution. Sent signal to server and retry
                instance_state.is_aborted_client = True
                command_object = Abort(sock, params, instance_state, main_logger)
                command_object.do_action()
        elif instance_state.is_aborted_server:
            # some case failed on server at all during execution. Server doesn't require to receive signal
            pass

        sock.close()

        if "client_clumsy_keys" in case and ("keep_client_clumsy" not in case or not case["keep_client_clumsy"]):
            close_clumsy()

    return process, last_log_line
