from time import sleep
import psutil
import os
import subprocess
from subprocess import PIPE
import sys
import traceback
import platform
from enum import Enum
import pyautogui
import pyscreenshot
from threading import Thread
import utils
from games_actions import locate_and_click, locate_on_screen, click_on_element, get_game_window_name
from elements import AMDLinkElements, FSElements
import signal
from locators import FSServerLocators

if platform.system() == "Windows":
    import win32gui
    import win32con
    import win32clipboard
    import pydirectinput
    pydirectinput.FAILSAFE = False

    from selenium import webdriver
    from selenium.webdriver.support.select import Select
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.firefox import GeckoDriverManager

    try:
        WEBDRIVER_VERSION = GeckoDriverManager().install()
    except:
        pass

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import main_logger

pyautogui.FAILSAFE = False


class StreamingType(Enum):
    SDK = 1
    AMD_LINK = 2
    FULL_SAMPLES = 3


def start_streaming(args, case, script_path=None, socket=None, debug_screen_path=None):
    main_logger.info("Start StreamingSDK {}".format(args.execution_type))

    if getattr(args, "streaming_type", None) == None or args.streaming_type == StreamingType.SDK:
        if not script_path:
            raise ValueError("Script path is required to launch Streaming SDK")

        return start_streaming_sdk(args, case, script_path)
    elif args.streaming_type == StreamingType.AMD_LINK:
        if not socket:
            raise ValueError("Socket is required to launch AMD Link")

        return start_streaming_amd_link(args, case, socket, debug_screen_path=debug_screen_path)
    elif args.streaming_type == StreamingType.FULL_SAMPLES:
        if not socket:
            raise ValueError("Socket is required to launch AMD Link")

        return start_full_samples(args, case, socket, script_path=script_path)
    else:
        raise ValueError(f"Unknown StreamingSDK type: {args.streaming_type}")


def start_streaming_sdk(args, case, script_path):
    if platform.system() == "Windows":
        process = psutil.Popen(script_path, stdout=PIPE, stderr=PIPE, shell=True)
    else:
        process = psutil.Popen(f"xterm -e {script_path}", stdout=PIPE, stderr=PIPE, shell=True)

    return process


def set_dropdown_option(case, field_width, param_name):
    label_coords = locate_on_screen(AMDLinkElements.DROPDOWN_OPTIONS_LABELS[param_name].build_path())
    pyautogui.click(label_coords[0] + field_width, label_coords[1] + label_coords[3] / 2)
    locate_and_click(AMDLinkElements.DROPDOWN_OPTIONS_VALUES[param_name][case["server_params"][param_name]].build_path())


def configure_boolean_option(case, field_width, param_name):
    label_coords = locate_on_screen(AMDLinkElements.DROPDOWN_OPTIONS_LABELS[param_name].build_path())
    region = (int(label_coords[0] + field_width - 100), int(label_coords[1]), int(field_width), int(label_coords[3]))
    try:
        coords = locate_on_screen(AMDLinkElements.ENABLED.build_path(), region=region)
        value = True
    except:
        try:
            coords = locate_on_screen(AMDLinkElements.DISABLED.build_path(), region=region)
            value = False
        except:
            raise Exception("Can't determine boolean value")

    if value != case["server_params"][param_name]:
        click_on_element(coords)


def set_adrenalin_params(case):
    # calculate approximate width of option field as distance between AMD Link Server and Stream Resolution labels
    amd_link_coords = locate_on_screen(AMDLinkElements.AMD_LINK_SERVER.build_path())
    resolution_coords = locate_on_screen(AMDLinkElements.STREAM_RESOLUTION.build_path())

    field_width = (resolution_coords[0] - amd_link_coords[0]) / 2

    # select Resolution
    set_dropdown_option(case, field_width, "resolution")

    # select Video Encoding
    set_dropdown_option(case, field_width, "encoding_type")

    # configure Accept All Connections option
    configure_boolean_option(case, field_width, "accept_all_connections")

    # configure Use Encryption option
    configure_boolean_option(case, field_width, "use_encryption")


