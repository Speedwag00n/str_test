import socket
import sys
import os
from time import sleep, strftime, gmtime
import psutil
from subprocess import PIPE
import traceback
import pyautogui
from threading import Thread
import platform
from utils import *
from actions import *
from streaming_actions import StreamingType, start_streaming
import games_actions

if platform.system() == "Windows":
    import win32gui
    import win32api
    from pyffmpeg import FFmpeg
    import pydirectinput
    pydirectinput.FAILSAFE = False

pyautogui.FAILSAFE = False
MC_CONFIG = get_mc_config()


# execute some cmd command on server (e.g. open game/benchmark)
class ExecuteCMD(Action):
    def parse(self):
        self.processes = self.params["processes"]
        self.cmd_command = self.params["arguments_line"]

    @Action.server_action_decorator
    def execute(self):
        process = psutil.Popen(self.cmd_command, stdout=PIPE, stderr=PIPE, shell=True)
        self.processes[self.cmd_command] = process
        self.logger.info("Executed: {}".format(self.cmd_command))

        return True


# open some game if it doesn't launched (e.g. open game/benchmark)
class OpenGame(Action):
    def parse(self):
        self.game_name = self.params["game_name"]
        self.args = self.params["args"]
        self.game_launcher = games_actions.get_game_launcher_path(self.game_name)
        self.game_window = games_actions.get_game_window_name(self.game_name)
        self.game_process_name = games_actions.get_game_process_name(self.game_name)

    @Action.server_action_decorator
    def execute(self):
        if self.game_launcher is None or self.game_window is None or self.game_process_name is None:
            return

        game_launched = True

        if platform.system() == "Windows":
            window = win32gui.FindWindow(None, self.game_window)

            if window is not None and window != 0:
                self.logger.info("Window {} was succesfully found".format(self.game_window))

                if self.args.streaming_type != StreamingType.AMD_LINK:
                    make_window_active(window)
            else:
                self.logger.error("Window {} wasn't found at all".format(self.game_window))
                game_launched = False
        else:
            process = subprocess.Popen("wmctrl -l", stdout=PIPE, shell=True)
            stdout, stderr = process.communicate()
            windows = [" ".join(x.split()[3::]) for x in stdout.decode("utf-8").strip().split("\n")]

            for window in windows:
                if window == self.game_window:
                    self.logger.info("Window {} was succesfully found".format(self.game_window))
                    break
            else:
                self.logger.error("Window {} wasn't found at all".format(self.game_window))
                game_launched = False

        for process in psutil.process_iter():
            if self.game_process_name in process.name():
                self.logger.info("Process {} was succesfully found".format(self.game_process_name))
                break
        else:
            self.logger.info("Process {} wasn't found at all".format(self.game_process_name))
            game_launched = False

        if not game_launched:
            if self.game_name == "lol":
                sleep(240)

            if platform.system() == "Windows":
                pyautogui.hotkey("win", "m")
                sleep(0.5)

            psutil.Popen(self.game_launcher, stdout=PIPE, stderr=PIPE, shell=True)
            self.logger.info("Executed: {}".format(self.game_launcher))

            # Run DX9 benchmarks in window mode in case of AMD Link autotests or in case of traces collection
            if self.game_name == "heavendx9" or self.game_name == "valleydx9":
                if self.args.streaming_type == StreamingType.AMD_LINK or self.args.collect_traces != "False":
                    fullscreen = False
                else:
                    fullscreen = True
            else:
                fullscreen = True

            self.logger.info(f"Run in fullscreen: {fullscreen}")
            games_actions.prepare_game(self.game_name, self.game_launcher, fullscreen=fullscreen)

        return True


# check what some window exists (it allows to check that some game/benchmark is opened)
class CheckWindow(Action):
    def parse(self):
        self.processes = self.params["processes"]
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.window_name = parsed_arguments[0]
        self.process_name = parsed_arguments[1]
        self.is_game = (self.params["command"] == "check_game")
        self.test_group = self.params["args"].test_group
        self.game_name = self.params["args"].game_name

    @Action.server_action_decorator
    def execute(self):
        result = False

        if self.window_name:
            if platform.system() == "Windows":
                window = win32gui.FindWindow(None, self.window_name)

                if window is not None and window != 0:
                    self.logger.info("Window {} was succesfully found".format(self.window_name))
                else:
                    self.logger.error("Window {} wasn't found at all".format(self.window_name))
                    return False
            else:
                process = subprocess.Popen("wmctrl -l", stdout=PIPE, shell=True)
                stdout, stderr = process.communicate()
                windows = [" ".join(x.split()[3::]) for x in stdout.decode("utf-8").strip().split("\n")]

                for window in windows:
                    if window == self.window_name:
                        self.logger.info("Window {} was succesfully found".format(self.window_name))
                        break
                else:
                    self.logger.error("Window {} wasn't found at all".format(self.window_name))
                    return False

        for process in psutil.process_iter():
            if self.process_name in process.name():
                self.logger.info("Process {} was succesfully found".format(self.process_name))
                self.processes[self.process_name] = process
                result = True
                break
        else:
            self.logger.info("Process {} wasn't found at all".format(self.process_name))
            result = False

        return result



