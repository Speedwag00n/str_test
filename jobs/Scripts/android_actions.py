import sys
import os
from time import sleep, strftime, gmtime
import psutil
import subprocess
from subprocess import PIPE
import traceback
import pyautogui
from threading import Thread
from utils import parse_arguments, execute_adb_command, get_mc_config, close_clumsy, make_window_active
from actions import *
import base64
import keyboard
import platform
import games_actions

if platform.system() == "Windows":
    import win32gui
    import win32api
    from pyffmpeg import FFmpeg
    import pydirectinput
    pydirectinput.FAILSAFE = False

pyautogui.FAILSAFE = False
MC_CONFIG = get_mc_config()


# open some game if it doesn't launched (e.g. open game/benchmark)
class OpenGame(Action):
    def parse(self):
        self.game_name = self.params["game_name"]
        self.game_launcher = games_actions.get_game_launcher_path(self.game_name)
        self.game_window = games_actions.get_game_window_name(self.game_name)
        self.game_process_name = games_actions.get_game_process_name(self.game_name)

    def execute(self):
        if self.game_launcher is None or self.game_window is None or self.game_process_name is None:
            return

        game_launched = True

        window = win32gui.FindWindow(None, self.game_window)

        if window is not None and window != 0:
            self.logger.info("Window {} was succesfully found".format(self.game_window))

            make_window_active(window)
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

            games_actions.prepare_game(self.game_name, self.game_launcher)


# Do click 
class Click(Action):
    def execute(self):
        pyautogui.click()
        sleep(0.2)


# Execute sleep 
class DoSleep(Action):
    def parse(self):
        self.seconds = self.params["arguments_line"]

    def execute(self):
        sleep(int(self.seconds))


# Press some sequence of keys on server
class PressKeys(Action):
    def parse(self):
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.keys_string = parsed_arguments[0]

    def execute(self):
        games_actions.press_keys(self.keys_string)


# Do screenshot
class MakeScreen(MulticonnectionAction):
    def parse(self):
        self.screen_path = self.params["screen_path"]
        self.screen_name = self.params["arguments_line"]
        self.current_image_num = self.params["current_image_num"]
        self.current_try = self.params["current_try"]
        self.client_type = self.params["client_type"]
        self.test_group = self.params["args"].test_group
        self.case_json_path = self.params["case_json_path"]

    def execute(self):
        if not self.screen_name:
            make_screen(self.screen_path, None, self.current_try, self.logger)
        else:
            make_screen(self.screen_path, self.case_json_path, self.current_try, self.logger, self.screen_name + self.client_type, self.current_image_num)
            self.params["current_image_num"] += 1

            if self.test_group in MC_CONFIG["android_client"]:
                if self.test_group in MC_CONFIG["second_win_client"]:
                    self.logger.info("Wait second client answer")
                    response = self.second_sock.recv(1024).decode("utf-8")
                    self.logger.info("Second client answer: {}".format(response))
                    self.sock.send(response.encode("utf-8"))
                else:
                    self.sock.send("done".encode("utf-8"))


def make_screen(screen_path, case_json_path, current_try, logger, screen_name = "", current_image_num = 0):
    try:
        screen_path = os.path.join(screen_path, "{:03}_{}_try_{:02}.png".format(current_image_num, screen_name, current_try + 1))
        out, err = execute_adb_command("adb exec-out screencap -p", return_output=True)

        with open(screen_path, "wb") as file:
            file.write(out)

        logger.error("Screencap command err: {}".format(err))
    except Exception as e:
        logger.error("Failed to make screenshot: {}".format(str(e)))
        logger.error("Traceback: {}".format(traceback.format_exc()))


# Make sequence of screens with delay. It supports initial delay before the first test case
class SleepAndScreen(MulticonnectionAction):
    def parse(self):
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.initial_delay = parsed_arguments[0]
        self.number_of_screens = parsed_arguments[1]
        self.delay = parsed_arguments[2]
        self.screen_path = self.params["screen_path"]
        self.screen_name = parsed_arguments[3]
        self.current_image_num = self.params["current_image_num"]
        self.current_try = self.params["current_try"]
        self.client_type = self.params["client_type"]
        self.test_group = self.params["args"].test_group
        self.case_json_path = self.params["case_json_path"]

    def execute(self):
        sleep(float(self.initial_delay))

        screen_number = 1

        while True:
            make_screen(self.screen_path, self.case_json_path, self.current_try, self.logger, self.screen_name + self.client_type, self.current_image_num)
            self.params["current_image_num"] += 1
            self.current_image_num = self.params["current_image_num"]
            screen_number += 1

            if screen_number > int(self.number_of_screens):
                break
            else:
                sleep(float(self.delay))

        if self.test_group in MC_CONFIG["android_client"]:
            if self.test_group in MC_CONFIG["second_win_client"]:
                self.logger.info("Wait second client answer")
                response = self.second_sock.recv(1024).decode("utf-8")
                self.logger.info("Second client answer: {}".format(response))
                self.sock.send(response.encode("utf-8"))
            else:
                self.sock.send("done".encode("utf-8"))