def start_streaming_amd_link(args, case, socket, debug_screen_path=None):
    if args.execution_type == "server":
        client_already_started = False

        try:
            window = win32gui.FindWindow(None, get_game_window_name(args.game_name))
            utils.hide_window(window)
            sleep(1)
            pyautogui.hotkey("win", "m")
            sleep(1)

            script_path = "C:\\JN\\Adrenalin.lnk"
            process = psutil.Popen(script_path, stdout=PIPE, stderr=PIPE, shell=True)

            # wait AMD Adrenalin window opening
            for i in range(10):
                try:
                    locate_on_screen(AMDLinkElements.ADRENALIN_ICON.build_path())
                    break
                except:
                    sleep(1)
            else:
                raise Exception("Adrenalin tool window wasn't found")

            window_hwnd = None

            for window in pyautogui.getAllWindows():
                if "AMD Software: Adrenalin" in window.title:
                    window_hwnd = window._hWnd
                    break

            if not window_hwnd:
                raise Exception("Adrenalin tool window wasn't found")

            utils.make_window_maximized(window_hwnd)

            try:
                locate_on_screen(AMDLinkElements.AMD_LINK_ACTIVE.build_path())
            except:
                # AMD Link tab isn't opened
                try:
                    locate_and_click(AMDLinkElements.HOME_INACTIVE.build_path())
                except:
                    pass

                # open AMD Link tab if it's required
                coords = locate_on_screen(AMDLinkElements.AMD_LINK_STATUS.build_path(), delay=1)
                pyautogui.click(coords[0] + coords[2] - 15, coords[1] + coords[3] - 15)

            try:
                # enable AMD Link if it's required
                locate_on_screen(AMDLinkElements.ENABLE_AMD_LINK.build_path())
            except:
                pass

            try:
                locate_on_screen(AMDLinkElements.STOP_STREAMING_BUTTON.build_path(), delay=1)
                server_already_started = True
            except:
                server_already_started = False

            try:
                locate_on_screen(AMDLinkElements.PC_ICON.build_path())
                client_already_started = True
            except:
                client_already_started = False

            main_logger.info("Server is already started: {}".format(server_already_started))
            main_logger.info("Client is already started: {}".format(client_already_started))

            if client_already_started:
                locate_and_click(AMDLinkElements.START_STREAMING_BUTTON.build_path(), delay=1)

                socket.send("restart".encode("utf-8"))
            else:
                # receive game invite link
                coords = locate_on_screen(AMDLinkElements.LINK_GAME_INVITE_SERVER.build_path(), delay=1)
                click_on_element(coords)
                sleep(1)
                # sometimes first click not work
                click_on_element(coords)

                if case["server_params"]["streaming_mode"] == "multi_play":
                    link_coords = locate_on_screen(AMDLinkElements.MULTI_PLAY.build_path(), delay=1)
                else:
                    link_coords = locate_on_screen(AMDLinkElements.FULL_ACCESS.build_path(), delay=1)

                # sometimes click not work
                for i in range(3):
                    click_on_element(link_coords)
                    sleep(0.5)

                for i in range(40):
                    try:
                        if case["server_params"]["streaming_mode"] == "multi_play":
                            coords = locate_on_screen(AMDLinkElements.MULTI_PLAY_FRESH_LINK.build_path())
                        else:
                            coords = locate_on_screen(AMDLinkElements.FULL_ACCESS_FRESH_LINK.build_path())
                        break
                    except:
                        sleep(1)
                else:
                    raise Exception("Fresh invitation code wasn't detected")

                
                click_on_element(link_coords)
                sleep(0.5)
                # copy invite code and close window with it
                try:
                    locate_and_click(AMDLinkElements.COPY_TEXT.build_path(), delay=1)
                except:
                    # sometimes click not work
                    click_on_element(link_coords)
                    sleep(0.5)
                    locate_and_click(AMDLinkElements.COPY_TEXT.build_path(), delay=1)

                locate_and_click(AMDLinkElements.CLOSE_INVITE_CODE_WINDOW.build_path(), delay=1)

                sleep(1)
                pyautogui.moveTo(10, 10)
                sleep(2)

                if not server_already_started:
                    locate_and_click(AMDLinkElements.START_STREAMING_BUTTON.build_path(), delay=1)

                    set_adrenalin_params(case)

                    # sometimes Start Streaming button click is ignored. Do it again
                    try:
                        locate_and_click(AMDLinkElements.START_STREAMING_BUTTON.build_path())
                    except:
                        pass

                if debug_screen_path:
                    # save debug screen
                    screen = pyscreenshot.grab()
                    screen = screen.convert("RGB")
                    screen.save(debug_screen_path)

                win32clipboard.OpenClipboard()
                invite_code = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()

                main_logger.info(f"Sending invite code: {invite_code}")

                socket.send(invite_code.encode("utf-8"))

            utils.hide_window(window_hwnd)
        except Exception as e:
            socket.send("failed".encode("utf-8"))

            if debug_screen_path:
                # save debug screen
                screen = pyscreenshot.grab()
                screen = screen.convert("RGB")
                screen.save(debug_screen_path)

            raise e

        # wait answer from client
        while True:
            try:
                answer = socket.recv(1024).decode("utf-8")
                break
            except Exception as e:
                sleep(0.1)
                continue

        if answer != "done":
            raise Exception("Failed to open AMD Link on client side")
    else:
        # wait invite code
        invite_code = socket.recv(1024).decode("utf-8")

        main_logger.info(f"Received invite code: {invite_code}")

        if invite_code == "failed":
           raise Exception("Failed to receive invite code on server side") 

        try:
            pyautogui.hotkey("win", "m")
            sleep(1)

            script_path = "C:\\JN\\AMDLink.lnk"
            process = psutil.Popen(script_path, stdout=PIPE, stderr=PIPE, shell=True)

            if invite_code != "restart":
                # wait AMD Link window opening
                for i in range(10):
                    try:
                        locate_on_screen(AMDLinkElements.AMD_LINK_ICON.build_path())
                        break
                    except:
                        sleep(1)
                else:
                    raise Exception("AMD Link tool window wasn't found")

                window_hwnd = None

                for window in pyautogui.getAllWindows():
                    if "AMD Link" in window.title:
                        window_hwnd = window._hWnd
                        break

                if not window_hwnd:
                    raise Exception("Adrenalin tool window wasn't found")

                utils.make_window_maximized(window_hwnd)
                
                # connect to server
                locate_and_click(AMDLinkElements.CONNECT_TO_PC.build_path(), delay=1)

                locate_and_click(AMDLinkElements.LINK_GAME_INVITE_CLIENT.build_path(), delay=1)

                # focus AMD Link window
                sleep(0.5)
                locate_and_click(AMDLinkElements.SUBMIT_CONNECT_DISABLED.build_path(), delay=1)

                # type invite code and press submit button
                sleep(0.5)
                pyautogui.write(invite_code)
                sleep(1)

                # sometimes click not work
                locate_and_click(AMDLinkElements.SUBMIT_CONNECT.build_path(), delay=1)
                sleep(1)
                try:
                    locate_and_click(AMDLinkElements.SUBMIT_CONNECT.build_path())
                except:
                    pass

                sleep(2)

                # check that submit button was clicked
                try:
                    locate_on_screen(AMDLinkElements.SUBMIT_CONNECT.build_path())
                    submit_button_found = True
                except:
                    submit_button_found = False

                if submit_button_found:
                    raise Exception("Submit button wasn't clicked. Invite code could be invalid / outdated or connection could't be established")

                try:
                    # skip optimizations and start streaming
                    locate_and_click(AMDLinkElements.SKIP_OPTIMIZATION.build_path(), delay=1)
                except:
                    pass

                if case['server_params']['streaming_mode'] == 'full_access':
                    try:
                        locate_and_click(AMDLinkElements.START_STREAMING.build_path(), delay=1)
                    except:
                        try:
                            # Start Streaming button can be hovered
                            locate_and_click(AMDLinkElements.START_STREAMING_2.build_path(), delay=1)
                        except:
                            try:
                                # Sometimes it's necesary to click on lobby icon
                                locate_and_click(AMDLinkElements.LOBBY_ICON.build_path(), delay=1)
                            except:
                                # Lobby icon can be hovered
                                locate_and_click(AMDLinkElements.LOBBY_ICON_2.build_path(), delay=1)

                sleep(5)

            # apply full screen
            try:
                locate_and_click(AMDLinkElements.APPLY_FULL_SCREEN.build_path(), delay=1)
            except:
                pass

            socket.send("done".encode("utf-8"))
        except Exception as e:
            socket.send("failed".encode("utf-8"))
            raise e

    return process