def close_processes(processes, logger):
    result = True

    for process_name in processes:
        try:
            terminate_process(processes[process_name])
        except Exception as e:
            logger.error("Failed to close process: {}".format(str(e)))
            logger.error("Traceback: {}".format(traceback.format_exc()))
            result = False

    return result


# press some sequence of keys on server
class PressKeysServer(Action):
    def parse(self):
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.keys_string = parsed_arguments[0]

    @Action.server_action_decorator
    def execute(self):
        games_actions.press_keys(self.keys_string)

        return True


# abort the current case execution (all opened processes of game/benchmark will be closed)
class Abort(Action):
    def parse(self):
        self.processes = self.params["processes"]

    @Action.server_action_decorator
    def execute(self):
        result = close_processes(self.processes, self.logger)

        if result:
            self.logger.info("Processes was succesfully closed")
        else:
            self.logger.error("Failed to close processes")

        return result

    
    def analyze_result(self):
        self.state.is_aborted = True
        raise ClientActionException("Client sent abort command")


# retry the current case execution (all opened processes of game/benchmark won't be closed)
class Retry(Action):
    @Action.server_action_decorator
    def execute(self):
        return True

    def analyze_result(self):
        self.state.is_aborted = True
        raise ClientActionException("Client sent abort command")


# start the next test case (it stops waiting of the next command)
class NextCase(Action):
    @Action.server_action_decorator
    def execute(self):
        if self.params["args"].track_used_memory:
            track_used_memory(self.params["case"], "server")

        return True

    def analyze_result(self):
        self.state.wait_next_command = False


class IPerf(Action):
    #TODO: add support for Ubuntu
    def parse(self):
        self.json_content = self.params["json_content"]

    def execute(self):
        execute_iperf = None

        for message in self.json_content["message"]:
            if "Network problem:" in message:
                execute_iperf = True
                break

        iperf_answer = "start" if execute_iperf else "skip"

        self.logger.info("IPerf answer: {}".format(iperf_answer))
        self.sock.send(iperf_answer.encode("utf-8"))

        if execute_iperf:
            collect_iperf_info(self.params["args"], self.params["case"]["case"])
            self.params["iperf_executed"] = True


# do click on server side
class ClickServer(Action):
    def parse(self):
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.x_description = parsed_arguments[0]
        self.y_description = parsed_arguments[1]
        if len(parsed_arguments) > 2:
            self.delay = float(parsed_arguments[2])
        else:
            self.delay = 0.2

    @Action.server_action_decorator
    def execute(self):
        games_actions.click(self.x_description, self.y_description, self.delay)
        return True


class RecordMicrophone(Action):
    def parse(self):
        self.duration = int(self.params["arguments_line"])
        self.action = self.params["action_line"]
        self.test_group = self.params["args"].test_group
        self.audio_path = self.params["output_path"]
        self.audio_name = self.params["case"]["case"] + "audio"

    @Action.server_action_decorator
    def execute(self):
        try:
            audio_full_path = os.path.join(self.audio_path, self.audio_name + ".mp4")
            time_flag_value = strftime("%H:%M:%S", gmtime(int(self.duration)))

            recorder = FFmpeg()
            self.logger.info("Start to record audio")

            recorder.options("-f dshow -i audio=\"Microphone (AMD Streaming Audio Device)\" -t {time} {audio}"
                .format(time=time_flag_value, audio=audio_full_path))
        except Exception as e:
            self.logger.error("Error during microphone recording")
            self.logger.error("Traceback: {}".format(traceback.format_exc()))

        return True


