from time import sleep
import psutil
import os
from glob import glob
import zipfile
import subprocess
from subprocess import PIPE, STDOUT
import shlex
import sys
import traceback
from shutil import copyfile
from datetime import datetime
import pyautogui
import pyshark
import json
import multiprocessing
import platform
from threading import Thread
from PIL import Image
from grayArtifacts import check_artifacts
from streaming_actions import StreamingType
import signal

if platform.system() == "Windows":
    import win32api
    import win32gui
    import win32con
    import pydirectinput
    pydirectinput.FAILSAFE = False
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.common.exceptions import TimeoutException

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import main_logger


GRAY_ARTIFACTS_LOCK = multiprocessing.Lock()


def get_mc_config():
    with open(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)), "multiconnection.json"), "r") as config:
        return json.load(config)


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True

    return sum([render_platform & set(x) == set(x) for x in case.get('skip_on', '')])


def terminate_process(process):
    child_processes = []

    try:
        child_processes = process.children()
    except psutil.NoSuchProcess:
        pass

    for ch in child_processes:
        try:
            ch.terminate()
            sleep(0.5)
            ch.kill()
            sleep(0.5)
            status = ch.status()
        except psutil.NoSuchProcess:
            pass

    try:
        process.terminate()
        sleep(0.5)
        process.kill()
        sleep(0.5)
        status = process.status()
    except psutil.NoSuchProcess:
        pass