def download_and_compress_video(temp_video_path, target_video_path, logger):
    execute_adb_command("adb pull /sdcard/video.mp4 {}".format(temp_video_path))

    recorder = FFmpeg()
    logger.info("Start video compressing")

    recorder.options("-i {} -pix_fmt yuv420p {}".format(temp_video_path, target_video_path))

    os.remove(temp_video_path)

    logger.info("Finish to compress video")


# Record video
class RecordVideo(MulticonnectionAction):
    def parse(self):
        self.video_path = self.params["output_path"]
        self.target_video_name = self.params["case"]["case"] + self.params["client_type"] + ".mp4"
        self.temp_video_name = self.params["case"]["case"] + self.params["client_type"] + "_temp.mp4"
        self.duration = int(self.params["arguments_line"])
        self.test_group = self.params["args"].test_group
        self.case_json_path = self.params["case_json_path"]
        self.recovery_clumsy = "recovery_android_clumsy" in self.params["case"] and self.params["case"]["recovery_android_clumsy"]
        self.game_name = self.params["args"].game_name

    def execute(self):
        try:
            if self.recovery_clumsy:
                self.logger.info("Recovery Streaming SDK work - close clumsy")
                close_clumsy()
                sleep(2)
                window = win32gui.FindWindow(None, games_actions.get_game_window_name(self.game_name))
                make_window_active(window)

            self.logger.info("Start to record video")
            execute_adb_command("adb shell screenrecord --time-limit={} /sdcard/video.mp4".format(self.duration))
            self.logger.info("Finish to record video")

            temp_video_path = os.path.join(self.video_path, self.temp_video_name)
            target_video_path = os.path.join(self.video_path, self.target_video_name)

            compressing_thread = Thread(target=download_and_compress_video, args=(temp_video_path, target_video_path, self.logger))
            compressing_thread.start()

        except Exception as e:
            self.logger.error("Failed to make screenshot: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))

        if self.test_group in MC_CONFIG["android_client"]:
            if self.test_group in MC_CONFIG["second_win_client"]:
                self.logger.info("Wait second client answer")
                response = self.second_sock.recv(1024).decode("utf-8")
                self.logger.info("Second client answer: {}".format(response))
                self.sock.send(response.encode("utf-8"))
            else:
                self.sock.send("done".encode("utf-8"))


class RecordMicrophone(Action):
    def parse(self):
        self.duration = int(self.params["arguments_line"])
        self.action = self.params["action_line"]
        self.test_group = self.params["args"].test_group
        self.audio_path = self.params["output_path"]
        self.audio_name = self.params["case"]["case"] + "audio"

    def execute(self):
        try:
            audio_full_path = os.path.join(self.audio_path, self.audio_name + ".mp4")
            time_flag_value = strftime("%H:%M:%S", gmtime(int(self.duration)))

            recorder = FFmpeg()
            sleep(30)
            self.logger.info("Start to record audio")

            recorder.options("-f dshow -i audio=\"Microphone (AMD Streaming Audio Device)\" -t {time} {audio}"
                .format(time=time_flag_value, audio=audio_full_path))
        except Exception as e:
            self.logger.error("Error during microphone recording")
            self.logger.error("Traceback: {}".format(traceback.format_exc()))


class StartActions(Action):
    def parse(self):
        self.game_name = self.params["game_name"]

    def execute(self):
        gpu_view_thread = Thread(target=do_test_actions, args=(self.game_name.lower(), self.logger,))
        gpu_view_thread.daemon = True
        gpu_view_thread.start()

def do_test_actions(game_name, logger):
    try:
        if game_name == "valorant":
            for i in range(10):
                pyautogui.keyDown("space")
                sleep(0.1)
                pydirectinput.keyUp("space")

                pydirectinput.press("x")
                sleep(1)
                pydirectinput.click()
                sleep(3)

        elif game_name == "dota2dx11" or game_name == "dota2vulkan":
            for i in range(6):
                pydirectinput.press("r")
                sleep(3)
                pydirectinput.press("w")
                sleep(3)

        elif game_name == "csgo":
            for i in range(20):
                pydirectinput.press("4")
                sleep(1.5)
                pyautogui.click()
            
        elif game_name == "lol":
            edge_x = win32api.GetSystemMetrics(0)
            edge_y = win32api.GetSystemMetrics(1)
            center_x = edge_x / 2
            center_y = edge_y / 2

            for i in range(5):
                pydirectinput.press("e")
                sleep(0.3)
                pydirectinput.press("w")
                sleep(0.3)
                pydirectinput.press("r")
                sleep(0.3)

                pyautogui.moveTo(center_x + 230, center_y + 60)
                sleep(0.1)
                pyautogui.click(button="right")
                sleep(1.5)

                pyautogui.moveTo(center_x - 230, center_y - 60)
                sleep(0.1)
                pyautogui.click(button="right")
                sleep(1.5)

        elif game_name == "pubg":
            pyautogui.press("z")
            sleep(0.2)
            pyautogui.press("m")
            sleep(0.2)
            pyautogui.press("m")
            sleep(0.2)
            pyautogui.press("z")
            sleep(0.2)
            pyautogui.press("v")
            sleep(0.2)
            pyautogui.press("tab")
            sleep(0.2)
            pyautogui.press("tab")
            sleep(0.2)
            pyautogui.press("v")

    except Exception as e:
        logger.error("Failed to do test actions: {}".format(str(e)))
        logger.error("Traceback: {}".format(traceback.format_exc()))
