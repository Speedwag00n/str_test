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
import json
import multiprocessing
import platform
from threading import Thread
from PIL import Image

if platform.system() == "Windows":
    import win32api
    import win32gui
    import win32con


def locate_on_screen(template, scale=True, tries=3, delay=0, **kwargs):
    coords = None
    if not "confidence" in kwargs:
        if scale:
            kwargs["confidence"] = 0.75
            # pyautogui locateOnScreen doesn't consider scale of elements
            # scale screenshots of elements with a small step to pick up the necessary scale
            # screenshots of elements made on 2k resolution (16:9). Screenshots are supported for up to 4k (16:10 and 16:9) resolution or down to full hd (16:10 and 16:9) resolution
            scale_up = False
        else:
            kwargs["confidence"] = 0.95

    while not coords and tries > 0 and kwargs["confidence"] > 0:
        with Image.open(template) as img:
            if scale:
                scaling_try = 0
                # Examples
                # scale up 10 times -> 2560 * 150% = 3840;  (4k 16:9)
                # scale up 12 times -> 2560 * 160% = 4096 (4k 16:10)
                # scale down 5 times -> 2560 * 75% = 1920 (full hd 16:9 or full hd 19:10)
                max_scaling_tries = 12 if scale_up else 10
                while not coords and max_scaling_tries > scaling_try:
                    # change size with step in 5% of width and height
                    print(scaling_try)
                    print(kwargs["confidence"])
                    if scale_up:
                        image = img.resize((int(img.width + img.width * scaling_try * 5 / 100), int(img.height + img.height * scaling_try * 5 / 100)))
                    else:
                        image = img.resize((int(img.width - img.width * scaling_try * 5 / 100), int(img.height - img.height * scaling_try * 5 / 100)))

                    coords = pyautogui.locateOnScreen(image, **kwargs)

                    scaling_try += 1
            else:
                coords = pyautogui.locateOnScreen(img, **kwargs)

        tries -= 1
        kwargs["confidence"] -= 0.07

        if not coords and delay:
            sleep(delay)
    if not coords:
        raise Exception("No such element on screen")
    return (coords[0], coords[1], coords[2], coords[3])


print(locate_on_screen("workshop_maps.png"))
