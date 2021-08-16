from time import sleep
import psutil
import os
from glob import glob
import zipfile
from subprocess import PIPE
import shlex
import win32api

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import main_logger


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True

    return sum([render_platform & set(x) == set(x) for x in case.get('skip_on', '')])


def close_process(process):
    child_processes = []

    try:
        child_processes = process.children()
    except psutil.NoSuchProcess:
        pass

    for ch in child_processes:
        try:
            ch.terminate()
            sleep(5)
            ch.kill()
            sleep(5)
            status = ch.status()
        except psutil.NoSuchProcess:
            pass

    try:
        process.terminate()
        sleep(5)
        process.kill()
        sleep(5)
        status = process.status()
    except psutil.NoSuchProcess:
        pass


def collect_traces(archive_path, archive_name):
    traces_base_path = "C:\\JN\\GPUViewTraces"
    # traces can generate in gpuview dir
    gpuview_path = os.getenv("GPUVIEW_PATH")
    executable_name = "log_extended.cmd - Shortcut.lnk"
    target_name = "Merged.etl"

    try:
        for filename in glob(os.path.join(traces_base_path, "*.etl")):
            os.remove(filename)
    except Exception:
        pass

    try:
        for filename in glob(os.path.join(gpuview_path, "*.etl")):
            os.remove(filename)
    except Exception:
        pass

    proc = psutil.Popen(os.path.join(traces_base_path, executable_name), stdout=PIPE, stderr=PIPE, shell=True)

    proc.communicate()

    sleep(2)

    target_path = os.path.join(traces_base_path, target_name)

    if not os.path.exists(target_path):
        target_path = os.path.join(gpuview_path, target_name)

        if not os.path.exists(target_path):
            raise Exception("Could not find etl file by path {}".format(target_path))

    with zipfile.ZipFile(os.path.join(archive_path, archive_name), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(target_path, arcname=target_name)


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


def should_case_be_closed(args, case):
    return "keep_{}".format(args.execution_type) not in case or not case["keep_{}".format(args.execution_type)]


def close_process(args, case, process):
    if should_case_be_closed(args, case):
        # close the current Streaming SDK process
        if process is not None:
            close_process(process)

        # additional try to kill Streaming SDK server/client (to be sure that all processes are closed)

        status = 0

        while status != 128:
            status = subprocess.call("taskkill /f /im RemoteGameClient.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        status = 0

        while status != 128:
            status = subprocess.call("taskkill /f /im RemoteGameServer.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        process = None

    return process


def save_logs(args, case):
    try:
        tool_path = args.server_tool if args.execution_type == "server" else args.client_tool
        tool_path = os.path.abspath(tool_path)

        log_source_path = tool_path + ".log"
        log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + "_{}".format(args.execution_type) + ".log")

        with open(log_source_path, "rb") as file:
            logs = file.read()

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

        logs = b"\n".join(lines)

        with open(log_destination_path, "ab") as file:
            file.write("\n---------- Try #{} ----------\n\n".format(current_try).encode("utf-8"))
            file.write(logs)
    except Exception as e:
        main_logger.error("Failed during logs saving. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


def start_streaming(args, script_path):
    main_logger.info("Start StreamingSDK {}".format(args.execution_type))

    # start Streaming SDK process
    process = psutil.Popen(script_path, stdout=PIPE, stderr=PIPE, shell=True)

    main_logger.info("Start execution_type depended script")

    # Wait a bit to launch streaming SDK client/server
    time.sleep(3)

    main_logger.info("Screen resolution: width = {}, height = {}".format(win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)))

    return process