def start_full_samples(args, case, socket, script_path=None):
    process = None

    if platform.system() == "Windows":
        if script_path:
            main_logger.info("Run Full Samples script")
            process = psutil.Popen(script_path)

        if args.execution_type == "server":
            try:
                set_full_samples_server_options(case)
                socket.send("done".encode("utf-8"))
                main_logger.info("Parameters were applied")
            except Exception as e:
                socket.send("failed".encode("utf-8"))
                main_logger.error(f"Failed to set Full Samples server options: {e}")
                main_logger.error("Traceback: {}".format(traceback.format_exc()))

            sleep(4)
        else:
            sleep(3)

            server_answer = socket.recv(1024).decode("utf-8")

            main_logger.info(f"Received server answer code: {server_answer}")

            if server_answer != "done":
               raise Exception("Failed to open Full Samples on server side") 

            # wait Full Samples window opening
            for window in pyautogui.getAllWindows():
                if "RemoteGameClient" in window.title:
                    window_hwnd = window._hWnd
                    break

            if not window_hwnd:
                raise Exception("Full Samples client window wasn't found")

            win32gui.ShowWindow(window_hwnd, win32con.SW_MAXIMIZE)

            # connect Full Samples client to server only if client is just opened
            if script_path:
                connect_full_samples_client(args, case)

    return process