# start doing test actions on server side
class DoTestActions(Action):
    def parse(self):
        self.game_name = self.params["game_name"]
        self.stage = 0

    def execute(self):
        try:
            if self.game_name == "valorant":
                if self.stage == 0:
                    sleep(1)
                    pydirectinput.keyDown("space")
                    sleep(0.1)
                    pyautogui.keyUp("space")
                elif self.stage == 1:
                    pyautogui.press("x")
                    sleep(1)
                    pyautogui.click()
                    sleep(1)
                elif self.stage == 2:
                    sleep(2)

                self.stage += 1

                if self.stage > 2:
                    self.stage = 0        
            elif self.game_name == "lol":
                if platform.system() == "Windows":
                    edge_x = win32api.GetSystemMetrics(0)
                    edge_y = win32api.GetSystemMetrics(1)
                else:
                    process = subprocess.Popen("xdpyinfo | awk '/dimensions/{print $2}'", stdout=PIPE, shell=True)
                    stdout, stderr = process.communicate()
                    edge_x, edge_y = stdout.decode("utf-8").strip().split("x")
                    edge_x = int(edge_x)
                    edge_y = int(edge_y)

                center_x = edge_x / 2
                center_y = edge_y / 2

                # avoid to long cycle of test actions (split it to parts)

                if self.stage == 0:
                    pydirectinput.press("e")
                    sleep(0.3)
                    pydirectinput.press("w")
                    sleep(0.3)
                    pydirectinput.press("r")
                    sleep(0.3)
                elif self.stage == 1:
                    pyautogui.moveTo(center_x + 230, center_y + 60)
                    sleep(0.1)
                    pyautogui.click(button="right")
                    sleep(1.5)
                elif self.stage == 2:
                    pyautogui.moveTo(center_x - 230, center_y - 60)
                    sleep(0.1)
                    pyautogui.click(button="right")
                    sleep(1.5)

                self.stage += 1

                if self.stage > 2:
                    self.stage = 0
            elif self.game_name == "dota2dx11" or self.game_name == "dota2vulkan":
                # do centering of the in-game camera on the hero
                pydirectinput.press("f1")
                pydirectinput.press("f1")

                pydirectinput.press("r")
                sleep(1)
                pydirectinput.press("w")
            elif self.game_name == "csgo":
                pydirectinput.press("4")
                sleep(1)
                pyautogui.click()
            elif self.game_name == "pubg":
                pydirectinput.press("z")
                sleep(0.2)
                pydirectinput.press("m")
                sleep(0.2)
                pydirectinput.press("m")
                sleep(0.2)
                pydirectinput.press("z")
                sleep(0.2)
                pydirectinput.press("v")
                sleep(0.2)
                pydirectinput.press("tab")
                sleep(0.2)
                pydirectinput.press("tab")
                sleep(0.2)
                pydirectinput.press("v")
            else:
                sleep(0.5)

        except Exception as e:
            self.logger.error("Failed to do test actions: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))

    def analyze_result(self):
        self.state.executing_test_actions = True


# check encryption traces on server side
class Encryption(MulticonnectionAction):
    def parse(self):
        self.test_group = self.params["args"].test_group

    def execute(self):
        self.second_sock.send("encryption".encode("utf-8"))
        response = self.second_sock.recv(1024).decode("utf-8")
        self.logger.info("Second client response for 'encryption' action: {}".format(response))

        self.sock.send("start".encode("utf-8"))

        compressing_thread = Thread(target=analyze_encryption, args=(self.params["case"], "server", getTransportProtocol(self.params["args"], self.params["case"]), \
            "-encrypt" in self.params["case"]["server_keys"].lower(), self.params["messages"], self.params["client_address"]))
        compressing_thread.start()


# collect gpuview traces on server side
class GPUView(Action):
    def parse(self):
        self.collect_traces = self.params["args"].collect_traces
        self.archive_path = self.params["archive_path"]
        self.archive_name = self.params["case"]["case"]

    def execute(self):
        if self.collect_traces == "AfterTests":
            self.sock.send("start".encode("utf-8"))

            try:
                collect_traces(self.archive_path, self.archive_name + "_server.zip")
            except Exception as e:
                self.logger.warning("Failed to collect GPUView traces: {}".format(str(e)))
                self.logger.warning("Traceback: {}".format(traceback.format_exc()))
        else:
            self.sock.send("skip".encode("utf-8"))


# record metrics on server side
class RecordMetrics(Action):
    def parse(self):
        self.test_group = self.params["args"].test_group

    @Action.server_action_decorator
    def execute(self):
        try:
            if self.test_group in MC_CONFIG["second_win_client"]:
                self.sock.send("record_metrics".encode("utf-8"))
        except Exception as e:
            self.logger.error("Failed to send action to second windows client: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))

        if "used_memory" not in self.params["case"]:
            self.params["case"]["used_memory"] = []

        if self.params["args"].track_used_memory:
            track_used_memory(self.params["case"], "server")

        return True


class MakeScreen(MulticonnectionAction):
    def parse(self):
        self.action = self.params["action_line"]
        self.test_group = self.params["args"].test_group

    def execute(self):
        try:
            self.second_sock.send(self.action.encode("utf-8"))

            if self.test_group in MC_CONFIG["second_win_client"] and self.test_group not in MC_CONFIG["android_client"]:
                self.logger.info("Wait second client answer")
                response = self.second_sock.recv(1024).decode("utf-8")
                self.logger.info("Second client answer: {}".format(response))
                self.sock.send(response.encode("utf-8"))
        except Exception as e:
            self.logger.error("Failed to communicate with second windows client: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))


class SleepAndScreen(MulticonnectionAction):
    def parse(self):
        self.action = self.params["action_line"]
        self.test_group = self.params["args"].test_group

    def execute(self):
        try:
            self.second_sock.send(self.action.encode("utf-8"))

            if self.test_group in MC_CONFIG["second_win_client"] and self.test_group not in MC_CONFIG["android_client"]:
                self.logger.info("Wait second client answer")
                response = self.second_sock.recv(1024).decode("utf-8")
                self.logger.info("Second client answer: {}".format(response))
                self.sock.send(response.encode("utf-8"))
        except Exception as e:
            self.logger.error("Failed to send action to second windows client: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))


class RecordVideo(MulticonnectionAction):
    def parse(self):
        self.action = self.params["action_line"]
        self.test_group = self.params["args"].test_group

    def execute(self):
        try:
            self.second_sock.send(self.action.encode("utf-8"))

            if self.test_group in MC_CONFIG["second_win_client"] and self.test_group not in MC_CONFIG["android_client"]:
                self.logger.info("Wait second client answer")
                response = self.second_sock.recv(1024).decode("utf-8")
                self.logger.info("Second client answer: {}".format(response))
                self.sock.send(response.encode("utf-8"))
        except Exception as e:
            self.logger.error("Failed to send action to second windows client: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))


# Start Streaming SDK clients and server
class StartStreaming(MulticonnectionAction):
    def parse(self):
        self.action = self.params["action_line"]
        self.case = self.params["case"]
        self.args = self.params["args"]
        self.archive_path = self.params["archive_path"]
        self.archive_name = self.params["case"]["case"]
        self.script_path = self.params["script_path"]
        self.android_client_closed = self.params["android_client_closed"]
        self.process = self.params["process"]
        self.game_name = self.params["game_name"]

    def execute(self):
        mc_config = get_mc_config()

        # TODO: make single parameter to configure launching order
        # start android client before server
        if "android_start" in self.case and self.case["android_start"] == "before_server":
            if self.android_client_closed:
                multiconnection_start_android(self.args.test_group)
                sleep(5)

        if self.args.streaming_type == StreamingType.AMD_LINK:
            debug_screen_path = os.path.join(self.params["screen_path"], f"{self.case['case']}_debug.jpg")

            self.process = start_streaming(self.args, self.case, socket=self.sock, debug_screen_path=debug_screen_path)

            window = win32gui.FindWindow(None, games_actions.get_game_window_name(self.game_name))
            make_window_active(window)

        # start server
        if self.process is None:
            should_collect_traces = (self.args.collect_traces == "BeforeTests")

            if self.args.streaming_type != StreamingType.AMD_LINK:
                self.process = start_streaming(self.args, self.case, script_path=self.script_path, socket=self.sock)

            if self.args.test_group in mc_config["second_win_client"] or self.args.test_group in mc_config["android_client"]:
                sleep(5)

            if should_collect_traces:
                collect_traces(self.archive_path, self.archive_name + "_server.zip")
            elif "start_first" in self.case and self.case["start_first"] == "server":
                sleep(5)
        elif self.args.streaming_type == StreamingType.FULL_SAMPLES:
            start_streaming(self.args, self.case, script_path=None, socket=self.sock)

        # TODO: make single parameter to configure launching order
        # start android client after server or default behaviour
        if "android_start" not in self.case or self.case["android_start"] == "after_server":
            if self.android_client_closed and self.args.test_group in mc_config["android_client"]:
                multiconnection_start_android(self.args.test_group)
                # small delay to give client time to connect
                sleep(5)

        # start second client after server
        if self.args.test_group in mc_config["second_win_client"]:
            self.second_sock.send(self.case["case"].encode("utf-8"))
            # small delay to give client time to connect
            sleep(5)

        self.sock.send("done".encode("utf-8"))


# Close clumsy
class RecoveryClumsy(Action):
    def parse(self):
        self.recovery_clumsy = "recovery_server_clumsy" in self.params["case"] and self.params["case"]["recovery_server_clumsy"]
        self.game_name = self.params["args"].game_name

    def execute(self):
        if self.recovery_clumsy:
            self.logger.info("Recovery Streaming SDK work - close clumsy")
            close_clumsy()
            sleep(2)
            window = win32gui.FindWindow(None, games_actions.get_game_window_name(self.game_name))
            make_window_active(window)


# Start Latency tool
class StartLatencyTool(MulticonnectionAction):
    def parse(self):
        self.action = self.params["action_line"]
        self.args = self.params["args"]
        self.tool_path = os.path.join(self.args.server_tool, "LatencyTestServer.exe")

    def execute(self):
        self.process = start_latency_tool(self.args.execution_type, self.tool_path)

        self.sock.send("done".encode("utf-8"))