def collect_traces(archive_path, archive_name):
    if platform.system() == "Windows":
        gpuview_path = os.getenv("GPUVIEW_PATH")
        executable_name = "log_extended.cmd"
        target_name = "Merged.etl"

        try:
            for filename in glob(os.path.join(gpuview_path, "*.etl")):
                os.remove(filename)
        except Exception:
            pass

        script = "powershell \"Start-Process cmd '/k cd \"{}\" && .\\log_extended.cmd & exit 0' -Verb RunAs\"".format(gpuview_path)

        proc = psutil.Popen(script, stdout=PIPE, stderr=PIPE, shell=True)

        target_path = os.path.join(gpuview_path, target_name)

        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() <= 30:
            if os.path.exists(target_path):
                sleep(5)
                break
        else:
            raise Exception("Could not find etl file by path {}".format(target_path))

        with zipfile.ZipFile(os.path.join(archive_path, archive_name), "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(target_path, arcname=target_name)
    else:
        raise Exception("Traces collecting aren't supported on Ubuntu")


def parse_arguments(arguments):
    return shlex.split(arguments)


def is_workable_condition(process):
    # is process with Streaming SDK alive
    try:
        process.wait(timeout=0)
        main_logger.error("StreamingSDK was down")

        return False
    except psutil.TimeoutExpired as e:
        main_logger.info("StreamingSDK is alive") 

        return True


def should_case_be_closed(execution_type, case):
    return "keep_{}".format(execution_type) not in case or not case["keep_{}".format(execution_type)]


def close_android_app(case=None, multiconnection=False):
    try:
        key = "android" if multiconnection else "client"

        if case is None or should_case_be_closed(key, case):
            execute_adb_command("adb shell am force-stop com.amd.remotegameclient")
            main_logger.info("Android client was killed")

            return True

        else:
            main_logger.info("Keep Android client instance")
            return False
    except Exception as e:
        main_logger.error("Failed to close Streaming SDK Android app. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


def save_logs(args, case, last_log_line, current_try, is_multiconnection=False):
    if getattr(args, "streaming_type", None) and args.streaming_type == StreamingType.AMD_LINK:
        # TODO: AMD Link logs not supported yet
        return None

    try:
        if not is_multiconnection:
            if hasattr(args, "execution_type"):
                execution_type = args.execution_type
            else:
                execution_type = "server"

            tool_path = args.server_tool if execution_type == "server" else args.client_tool
        else:
            execution_type = "second_client"
            tool_path = args.tool

        tool_name = get_tool_name(args)
        tool_path = os.path.abspath(os.path.join(tool_path, tool_name))

        log_source_path = tool_path + ".log"
        log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + "_{}".format(execution_type) + ".log")

        with open(log_source_path, "rb") as file:
            logs = file.read()

        if platform.system() == "Windows":
            # Firstly, convert utf-2 le bom to utf-8 with BOM. Secondly, remove BOM
            logs = logs.decode("utf-16-le").encode("utf-8").decode("utf-8-sig").encode("utf-8")

        lines = logs.split(b"\n")

        # index of first line of the current log in whole log file
        first_log_line_index = 0

        for i in range(len(lines)):
            if last_log_line is not None and last_log_line in lines[i]:
                first_log_line_index = i + 1
                break

        # update last log line
        for i in range(len(lines) - 1, -1, -1):
            if lines[i] and lines[i] != b"\r":
                last_log_line = lines[i]
                break

        if first_log_line_index != 0:
            lines = lines[first_log_line_index:]

        lines = [line for line in lines if (b"DiscoverServers() start Disabled" not in line and b"DiscoverServers() ends result=false" not in line)]

        logs = b"\n".join(lines)

        with open(log_destination_path, "ab") as file:
            file.write("\n---------- Try #{} ----------\n\n".format(current_try).encode("utf-8"))
            file.write(logs)

        main_logger.info("Finish logs saving for {}".format(execution_type))

        return last_log_line
    except Exception as e:
        main_logger.error("Failed during logs saving. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        return None


def save_latency_tool_logs(args, case, current_try):
    try:
        log_source_path = os.path.join(args.server_tool, "LatencyTestServer.exe" if args.execution_type == "server" else "LatencyTestClient.exe") + ".log"
        log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + "_latency_{}".format(args.execution_type) + ".log")

        with open(log_source_path, "rb") as file:
            logs = file.read()

        logs = logs.decode("utf-16-le").encode("utf-8").decode("utf-8-sig").encode("utf-8")

        with open(log_destination_path, "ab") as file:
            file.write("\n---------- Try #{} ----------\n\n".format(current_try).encode("utf-8"))
            file.write(logs)

        main_logger.info("Finish latency tool logs saving for {}".format(args.execution_type))
        return log_destination_path
    except Exception as e:
        main_logger.error("Failed during latency tool logs saving. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        return None


def analyze_latency_tool_logs(test_case_report, log_path):
    with open(log_path, "r") as file:
        logs = file.read()

    test_case_report["latency_tool_results"] = {}

    total_injects = None
    total_reacts = None
    average_reactions = None
    min_latency = None
    max_latency = None
    average_latency = None

    for line in logs.split("\n"):
        if "Total mouse injected" in line:
            total_injects = int(line.split("Total mouse injected:")[1].strip())
        elif "Total surface reacted" in line:
            total_reacts = int(line.split("Total surface reacted:")[1].strip())
        elif "Average reaction per second" in line:
            average_reactions = int(line.split("Average reaction per second :")[1].strip())
        elif "Min latency" in line:
            min_latency = int(line.split("Min latency:")[1].replace("ms", "").strip())
        elif "Max latency" in line:
            max_latency = int(line.split("Max latency:")[1].replace("ms", "").strip())
        elif "AVERAGE LATENCY" in line:
            average_latency = int(line.split("AVERAGE LATENCY:")[1].replace("ms", "").strip())

    if total_injects and total_reacts:
        test_case_report["latency_tool_results"]["accuracy"] = total_reacts / total_injects * 100
    else:
        test_case_report["latency_tool_results"]["accuracy"] = 0.0

    if average_reactions is not None:
        test_case_report["latency_tool_results"]["average_reactions"] = average_reactions
    else:
        test_case_report["latency_tool_results"]["average_reactions"] = -1

    if min_latency is not None:
        test_case_report["latency_tool_results"]["min_latency"] = min_latency
    else:
        test_case_report["latency_tool_results"]["min_latency"] = -1

    if max_latency is not None:
        test_case_report["latency_tool_results"]["max_latency"] = max_latency
    else:
        test_case_report["latency_tool_results"]["max_latency"] = -1

    if average_latency is not None:
        test_case_report["latency_tool_results"]["average_latency"] = average_latency
    else:
        test_case_report["latency_tool_results"]["average_latency"] = -1


def save_android_log(args, case, current_try, log_name_postfix="_client"):
    try:
        out, err = execute_adb_command("adb logcat -d", return_output=True)

        raw_logs = out.split(b"\r\n")

        log_lines = []

        for log_line in raw_logs:
            log_lines.append(log_line.decode("utf-8", "ignore").encode("utf-8", "ignore"))

        log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + log_name_postfix + ".log")

        with open(log_destination_path, "ab") as file:
            # filter Android client logs
            filtered_log_line = []

            for line in log_lines:
                prepared_line = line.decode("utf-8").lower()

                if "amf_trace" in prepared_line or "remotegameclient" in prepared_line:
                    filtered_log_line.append(line)

            file.write("\n---------- Try #{} ----------\n\n".format(current_try).encode("utf-8"))
            file.write(b"\n".join(filtered_log_line))

        execute_adb_command("adb logcat -c")

        main_logger.info("Finish logs saving for Android client")
    except Exception as e:
        main_logger.error("Failed during android logs saving. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        return None


def start_latency_tool(execution_type, tool_path):
    main_logger.info("Start Latency tool")

    # start Streaming SDK process
    process = psutil.Popen(tool_path, stdout=PIPE, stderr=PIPE, shell=True)

    return process


def close_latency_tool(execution_type):
    pyautogui.press("Q")

    sleep(5)

    subprocess.call("taskkill /f /im LatencyToolClient.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    subprocess.call("taskkill /f /im LatencyToolServer.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


def collect_iperf_info(args, log_name_base):
    if platform.system() == "Windows":
        iperf_base_path = "C:\\iperf"
        server_executable_name = "ServerTrafficListener.bat"
    else:
        iperf_base_path = os.getenv("IPERF_PATH")
        server_executable_name = "./ServerTrafficListener.sh"

    current_dir = os.getcwd()

    try:
        logs_path = os.path.join(args.output, "tool_logs")

        # change current dir to dir with iperf
        os.chdir(iperf_base_path)

        if args.execution_type == "server":
            # run iperf scripts
            proc = psutil.Popen(server_executable_name, stdout=PIPE, stderr=PIPE, shell=True)
            proc.communicate(timeout=30)
        else:
            # run iperf scripts
            proc = psutil.Popen("UDPTrafficTest.bat -d {} -s 130 -r 100 > result.log 2>&1".format(args.ip_address), stdout=PIPE, stderr=PIPE, shell=True)
            proc.communicate(timeout=30)

            # save output files
            copyfile("result.log", os.path.join(logs_path, log_name_base + "_iperf.log"))

    except Exception as e:
        main_logger.error("Failed during iperf execution. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

    os.chdir(current_dir)


def execute_adb_command(command, return_output=False):
    max_tries = 3
    current_try = 0

    while current_try < max_tries:
        current_try += 1

        try:
            command_process = subprocess.Popen(command, shell=False, stdin=PIPE, stdout=PIPE)
            out, err = command_process.communicate(timeout=30)
            main_logger.info("ADB command executed (try #{}): {}".format(command, current_try))
            if return_output:
                return out, err
            else:
                main_logger.info("ADB command out (try #{}): {}".format(out, current_try))
                main_logger.info("ADB command err (try #{}): {}".format(err, current_try))
                break
        except (psutil.TimeoutExpired, subprocess.TimeoutExpired) as err:
            main_logger.error("Failed to execute ADB command due to timeout (try #{}): {}".format(command, current_try))


def track_used_memory(case, execution_type):
    if platform.system() == "Windows":
        process_name = "RemoteGameClient.exe" if execution_type == "client" else "RemoteGameServer.exe"
    else:
        process_name = "RemoteGameClient" if execution_type == "client" else "RemoteGameServer"

    for process in psutil.process_iter():
        if process.name() == process_name:
            if platform.system() == "Windows":
                value = psutil.Process(process.pid).memory_full_info().uss / 1024 ** 2
            else:
                command = "sudo python3.9 -c 'import psutil; print(psutil.Process({}).memory_full_info().uss / 1024 ** 2)'".format(process.pid)
                proc = psutil.Popen(command, stdout=PIPE, shell=True)
                stdout, stderr = proc.communicate(timeout=30)
                value = stdout.decode("utf-8").strip()

            if "used_memory" in case and isinstance(case["used_memory"], list):
                case["used_memory"].append(value)
            else:
                case["used_memory"] = value
            break
    else:
        main_logger.error("Target process not found")


def multiconnection_start_android(test_group):
    # start Android client for multiconnection group
    if test_group in get_mc_config()["android_client"]:
        execute_adb_command("adb logcat -c")
        execute_adb_command("adb shell am start -a com.amd.wirelessvr.CONNECT -n com.amd.remotegameclient/.MainActivity")


# address is address of the opposite side
def analyze_encryption(case, execution_type, transport_protocol, is_encrypted, messages, address=None):
    if "expected_connection_problems" in case and execution_type in case["expected_connection_problems"]:
        main_logger.info("Ignore encryption analyzing due to expected problems")
        return

    encryption_is_valid = validate_encryption(execution_type, transport_protocol, "src", is_encrypted, address)

    if not encryption_is_valid:
        messages.add("Found invalid encryption. Packet: server -> client (found on {} side)".format(execution_type))

    encryption_is_valid = validate_encryption(execution_type, transport_protocol, "dst", is_encrypted, address)

    if not encryption_is_valid:
        messages.add("Found invalid encryption. Packet: client -> server (found on {} side)".format(execution_type))


def decode_payload(payload):
    result = ""
    for byte in payload.split(":"):
        result += chr(int(byte, 16))
    return result.encode("cp1251", "ignore").decode("utf8", "ignore")


# address is address of the opposite side
def validate_encryption(execution_type, transport_protocol, direction, is_encrypted, address):
    # number of packets which should be analyzed (some packets doesn't contain payload, they'll be skipped)
    packets_to_analyze = 5

    main_logger.info("Check {} packets".format(packets_to_analyze))

    if execution_type == "client":
        capture_filter = "{direction} host {address} and {transport_protocol} {direction} port 1235".format(direction=direction, address=address, transport_protocol=transport_protocol)
    else:
        if direction == "src":
            capture_filter = "src host {address} and {transport_protocol} dst port 1235".format(address=address, transport_protocol=transport_protocol)
        else:
            capture_filter = "dst host {address} and {transport_protocol} src port 1235".format(address=address, transport_protocol=transport_protocol)

    main_logger.info("Capture filter: {}".format(capture_filter))

    packets = pyshark.LiveCapture("eth", bpf_filter=capture_filter)
    packets.sniff(timeout=3)

    main_logger.info(packets)

    non_encrypted_packet_found = False

    if len(packets) < packets_to_analyze:
        main_logger.warning("Not enough packets for analyze")
        return True

    if packets_to_analyze > len(packets):
        packets_to_analyze = len(packets)

    analyzed_packets = 0

    for packet in packets:
        try:
            if transport_protocol == "udp":
                payload = packet.udp.payload
            else:
                payload = packet.tcp.payload

            analyzed_packets += 1
        except AttributeError:
            main_logger.warning("Could not get payload")
            continue
        except Exception as e:
            main_logger.error("Failed to get packet payload. Exception: {}".format(str(e)))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))
            continue

        decoded_payload = decode_payload(payload)
        main_logger.info("Decoded payload: {}".format(decoded_payload))

        if "\"id\":" in decoded_payload or "\"DeviceID\":" in decoded_payload:
            non_encrypted_packet_found = True
            break

        if analyzed_packets >= packets_to_analyze:
            break

    packets.close()

    if is_encrypted == (not non_encrypted_packet_found):
        main_logger.info("Encryption is valid")
        return True
    else:
        main_logger.warning("Encryption isn't valid")
        return False


def contains_encryption_errors(error_messages):
    for message in error_messages:
        if message.startswith("Found invalid encryption"):
            return True
            break
    else:
        return False


def start_clumsy(keys, client_ip=None, server_ip=None, android_ip=None, second_client_ip=None):
    if platform.system() == "Windows":
        script = "powershell \"Start-Process cmd '/k clumsy.exe {} & exit 0' -Verb RunAs\"".format(keys.replace("\"", "\\\""))

        ips = {"client_ip": client_ip, "server_ip": server_ip, "android_ip": android_ip, "second_client_ip": second_client_ip}

        for ip_key, ip_value in ips.items():
            if ip_value is not None:
                script = script.replace("<{}>".format(ip_key), ip_value)

        psutil.Popen(script, stdout=PIPE, stderr=PIPE, shell=True)

        sleep(1.5)
    else:
        raise Exception("Clumsy isn't supported on Ubuntu")


def close_clumsy():
    script = "powershell \"Start-Process cmd '/k taskkill /im clumsy.exe & exit 0' -Verb RunAs\""
    psutil.Popen(script, stdout=PIPE, stderr=PIPE, shell=True)


def check_artifacts_and_save_status(artifact_path, json_path, logger, limit=100000, obj_type="image", step=5):
    def do_check():
        status = check_artifacts(artifact_path, limit, obj_type, step)
        logger.info("{} gray artifact check status: {}".format(artifact_path, status))

        if status:
            with GRAY_ARTIFACTS_LOCK:
                with open(json_path, "r") as file:
                    test_case_report = json.loads(file.read())[0]
                    test_case_report["gray_artifacts_detected"] = True

                with open(json_path, "w") as file:
                    json.dump([test_case_report], file, indent=4)

    checking_thread = Thread(target=do_check, args=())
    checking_thread.start()


def make_window_active(window):
    win32gui.ShowWindow(window, 9)


def make_window_maximized(window):
    win32gui.ShowWindow(window, 3)


def hide_window(window):
    win32gui.ShowWindow(window, 6)


# Function return protocol type(tcp\udp) from server keys in case (in case of Streaming SDK) or from transport_protocol key (in case of Full Samples)
def getTransportProtocol(args, case):
    if getattr(args, "streaming_type", None) == None or args.streaming_type == StreamingType.SDK or args.streaming_type == StreamingType.FULL_SAMPLES:
        current_protocol = "tcp"
        if "-protocol udp" in case["server_keys"].lower():
            current_protocol = "udp"
        return current_protocol


def get_tool_name(args):
    if getattr(args, "streaming_type", None) == None or args.streaming_type == StreamingType.SDK:
        if args.execution_type == "server":
            if platform.system() == "Windows":
                return "RemoteGameServer.exe"
            else:
                return "RemoteGameServer"
        else:
            return "RemoteGameClient.exe"
    elif args.streaming_type == StreamingType.FULL_SAMPLES:
        if args.execution_type == "server":
            return "FullGameServer.exe"
        else:
            return "FullGameClient.exe"


def find_by_xpath(xpath, driver, wait=5):
    try:
        element = WebDriverWait(driver, wait).until(
            lambda d: d.find_element(By.XPATH, xpath)
        )
        return element
    except TimeoutException:
<<<<<<< HEAD
        return ValueError(f"Could not find element with XPATH: {xpath}")
=======
        raise ValueError(f"Could not find element with XPATH: {xpath}")
>>>>>>> dedicated_repo/master