def set_full_samples_server_options(case):
    if "full_samples_settings" in case and len(case["full_samples_settings"]) > 0:
        service = Service(WEBDRIVER_VERSION)
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.headless = True
        driver = webdriver.Chrome(service=service, options=firefox_options)
        sleep(3)
        driver.get("http://localhost")

        for tab, options in case["full_samples_settings"].items():
            utils.find_by_xpath(FSServerLocators.TAB_TEMPLATE.replace("<tab_name>", tab), driver).click()

            sleep(0.5)

            # There are four possible types of options: boolean, select, input and double input (e.g. encoder resolution)

            for option_name, option_value in options.items():
                main_logger.error(f"Set {option_name} option ({tab} tab)")

                if isinstance(option_value, bool):
                    main_logger.info("Set the option value in a flag")
                    element = utils.find_by_xpath(FSServerLocators.BOOLEAN_OPTION_TEMPLATE.replace("<option_name>", option_name), driver)

                    if option_value != element.is_selected():
                        element.click()

                elif isinstance(option_value, str):
                    is_input = False

                    try:
                        element = utils.find_by_xpath(FSServerLocators.SELECT_OPTION_TEMPLATE.replace("<option_name>", option_name), driver)
                    except:
                        element = utils.find_by_xpath(FSServerLocators.INPUT_OPTION_TEMPLATE.replace("<option_name>", option_name), driver)
                        is_input = True

                    if is_input:
                        main_logger.info("Set the option value in an input")
                        element.clear()
                        element.send_keys(option_value)
                    else:
                        main_logger.info("Set the option value in a select")
                        Select(element).select_by_value(option_value)
                elif isinstance(option_value, list):
                    main_logger.info("Set the option value in two inputs")
                    first_element = utils.find_by_xpath(FSServerLocators.INPUT_OPTION_TEMPLATE_FIRST.replace("<option_name>", option_name), driver)
                    second_element = utils.find_by_xpath(FSServerLocators.INPUT_OPTION_TEMPLATE_SECOND.replace("<option_name>", option_name), driver)

                    first_element.clear()
                    first_element.send_keys(option_value[0])

                    second_element.clear()
                    second_element.send_keys(option_value[1])
                else:
                    raise ValueError(f"Unknown value type for option '{option_name}' of tab '{tab}'")

        utils.find_by_xpath(FSServerLocators.APPLY_BUTTON, driver).click()

        driver_closing_thread = Thread(target=driver.close, args=())
        driver_closing_thread.start()


