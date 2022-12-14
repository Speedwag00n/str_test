import os
from time import sleep, strftime, gmtime
import traceback
import pyautogui
import pyscreenshot
import json
from pyffmpeg import FFmpeg
from threading import Thread
from utils import collect_traces, parse_arguments, collect_iperf_info, track_used_memory, analyze_encryption, check_artifacts_and_save_status, getTransportProtocol
import win32api
from actions import *

pyautogui.FAILSAFE = False


# [Client action] do screenshot
class MakeScreen(Action):
    def parse(self):
        self.action = self.params["action_line"]
        self.test_group = self.params["args"].test_group
        self.screen_path = self.params["screen_path"]
        self.screen_name = self.params["arguments_line"]
        self.current_image_num = self.params["current_image_num"]
        self.current_try = self.params["current_try"]
        self.client_type = self.params["client_type"]
        self.case_json_path = self.params["case_json_path"]

    def execute(self):
        if not self.screen_name:
            make_screen(self.screen_path, None, self.current_try, self.logger)
        else:
            make_screen(self.screen_path, self.case_json_path, self.current_try, self.logger, self.screen_name + self.client_type, self.current_image_num)
            self.params["current_image_num"] += 1
            self.sock.send("done".encode("utf-8"))


def make_screen(screen_path, case_json_path, current_try, logger, screen_name = "", current_image_num = 0):
    screen = pyscreenshot.grab()

    if screen_name:
        screen = screen.convert("RGB")
        screen.save(os.path.join(screen_path, "{:03}_{}_try_{:02}.jpg".format(current_image_num, screen_name, current_try + 1)))

        # Check artifacts
        if case_json_path is not None:
            check_artifacts_and_save_status(os.path.join(screen_path, "{:03}_{}_try_{:02}.jpg".format(current_image_num, screen_name, current_try + 1)), case_json_path, logger)


# [Client action] make sequence of screens with delay. It supports initial delay before the first test case
class SleepAndScreen(Action):
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

        self.logger.info("Finish to do screens")
        self.sock.send("done".encode("utf-8"))


# [Client + Server action] record metrics on client and server sides
class RecordMetrics(Action):
    def parse(self):
        self.action = self.params["action_line"]

    def execute(self):
        if "used_memory" not in self.params["case"]:
            self.params["case"]["used_memory"] = []

        if self.params["args"].track_used_memory:
            track_used_memory(self.params["case"], "client")


# [Client action] record video
class RecordVideo(Action):
    def parse(self):
        self.audio_device_name = self.params["audio_device_name"]
        self.video_path = self.params["output_path"]
        self.video_name = self.params["case"]["case"] + self.params["client_type"]
        self.resolution = self.params["args"].screen_resolution
        self.duration = int(self.params["arguments_line"])
        self.case_json_path = self.params["case_json_path"]
        self.recovery_clumsy = "recovery_second_client_clumsy" in self.params["case"] and self.params["case"]["recovery_second_client_clumsy"]

    def execute(self):
        if self.recovery_clumsy:
            self.logger.info("Recovery Streaming SDK work - close clumsy")
            close_clumsy()

        video_full_path = os.path.join(self.video_path, self.video_name + ".mp4")
        time_flag_value = strftime("%H:%M:%S", gmtime(int(self.duration)))

        recorder = FFmpeg()
        self.logger.info("Start to record video")

        self.logger.info("-f gdigrab -video_size {resolution} -i desktop -f dshow -i audio=\"{audio_device_name}\" -t {time} -q:v 3 -pix_fmt yuv420p {video}"
            .format(resolution=self.resolution, audio_device_name=self.audio_device_name, time=time_flag_value, video=video_full_path))

        recorder.options("-f gdigrab -video_size {resolution} -i desktop -f dshow -i audio=\"{audio_device_name}\" -t {time} -q:v 3 -pix_fmt yuv420p {video}"
            .format(resolution=self.resolution, audio_device_name=self.audio_device_name, time=time_flag_value, video=video_full_path))

        self.logger.info("Finish to record video")

        # Check artifacts
        check_artifacts_and_save_status(video_full_path, self.case_json_path, self.logger, obj_type="video")

        self.sock.send("done".encode("utf-8"))

        if self.params["args"].track_used_memory:
            track_used_memory(self.params["case"], "client") 


class Encryption(Action):
    def parse(self):
        pass

    def execute(self):
        try:
            self.sock.send("start".encode("utf-8"))

            compressing_thread = Thread(target=analyze_encryption, args=(self.params["case"], "second_client", getTransportProtocol(self.params["args"], self.params["case"]), \
                "-encrypt" in self.params["case"]["server_keys"].lower(), self.params["messages"], self.params["args"].ip_address))
            compressing_thread.start()
        except Exception as e:
            self.logger.warning("Failed to validate encryption: {}".format(str(e)))
            self.logger.warning("Traceback: {}".format(traceback.format_exc())) 


class Finish(Action):
    def parse(self):
        pass

    def execute(self):
        pass

    def analyze_result(self):
        self.state.finish_command_received = True
