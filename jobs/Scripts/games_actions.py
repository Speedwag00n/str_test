from time import sleep
import psutil
import os
import subprocess
from subprocess import PIPE, STDOUT
import sys
import traceback
import pyautogui
import json
import platform
from PIL import Image
import keyboard
from elements import *

if platform.system() == "Windows":
    import win32api
    import win32gui
    import pydirectinput
    pydirectinput.FAILSAFE = False

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import main_logger


def close_game(game_name):
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

    if game_name == "lol":
        pydirectinput.keyDown("esc")
        sleep(0.1)
        pydirectinput.keyUp("esc")

        sleep(2)

        pyautogui.moveTo(center_x - 360, center_y + 335)
        sleep(0.2)
        pyautogui.mouseDown()
        sleep(0.2)
        pyautogui.mouseUp()
        sleep(0.2)
        pyautogui.mouseDown()
        sleep(0.2)
        pyautogui.mouseUp()

        sleep(1)

        pyautogui.moveTo(center_x - 130, center_y - 50)
        sleep(0.2)
        pyautogui.mouseDown()
        sleep(0.2)
        pyautogui.mouseUp()

        sleep(3)
    elif game_name == "pubg":
        subprocess.call("taskkill /f /im TslGame.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


def close_game_process(game_name):
    try:
        games_processes = {
            "heavendx9": ["browser_x86.exe", "Heaven.exe"],
            "heavendx11": ["browser_x86.exe", "Heaven.exe"],
            "heavenopengl": ["browser_x86.exe", "Heaven.exe"],
            "valleydx9": ["browser_x86.exe", "Valley.exe"],
            "valleydx11": ["browser_x86.exe", "Valley.exe"],
            "valleyopengl": ["browser_x86.exe", "Valley.exe"],
            "borderlands3": ["Borderlands3.exe"],
            "apexlegends": ["r5apex.exe"],
            "valorant": ["VALORANT-Win64-Shipping.exe"],
            "lol": ["LeagueClient.exe", "League of Legends.exe"],
            "csgo": ["csgo.exe"],
            "dota2dx11": ["dota2.exe"],
            "dota2vulkan": ["dota2.exe"],
            "pubg": ["TslGame.exe"]
        }

        if game_name in games_processes:
            processes_names = games_processes[game_name]

            for process in psutil.process_iter():
                if process.name() in processes_names:
                    process.kill()
                    main_logger.info("Target game process found. Close it")

    except Exception as e:
        main_logger.error("Failed to close game process. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


def locate_on_screen(template, scale=False, tries=3, delay=0, step=0.07, **kwargs):
    coords = None
    if not "confidence" in kwargs:
        if scale:
            kwargs["confidence"] = 0.75
            # pyautogui locateOnScreen doesn't consider scale of elements
            # scale screenshots of elements with a small step to pick up the necessary scale
            # screenshots of elements made on 2k resolution (16:9). Screenshots are supported for up to 4k (16:10 and 16:9) resolution or down to full hd (16:10 and 16:9) resolution
            scale_up = win32api.GetSystemMetrics(0) >= 2560
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
                max_scaling_tries = 14 if scale_up else 7
                while not coords and max_scaling_tries > scaling_try:
                    # change size with step in 5% of width and height
                    if scale_up:
                        image = img.resize((int(img.width + img.width * scaling_try * 5 / 100), int(img.height + img.height * scaling_try * 5 / 100)))
                    else:
                        image = img.resize((int(img.width - img.width * scaling_try * 5 / 100), int(img.height - img.height * scaling_try * 5 / 100)))

                    coords = pyautogui.locateOnScreen(image, **kwargs)

                    scaling_try += 1
            else:
                coords = pyautogui.locateOnScreen(img, **kwargs)

        tries -= 1
        kwargs["confidence"] -= step

        if not coords and delay:
            sleep(delay)
    if not coords:
        raise Exception("No such element on screen")
    return (coords[0], coords[1], coords[2], coords[3])


# do click on center with flexible offsets
def click_on_element(coords, x_offset=0, y_offset=0):
    x = coords[0] + coords[2] / 2 + x_offset
    y = coords[1] + coords[3] / 2 + y_offset
    pyautogui.moveTo(x, y)
    sleep(0.3)
    pyautogui.click()
    main_logger.info("Click at x = {}, y = {}".format(x, y))


def locate_and_click(template, scale=False, tries=3, delay=0, x_offset=0, y_offset=0, **kwargs):
    coords = locate_on_screen(template, scale=scale, tries=tries, delay=delay, **kwargs)
    click_on_element(coords, x_offset=x_offset, y_offset=y_offset)


def prepare_game(game_name, game_launcher, fullscreen=True):
    if game_name == "heavendx9" or game_name == "heavendx11" or game_name == "heavenopengl":
        sleep(6)

        if platform.system() == "Windows":
            coords = locate_on_screen(HeavenElements.API_LABEL.build_path())
            click_on_element(coords, x_offset=50)

            sleep(0.5)

            if game_name == "heavendx11":
                click_on_element(coords, x_offset=50, y_offset=15)
            elif game_name == "heavendx9":
                click_on_element(coords, x_offset=50, y_offset=30)
            else:
                click_on_element(coords, x_offset=50, y_offset=45)

            sleep(0.5)

            if fullscreen:
                try:
                    locate_and_click(HeavenElements.WINDOWED.build_path(), tries=1)
                except:
                    pass
            else:
                try:
                    locate_and_click(HeavenElements.FULL_SCREEN.build_path(), tries=1)
                except:
                    pass

            sleep(0.5)

            locate_and_click(HeavenElements.RUN_BUTTON.build_path())
        else:
            locate_and_click(HeavenElements.RUN_BUTTON_UBUNTU.build_path())

        if platform.system() == "Windows":
            subprocess.call("taskkill /f /im browser_x86.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)

        sleep(20)
    if game_name == "valleydx9" or game_name == "valleydx11" or game_name == "valleyopengl":
        sleep(6)

        if platform.system() == "Windows":
            coords = locate_on_screen(ValleyElements.API_LABEL.build_path())
            click_on_element(coords, x_offset=50)

            sleep(0.5)

            if game_name == "valleydx11":
                click_on_element(coords, x_offset=50, y_offset=15)
            elif game_name == "valleydx9":
                click_on_element(coords, x_offset=50, y_offset=30)
            else:
                click_on_element(coords, x_offset=50, y_offset=45)

            sleep(0.5)

            if fullscreen:
                try:
                    locate_and_click(ValleyElements.WINDOWED.build_path(), tries=1)
                except:
                    pass
            else:
                try:
                    locate_and_click(ValleyElements.FULL_SCREEN.build_path(), tries=1)
                except:
                    pass

            sleep(0.5)

            locate_and_click(ValleyElements.RUN_BUTTON.build_path())
        else:
            locate_and_click(ValleyElements.RUN_BUTTON_UBUNTU.build_path())

        if platform.system() == "Windows":
            subprocess.call("taskkill /f /im browser_x86.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)

        sleep(20)
    elif game_name == "valorant":
        sleep(60)
        click("380", "edge_-225")
        sleep(1)
        click("360", "210")
        sleep(60)

        # do opening of lobby twice to avoid ads
        click("center_0", "25")
        sleep(3)

        press_keys("esc")

        click("center_0", "25")
        sleep(3)

        click("center_-300", "edge_-95")
        sleep(3)

        click("center_0", "center_225")
        sleep(30)

        click("center_-260", "center_-55")
        sleep(2)
        click("center_0", "center_110")
    elif game_name == "lol":
        # TODO: check find Play button and click on it
        sleep(90)
        click("center_-15", "center_-160")
        sleep(1)
        coords = locate_on_screen(LoLElements.PLAY_BUTTON.build_path(), tries=4, delay=15)
        click_on_element(coords)
        sleep(0.5)
        click_on_element(coords)
        sleep(1)
        locate_and_click(LoLElements.TRAINING_BUTTON.build_path())
        sleep(1)
        locate_and_click(LoLElements.PRACTICE_TOOL.build_path())
        sleep(1)
        locate_and_click(LoLElements.CONFIRM_BUTTON.build_path())
        sleep(1)
        locate_and_click(LoLElements.START_GAME_ACTIVE.build_path())
        sleep(1)
        locate_and_click(LoLElements.MALPHITE_ICON.build_path())
        sleep(1)
        locate_and_click(LoLElements.LOCK_IN_BUTTON.build_path())
        sleep(45)
        click("center_0", "center_0")
        sleep(1)
        click("center_10", "center_10")
        press_keys("shift+x ctrl+shift+i shift+y:3 ctrl+e ctrl+r")
        press_keys("y")
    elif game_name == "dota2dx11" or game_name == "dota2vulkan":
        sleep(60)
        press_keys("esc")
        sleep(1)

        # click on arcade to disable lighting from Dota2 logo
        locate_and_click(Dota2Elements.ARCADE.build_path(), scale=True)
        sleep(1)
        locate_and_click(Dota2Elements.SETTINGS_BUTTON.build_path(), scale=True)
        sleep(1)
        locate_and_click(Dota2Elements.VIDEO_TAB.build_path(), scale=True)
        sleep(1)
        locate_and_click(Dota2Elements.RENDER_API_SELECTION.build_path(), scale=True)
        sleep(1)
        if game_name == "dota2dx11":
            locate_and_click(Dota2Elements.RENDER_API_DX11_OPTION.build_path(), scale=True)
        else:
            locate_and_click(Dota2Elements.RENDER_API_VULKAN_OPTION.build_path(), scale=True)
        sleep(1)
        press_keys("esc")
        sleep(3)
        locate_and_click(Dota2Elements.EXIT_BUTTON.build_path(), scale=True)
        sleep(1)
        locate_and_click(Dota2Elements.YES_BUTTON.build_path(), scale=True)
        sleep(1)

        psutil.Popen(game_launcher, stdout=PIPE, stderr=PIPE, shell=True)
        sleep(60)
        press_keys("esc")
        sleep(1)

        locate_and_click(Dota2Elements.ARCADE.build_path(), scale=True)
        sleep(1)
        locate_and_click(Dota2Elements.HEROES.build_path(), scale=True)
        sleep(1)
        pyautogui.typewrite("sand king", interval=0.15)
        sleep(0.5)
        press_keys("enter")
        sleep(1)
        locate_and_click(Dota2Elements.DEMO_HERO.build_path(), scale=True)
        sleep(15)
        locate_and_click(Dota2Elements.FREE_SPELLS.build_path(), scale=True)
        sleep(1)
        locate_and_click(Dota2Elements.LVL_MAX.build_path(), scale=True)
        sleep(1)
    elif game_name == "csgo":
        sleep(30)
        press_keys("esc")
        sleep(3)
        press_keys("esc")
        sleep(3)
        locate_and_click(CSGOElements.PLAY_BUTTON.build_path(), scale=True)
        sleep(1)
        pyautogui.moveTo(1, 1)
        sleep(1)
        locate_and_click(CSGOElements.MODE_SELECTION.build_path(), scale=True)
        sleep(1)
        locate_and_click(CSGOElements.WORKSHOP_MAPS.build_path(), scale=True)
        sleep(1)
        locate_and_click(CSGOElements.TRAINING_MAP.build_path(), scale=True)
        sleep(1)
        # go button has dynamic background. try finding it few times
        for i in range(3):
            try:
                locate_and_click(CSGOElements.SELECT_MAP_BUTTON.build_path(), scale=True)
                break
            except Exception as e:
                sleep(1)
                main_logger.warning(f"Select map button wasn't found: {e}")
        else:
            raise Exception("Select map button wasn't found at all")
        sleep(1)
        locate_and_click(CSGOElements.GO_BUTTON.build_path(), scale=True)
        sleep(40)
        press_keys("w_3")

        # enter commands to csgo console
        commands = [
            "`",
            "sv_cheats 1",
            "give weapon_deagle",
            "give weapon_molotov",
            "sv_infinite_ammo 1",
            "`"
        ]
        for command in commands:
            if command != "`":
                keyboard.write(command)
            else:
                pydirectinput.press("`")
            sleep(0.5)
            pydirectinput.press("enter")

    elif game_name == "pubg":
        sleep(90)

        try:
            locate_and_click(PUBGElements.RIGHT_ARROW.build_path(), scale=True)
            sleep(0.5)
            pydirectinput.click()
        except:
            press_keys("esc")
            locate_and_click(PUBGElements.RIGHT_ARROW.build_path(), scale=True)
            sleep(0.5)
            pydirectinput.click()

        sleep(0.5)
        locate_and_click(PUBGElements.PLAY_BUTTON.build_path(), scale=True)
        sleep(30)


def press_keys(keys_string):
    keys = keys_string.split()

    # press keys one by one
    # possible formats
    # * space - press space
    # * space_10 - press space down for 10 seconds
    # * space+shift - press space and shift
    # * space+shift:10 - press space and shift 10 times
    for i in range(len(keys)):
        key = keys[i]

        duration = 0

        if "_" in key:
            parts = key.split("_")
            key = parts[0]
            duration = int(parts[1])

        main_logger.info("Press: {}. Duration: {}".format(key, duration))

        if duration == 0:
            times = 1

            if ":" in key:
                parts = key.split(":")
                key = parts[0]
                times = int(parts[1])

            keys_to_press = key.split("+")

            for i in range(times):
                for key_to_press in keys_to_press:
                    if platform.system() == "Windows":
                        pydirectinput.keyDown(key_to_press)
                    else:
                        pyautogui.keyDown(key_to_press)

                sleep(0.1)

                for key_to_press in keys_to_press:
                    if platform.system() == "Windows":
                        pydirectinput.keyUp(key_to_press)
                    else:
                        pyautogui.keyUp(key_to_press)

                sleep(0.5)
        else:
            keys_to_press = key.split("+")

            for key_to_press in keys_to_press:
                if platform.system() == "Windows":
                    pydirectinput.keyDown(key_to_press)
                else:
                    pyautogui.keyDown(key_to_press)

            sleep(duration)

            for key_to_press in keys_to_press:
                if platform.system() == "Windows":
                    pydirectinput.keyUp(key_to_press)
                else:
                    pyautogui.keyUp(key_to_press)

        # if it isn't the last key - make a delay
        if i != len(keys) - 1:
            if "enter" in key:
                sleep(2)
            else:
                sleep(1)


def click(x_description, y_description, delay = 0.2):
    if platform.system() == "Windows":
        edge_x = win32api.GetSystemMetrics(0)
        edge_y = win32api.GetSystemMetrics(1)
    else:
        process = subprocess.Popen("xdpyinfo | awk '/dimensions/{print $2}'", stdout=PIPE, shell=True)
        stdout, stderr = process.communicate()
        edge_x, edge_y = stdout.decode("utf-8").strip().split("x")
        edge_x = int(edge_x)
        edge_y = int(edge_y)

    if "center_" in x_description:
        x = edge_x / 2 + int(x_description.replace("center_", ""))
    elif "edge_" in x_description:
        x = edge_x + int(x_description.replace("edge_", ""))
    else:
        x = int(x_description)

    if "center_" in y_description:
        y = edge_y / 2 + int(y_description.replace("center_", ""))
    elif "edge_" in y_description:
        y = edge_y + int(y_description.replace("edge_", ""))
    else:
        y = int(y_description)

    main_logger.info("Click at x = {}, y = {}".format(x, y))

    pyautogui.moveTo(x, y)
    sleep(delay)
    pyautogui.click()


def get_game_window_name(game_name):
    games_windows = {
        "Windows": {
            "heavendx9": "Unigine Heaven Benchmark 4.0 Basic (Direct3D9)",
            "heavendx11": "Unigine Heaven Benchmark 4.0 Basic (Direct3D11)",
            "heavenopengl": "Unigine Heaven Benchmark 4.0 Basic (OpenGL)",
            "valleydx9": "Unigine Valley Benchmark 1.0 Basic (Direct3D9)",
            "valleydx11": "Unigine Valley Benchmark 1.0 Basic (Direct3D11)",
            "valleyopengl": "Unigine Valley Benchmark 1.0 Basic (OpenGL)",
            "valorant": "VALORANT  ",
            "lol": "League of Legends (TM) Client",
            "dota2dx11": "Dota 2",
            "dota2vulkan": "Dota 2",
            "csgo": "Counter-Strike: Global Offensive - Direct3D 9",
            "pubg": "PUBG: BATTLEGROUNDS ",
            "empty": None
        },
        "Linux": {
            "heavenopengl": "Unigine Heaven Benchmark 4.0 (Basic Edition)",
            "valleyopengl": "Unigine Valley Benchmark (Basic Edition)"
        }
    }

    if platform.system() == "Windows":
        return games_windows["Windows"][game_name.lower()]
    else:
        return games_windows["Linux"][game_name.lower()]


def get_game_process_name(game_name):
    games_windows = {
        "Windows": {
            "heavendx9": "Heaven.exe",
            "heavendx11": "Heaven.exe",
            "heavenopengl": "Heaven.exe",
            "valleydx9": "Valley.exe",
            "valleydx11": "Valley.exe",
            "valleyopengl": "Valley.exe",
            "valorant": "VALORANT-Win64-Shipping.exe",
            "lol": "League of Legends.exe",
            "dota2dx11": "dota2.exe",
            "dota2vulkan": "dota2.exe",
            "csgo": "csgo.exe",
            "pubg": "TslGame.exe",
            "empty": None
        },
        "Linux": {
            "heavenopengl": "heaven_x64",
            "valleyopengl": "valley_x64"
        }
    }

    if platform.system() == "Windows":
        return games_windows["Windows"][game_name.lower()]
    else:
        return games_windows["Linux"][game_name.lower()]


def get_game_launcher_path(game_name):
    games_launchers = {
        "Windows": {
            "heavendx9": "C:\\JN\\Heaven Benchmark 4.0.lnk",
            "heavendx11": "C:\\JN\\Heaven Benchmark 4.0.lnk",
            "heavenopengl": "C:\\JN\\Heaven Benchmark 4.0.lnk",
            "valleydx9": "C:\\JN\\Valley Benchmark 1.0.lnk",
            "valleydx11": "C:\\JN\\Valley Benchmark 1.0.lnk",
            "valleyopengl": "C:\\JN\\Valley Benchmark 1.0.lnk",
            "valorant": "C:\\JN\\VALORANT.exe - Shortcut.lnk",
            "lol": "C:\\JN\\League of Legends.lnk",
            "dota2dx11": "C:\\JN\\dota2.exe.lnk",
            "dota2vulkan": "C:\\JN\\dota2.exe.lnk",
            "csgo": "C:\\JN\\csgo.exe.url",
            "pubg": "C:\\JN\\pubg.url",
            "empty": None
        },
        "Linux": {
            "heavenopengl": "/scripts/launch_heaven",
            "valleyopengl": "/scripts/launch_valley"
        }
    }

    if platform.system() == "Windows":
        return games_launchers["Windows"][game_name.lower()]
    else:
        return games_launchers["Linux"][game_name.lower()]