def connect_full_samples_client(args, case):
    coords = locate_on_screen(FSElements.CONNECT_TO.build_path(), tries=7, delay=1, step=0.02)

    pyautogui.click(coords[0] + coords[2] + 35, coords[1] + coords[3] / 2)

    if utils.getTransportProtocol(args, case) == "udp":
        pyautogui.moveTo(coords[0] + coords[2] + 35, coords[1] + coords[3] / 2 + 25)
    else:
        pyautogui.moveTo(coords[0] + coords[2] + 35, coords[1] + coords[3] / 2 + 45)

    sleep(0.1)
    pyautogui.click()
    sleep(0.1)

    pyautogui.press("tab")
    sleep(0.1)
    pyautogui.press("backspace", presses=30)
    sleep(0.1)
    pyautogui.typewrite(args.ip_address)

    sleep(0.1)

    pyautogui.press("tab")
    sleep(0.1)
    pyautogui.press("backspace", presses=30)
    sleep(0.1)
    pyautogui.typewrite("1235")

    sleep(0.1)

    if "client_password" in case:
        pyautogui.press("tab")
        sleep(0.1)
        pyautogui.press("backspace", presses=30)
        sleep(0.1)
        pyautogui.typewrite(case["client_password"])

    locate_and_click(FSElements.CONNECT.build_path())


def close_streaming(args, case, process):
    try:
        if getattr(args, "streaming_type", None) == None or args.streaming_type == StreamingType.SDK:
            return close_streaming_sdk(args, case, process)
        elif args.streaming_type == StreamingType.AMD_LINK:
            return close_streaming_amd_link(args, case, process)
        elif args.streaming_type == StreamingType.FULL_SAMPLES:
            return close_full_samples(args, case, process)
        else:
            raise ValueError(f"Unknown StreamingSDK type: {args.streaming_type}")
    except Exception as e:
        main_logger.error("Failed to close Streaming SDK process. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        return None


def close_streaming_sdk(args, case, process):
    if utils.should_case_be_closed(args.execution_type, case):
        # close the current Streaming SDK process
        main_logger.info("Start closing")

        if platform.system() == "Windows":
            if args.execution_type != "server":
                for window in pyautogui.getAllWindows():
                    if "RemoteGameClient" in window.title:
                        streaming_window = window._hWnd
                        break

                win32gui.PostMessage(streaming_window, win32con.WM_CLOSE, 0, 0)
            else:
                close_streaming_server_process(process)

            if args.execution_type == "server":
                crash_window = win32gui.FindWindow(None, "RemoteGameServer.exe")
            else:
                crash_window = win32gui.FindWindow(None, "RemoteGameClient.exe")

            if crash_window:
                main_logger.info("Crash window was found. Closing it...")
                win32gui.PostMessage(crash_window, win32con.WM_CLOSE, 0, 0)
        else:
            close_streaming_server_process(process)

        main_logger.info("Finish closing")

        return None
    else:
        main_logger.info("Keep StreamingSDK instance")

    return process


def close_streaming_amd_link(args, case, process):
    if utils.should_case_be_closed(args.execution_type, case):
        # close the current Streaming SDK process
        main_logger.info("Start closing") 

        if args.execution_type == "server":
            # wait closing on client
            sleep(3)

            window = win32gui.FindWindow(None, get_game_window_name(args.game_name))
            utils.hide_window(window)
            sleep(1)
            pyautogui.hotkey("win", "m")
            sleep(1)

            script_path = "C:\\JN\\Adrenalin.lnk"
            process = psutil.Popen(script_path, stdout=PIPE, stderr=PIPE, shell=True)

            # wait AMD Adrenalin window opening
            for i in range(10):
                try:
                    locate_on_screen(AMDLinkElements.ADRENALIN_ICON.build_path())
                    break
                except:
                    sleep(1)
            else:
                raise Exception("Adrenalin tool window wasn't found")

            window_hwnd = None

            for window in pyautogui.getAllWindows():
                if "AMD Software: Adrenalin" in window.title:
                    window_hwnd = window._hWnd
                    break

            if not window_hwnd:
                raise Exception("Adrenalin tool window wasn't found")

            utils.make_window_maximized(window_hwnd)

            # make a click on Adrenalin tool
            locate_and_click(AMDLinkElements.ADRENALIN_ICON.build_path(), delay=1)

            # stop Streaming SDK server if it isn't done automatically
            try:
                locate_and_click(AMDLinkElements.STOP_STREAMING_BUTTON.build_path(), delay=1)
            except:
                pass

        elif args.execution_type == "client":
            for window in pyautogui.getAllWindows():
                if "AMD Link" in window.title:
                    amd_link_window = window._hWnd
                    break

            win32gui.PostMessage(amd_link_window, win32con.WM_CLOSE, 0, 0)

            sleep(3)

        main_logger.info("Finish closing")

        return None
    else:
        main_logger.info("Keep StreamingSDK instance")

    return process


def close_full_samples(args, case, process):
    if utils.should_case_be_closed(args.execution_type, case):
        # close the current Streaming SDK process
        main_logger.info("Start closing")

        if platform.system() == "Windows":
            if args.execution_type != "server":
                for window in pyautogui.getAllWindows():
                    if "RemoteGameClient" in window.title:
                        streaming_window = window._hWnd
                        break

                win32gui.PostMessage(streaming_window, win32con.WM_CLOSE, 0, 0)
            else:
                close_streaming_server_process(process)

        main_logger.info("Finish closing")

        return None
    else:
        main_logger.info("Keep Full Samples instance")

    return process


def close_streaming_server_process(process):
    stop_signal = signal.SIGINT

    child_processes = []

    try:
        child_processes = process.children()
    except psutil.NoSuchProcess:
        pass

    # StreamingSDK server is a child process
    for ch in child_processes:
        try:
            main_logger.info(ch.pid)
            main_logger.info(ch.name())
            os.kill(ch.pid, stop_signal)
            sleep(0.5)
            status = process.status()
            main_logger.info("Process is still alive. Try to send sigint second time")
            os.kill(ch.pid, stop_signal)
            sleep(0.5)
            status = process.status()
            main_logger.info("Process is still alive. Try to force terminate process")
            utils.terminate_process(ch.pid)
            status = process.status()
            raise Exception("Process is alive after force termination")
        except psutil.NoSuchProcess:
            pass

    # try to close cmd/terminal process
    try:
        main_logger.info(process.pid)
        main_logger.info(process.name())
        os.kill(process.pid, stop_signal)
    except:
        pass
