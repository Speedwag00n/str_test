import sys
import json
import os
import argparse
from statistics import stdev, mean
import re
import traceback

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
    )
)

from jobs_launcher.core.config import *


def get_framerate(keys):
    if '-Framerate ' in keys:
        return int(keys.split('-Framerate')[1].split()[0])
    else:
        return 30

def get_qos_status(keys):
    if '-QoS ' in keys:
        value = keys.split('-QoS')[1].split()[0]
        return value != "False" and value != "false"
    else:
        return True

def get_resolution(keys):
    if '-Resolution' in keys:
        return keys.split('-Resolution')[1].split()[0]
    else:
        return '2560,1440'

def get_codec(keys):
    if '-Codec' in keys:
        return keys.split('-Codec')[1].split()[0]
    else:
        return 'h.265'

def get_capture(keys):
    if '-Capture' in keys:
        return keys.split('-Capture')[1].split()[0]
    else:
        return 'amd'

def parse_block_line(line, saved_values):
    if 'Average latency' in line:
        # Line example:
        # 2021-05-31 09:01:55.469     3F90 [RemoteGamePipeline]    Info: Average latency: full 35.08, client  1.69, server 21.83, encoder  3.42, network 11.56, decoder  1.26, Rx rate: 122.67 fps, Tx rate: 62.33 fps
        if 'client' in line:
            if 'client_latencies' not in saved_values:
                saved_values['client_latencies'] = []

            client_latency = float(line.split('client')[1].split(',')[0])
            saved_values['client_latencies'].append(client_latency)

        if 'server' in line:
            if 'server_latencies' not in saved_values:
                saved_values['server_latencies'] = []

            server_latency = float(line.split('server')[1].split(',')[0])
            saved_values['server_latencies'].append(server_latency)

        if 'network' in line:
            if 'network_latencies' not in saved_values:
                saved_values['network_latencies'] = []

            network_latency = float(line.split('network')[1].split(',')[0])
            saved_values['network_latencies'].append(network_latency)  

        if 'encoder' in line:
            if 'encoder_values' not in saved_values:
                saved_values['encoder_values'] = []

            encoder_value = float(line.split('encoder')[1].split(',')[0])
            saved_values['encoder_values'].append(encoder_value)

        if 'decoder' in line:
            if 'decoder_values' not in saved_values:
                saved_values['decoder_values'] = []

            decoder_value = float(line.split('decoder')[1].split(',')[0])
            saved_values['decoder_values'].append(decoder_value)      

        if 'Rx rate:' in line:
            if 'rx_rates' not in saved_values:
                saved_values['rx_rates'] = []

            rx_rate = float(line.split('Rx rate:')[1].split(',')[0].replace('fps', ''))
            saved_values['rx_rates'].append(rx_rate)

        if 'Tx rate:' in line:
            if 'tx_rates' not in saved_values:
                saved_values['tx_rates'] = []

            tx_rate = float(line.split('Tx rate:')[1].split(',')[0].replace('fps', ''))
            saved_values['tx_rates'].append(tx_rate)

    elif 'Queue depth' in line:
        # Line example:
        # 2021-07-07 13:43:17.038      A60 [RemoteGamePipeline]    Info: Queue depth: Encoder: 0, Decoder: 0
        if 'queue_encoder_values' not in saved_values:
            saved_values['queue_encoder_values'] = []

        queue_encoder_value = float(line.split('Encoder:')[1].split(',')[0])
        saved_values['queue_encoder_values'].append(queue_encoder_value)

        if 'queue_decoder_values' not in saved_values:
            saved_values['queue_decoder_values'] = []

        queue_decoder_value = float(line.split('Decoder:')[1].split(',')[0])
        saved_values['queue_decoder_values'].append(queue_decoder_value)

    elif 'A/V desync' in line:
        # Line example:
        # 2021-07-07 13:43:23.081      A60 [RemoteGamePipeline]    Info: A/V desync:  1.29 ms, video bitrate: 20.00 Mbps
        if 'decyns_values' not in saved_values:
            saved_values['decyns_values'] = []

        decyns_values = float(line.split('desync:')[1].split(',')[0].replace('ms', ''))
        saved_values['decyns_values'].append(decyns_values)

        if 'video_bitrate' not in saved_values:
            saved_values['video_bitrate'] = []

        video_bitrate = float(line.split('video bitrate:')[1].replace('Mbps', ''))
        saved_values['video_bitrate'].append(video_bitrate)

    elif 'Average bandwidth' in line:
        # Line example:
        # 2021-07-07 13:43:32.160      A60 [RemoteGamePipeline]    Info: Average bandwidth: Tx: 16794.37 kbps (video/audio/user: 16255.78/139.55/ 0.00), Rx: 147.09 kbps (ctrl/audio/user: 147.09/ 0.00/ 0.00)
        if 'average_bandwidth_tx' not in saved_values:
            saved_values['average_bandwidth_tx'] = []

        average_bandwidth_tx = float(line.split('user:')[1].split('/')[0])
        saved_values['average_bandwidth_tx'].append(average_bandwidth_tx)

    elif 'Send time (avg/worst)' in line:
        # Line example:
        # 2021-07-07 13:43:23.082      A60 [RemoteGamePipeline]    Info: Send time (avg/worst):  0.05/ 5.95 ms
        if 'send_time_avg' not in saved_values:
            saved_values['send_time_avg'] = []

        send_time_avg = float(line.split('(avg/worst):')[1].split('/')[0])
        saved_values['send_time_avg'].append(send_time_avg)

        if 'send_time_worst' not in saved_values:
            saved_values['send_time_worst'] = []

        send_time_worst = float(line.split('/')[2].replace('ms', ''))
        saved_values['send_time_worst'].append(send_time_worst)


def parse_line(line, saved_values):
    if 'Bitrate: ' in line:
        if 'bitrate' not in saved_values:
            saved_values['bitrate'] = set()

        bitrate = float(line.split('Bitrate: ')[1].replace('bps', '').strip()) / 1000000
        saved_values['bitrate'].add(bitrate)

    elif 'HEVC Video bitrate changed to' in line:
        # Line example:
        # 2021-10-10 22:11:45.335     153C [VideoPipeline]    Info: HEVC Video bitrate changed to 50.00 Mbps for left eye
        if 'hevc_video_bitrate' not in saved_values:
            saved_values['hevc_video_bitrate'] = set()

        hevc_video_bitrate = float(line.split('changed to')[1].split()[0])
        saved_values['hevc_video_bitrate'].add(hevc_video_bitrate)

    elif 'VIDEO_OP_CODE_FORCE_IDR' in line:
        saved_values['code_force_idr'] = True

    elif 'Input Queue Full' in line:
        saved_values['input_queue_full'] = True


def parse_error(line, saved_errors):
    error_message = line.split(':', maxsplit = 3)[3].split('.')[0].replace('fps', '').strip()

    parts = error_message.split()
    if '(' in parts[-1]:
        error_message = error_message.split('(')[0]
    elif parts[-1].isdigit():
        parts.pop()
        error_message = " ".join(parts)

    error_message = re.sub(r' at$| to$| -$| =$', '', error_message).strip()

    if error_message and error_message not in saved_errors:
        saved_errors.append(error_message)


def update_status(json_content, case, saved_values, saved_errors, framerate, execution_type):
    if "client_latencies" not in saved_values or "server_latencies" not in saved_values:
        json_content["test_status"] = "error"
        json_content["message"].append("Application problem: Client could not connect")
    elif max(saved_values["client_latencies"]) == 0 or max(saved_values["server_latencies"]) == 0:
        json_content["test_status"] = "error"
        json_content["message"].append("Application problem: Client could not connect")
    else:

        if 'encoder_values' in saved_values:
            # rule №15: ignore rules 1.1 and 1.2 if Capture dd
            # rule №1.1: encoder >= framerate -> problem with app
            # ignore for Android
            if get_capture(case["prepared_keys"]) != "dd" and get_capture(case["prepared_keys"]) != "false":
                if execution_type != "android":
                    bad_encoder_value = None

                    for encoder_value in saved_values['encoder_values']:
                        # find the worst value
                        if encoder_value >= framerate:
                            if bad_encoder_value is None or bad_encoder_value < encoder_value:
                                bad_encoder_value = encoder_value

                    if bad_encoder_value:
                        json_content["message"].append("Application problem: Encoder is equal to or bigger than framerate. Encoder  {}. Framerate: {}".format(bad_encoder_value, framerate))
                        if json_content["test_status"] != "error":
                            json_content["test_status"] = "failed"

                # rule №1.2: avrg encoder * 2 < encoder -> problem with app
                avrg_encoder_value = mean(saved_values['encoder_values'])

                # catch 3 value in succession
                bad_avrg_encoder_values = []
                bad_encoder_values = []

                for encoder_value in saved_values['encoder_values']:
                    if avrg_encoder_value * 2 < encoder_value:
                        bad_avrg_encoder_values.append(avrg_encoder_value)
                        bad_encoder_values.append(encoder_value)

                    else:
                        bad_avrg_encoder_values = []
                        bad_encoder_values = []

                    if len(bad_avrg_encoder_values) >= 3:
                        formatted_avrg_encoder_values = "[{}, {}, {}]".format(round(bad_avrg_encoder_values[0], 2), round(bad_avrg_encoder_values[1], 2), round(bad_avrg_encoder_values[2], 2))
                        formatted_encoder_values = "[{}, {}, {}]".format(round(bad_encoder_values[0], 2), round(bad_encoder_values[1], 2), round(bad_encoder_values[2], 2))

                        json_content["message"].append("Application problem: At least 3 encoder values in sucession are much bigger than average encoder value. Encoder {}. Avrg encoder: {}".format(formatted_encoder_values, formatted_avrg_encoder_values))
                        if json_content["test_status"] != "error":
                            json_content["test_status"] = "failed"

                        break

        # rule №2.1: tx rate - rx rate > 8 -> problem with network
        if 'rx_rates' in saved_values and 'tx_rates' in saved_values:
            bad_rx_rate = None
            bad_tx_rate = None

            for i in range(len(saved_values['rx_rates'])):
                # find the worst value
                if saved_values['tx_rates'][i] - saved_values['rx_rates'][i] > 8:
                    if bad_rx_rate is None or (saved_values['tx_rates'][i] - saved_values['rx_rates'][i]) > (bad_tx_rate - bad_rx_rate):
                        bad_rx_rate = saved_values['rx_rates'][i]
                        bad_tx_rate = saved_values['tx_rates'][i]

            if bad_rx_rate and bad_tx_rate:
                json_content["message"].append("Network problem: TX Rate is much bigger than RX Rate. TX rate: {}. RX rate: {}".format(bad_tx_rate, bad_rx_rate))

        # rule №2.2: framerate - tx rate > 10 -> problem with app
        # ignore for Android
        if execution_type != "android":
            # Heaven can't show more than 120 fps
            if not (framerate >= 110 and (case["game_name"] == "HeavenDX9" or case["game_name"] == "HeavenDX11")):
                if 'tx_rates' in saved_values:
                    bad_tx_rate = None

                    for tx_rate in saved_values['tx_rates']:
                        # find the worst value
                        if framerate - tx_rate > 10:
                            if bad_tx_rate is None or tx_rate < bad_tx_rate:
                                bad_tx_rate = tx_rate

                    if bad_tx_rate:
                        json_content["message"].append("Application problem: TX Rate is much less than framerate. Framerate: {}. TX rate: {} fps".format(framerate, bad_tx_rate))
                        if json_content["test_status"] != "error":
                            json_content["test_status"] = "failed"


        # rule №4: encoder and decoder check. Problems with encoder -> warning. Problems with decoder -> issue with app
        # 0-0 -> skip
        # X-Y -> first time - skip. second time - problem (Y > 1, X < Y)
        # X-Y -> first time - skip. sec (X > 1, X > Y)
        # + rule №12
        if 'queue_encoder_values' in saved_values:
            # number of invalid blocks in succession
            invalid_blocks_number = 0

            for i in range(len(saved_values['queue_encoder_values'])):
                # ignore values less than 10
                if saved_values['queue_encoder_values'][i] >= 10:
                    invalid_blocks_number += 1
                else:
                    invalid_blocks_number = 0

                if invalid_blocks_number >= 3:
                    json_content["message"].append("Application problem: high encoder ({}-{}-{})".format(saved_values['queue_encoder_values'][i - 2], saved_values['queue_encoder_values'][i - 1]), saved_values['queue_encoder_values'][i])
                    
                    if json_content["test_status"] != "error":
                        json_content["test_status"] = "failed"

                    break

        if 'queue_decoder_values' in saved_values:
            # number of invalid blocks in succession
            invalid_blocks_number = 0

            for i in range(len(saved_values['queue_decoder_values'])):
                # ignore values less than 10
                if saved_values['queue_decoder_values'][i] >= 10:
                    invalid_blocks_number += 1
                else:
                    invalid_blocks_number = 0

                if invalid_blocks_number >= 3:
                    json_content["message"].append("Application problem: high encoder ({}-{}-{})".format(saved_values['queue_decoder_values'][i - 2], saved_values['queue_decoder_values'][i - 1]), saved_values['queue_decoder_values'][i])

                    break

        # rule №6.1: client latency <= decoder -> issue with app
        if 'client_latencies' in saved_values and 'decoder_values' in saved_values:
            bad_client_latency = None
            bad_decoder_value = None

            for i in range(len(saved_values['client_latencies'])):
                # find the worst value
                if saved_values['client_latencies'][i] <= saved_values['decoder_values'][i]:
                    if bad_client_latency is None or (saved_values['decoder_values'][i] - saved_values['client_latencies'][i]) > (bad_decoder_value - bad_client_latency):
                        bad_client_latency = saved_values['client_latencies'][i]
                        bad_decoder_value = saved_values['decoder_values'][i]

            if bad_client_latency and bad_decoder_value:
                json_content["message"].append("Application problem: client latency is less than decoder value. Client  {}. Decoder  {}".format(bad_client_latency, bad_decoder_value))
                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failed"

        # rule №6.2: server latency <= encoder -> issue with app
        if 'server_latencies' in saved_values and 'encoder_value' in saved_values:
            bad_server_latency = None
            bad_encoder_value = None

            for i in range(len(saved_values['server_latencies'])):
                # find the worst value
                if saved_values['server_latencies'][i] <= saved_values['encoder_value'][i]:
                    if bad_server_latency is None or (saved_values['encoder_value'][i] - saved_values['server_latencies'][i]) > (bad_encoder_value - bad_server_latency):
                        bad_server_latency = saved_values['server_latencies'][i]
                        bad_encoder_value = saved_values['encoder_value'][i]

            if bad_server_latency and bad_encoder_value:
                json_content["message"].append("Application problem: server latency is less than encoder value. Server  {}. Encoder  {}".format(bad_server_latency, bad_encoder_value))
                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failed"

        # rule №7: |decyns value| > 50ms -> issue with app
        if 'decyns_values' in saved_values:
            bad_decyns_value = None

            for decyns_value in saved_values['decyns_values']:
                # find the worst value
                if abs(decyns_value) > 50:
                    if bad_decyns_value is None or bad_decyns_value < abs(decyns_value):
                        bad_decyns_value = abs(decyns_value)

            if bad_decyns_value:
                json_content["message"].append("Application problem: Absolute value of A/V desync is more than 100 ms. A/V desync: {} ms".format(bad_decyns_value))
                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failed"

        # rule №8.1: (sum of video bitrate - sum of average bandwidth tx) / video bitrate > 0.25 or 3.0 -> issue with app
        if 'average_bandwidth_tx' in saved_values and 'video_bitrate' in saved_values:
            def check_rule_8(average_bandwidth_tx_sum, video_bitrate, block_number):
                if block_number == 0:
                    return

                average_bandwidth_tx_sum /= 1000

                average_bandwidth_tx_sum /= block_number

                difference = (average_bandwidth_tx_sum - video_bitrate) / video_bitrate

                max_difference = 0.25

                if get_codec(case["prepared_keys"]) == 'h.265':
                    max_difference = 3.0
                if video_bitrate == 1:
                    max_difference = 3.0

                if difference > max_difference:
                    json_content["message"].append("Application problem: Too high Bandwidth AVG. AVG total bandwidth for case: {}. AVG total bitrate for case: {}. Difference: {}%".format(round(average_bandwidth_tx_sum, 2), round(video_bitrate, 2), round(difference * 100, 2)))

                    if get_codec(case["prepared_keys"]) != 'h.265':
                        if json_content["test_status"] != "error":
                            json_content["test_status"] = "failed"

            average_bandwidth_tx_sum = 0
            # take the first video bitrate
            previous_video_bitrate = saved_values['video_bitrate'][0]
            # number of block in succession with the same video bitrate
            block_number = 0

            for i in range(len(saved_values['average_bandwidth_tx'])):
                if saved_values['video_bitrate'][i] != previous_video_bitrate:
                    # if QoS == false and value change - it's abnormal
                    if not get_qos_status(case["prepared_keys"]):
                        json_content["message"].append("Application problem: QoS is false, but bitrate changed from {} to {}".format(previous_video_bitrate, saved_values['video_bitrate'][i]))

                        if json_content["test_status"] != "error":
                            json_content["test_status"] = "failed"

                    if block_number >= 5:
                        check_rule_8(average_bandwidth_tx_sum, previous_video_bitrate, block_number)
                    previous_video_bitrate = saved_values['video_bitrate'][i]
                    average_bandwidth_tx_sum = 0
                    block_number = 0

                average_bandwidth_tx_sum += saved_values['average_bandwidth_tx'][i]
                block_number += 1

            check_rule_8(average_bandwidth_tx_sum, previous_video_bitrate, block_number)

        # rule №8.2: if QoS false -> all bitrates must be same
        if not get_qos_status(case["prepared_keys"]) and 'video_bitrate' in saved_values:
            video_bitrate_set = set(saved_values['video_bitrate'])
            # make symmetric difference of sets
            has_different_values = (video_bitrate_set ^ saved_values['hevc_video_bitrate']) or (saved_values['hevc_video_bitrate'] ^ saved_values['bitrate']) or (saved_values['bitrate'] ^ video_bitrate_set)

            if has_different_values:
                json_content["message"].append("Application problem: QoS is false, but some bitrate values are different")

                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failed"

        # rule №9: number of abnormal network latency values is bigger than 10% of total values -> issue with app
        # Abnormal value: avrg network latency * 2 < network latency
        if 'network_latencies' in saved_values:
            avrg_network_latency = mean(saved_values['network_latencies'])
            abnormal_values_num = 0
            total_values_num = len(saved_values['network_latencies'])

            for network_latency in saved_values['network_latencies']:
                if avrg_network_latency * 2 < network_latency:
                    abnormal_values_num += 1

            if abnormal_values_num > round(total_values_num * 0.1):
                json_content["message"].append("Network problem: Too many high values of network latency (more than 10%)")

        # rule №10: send time avg * 100 < send time worst -> issue with network
        if 'send_time_avg' in saved_values and 'send_time_worst' in saved_values:
            for i in range(len(saved_values['send_time_avg'])):
                if saved_values['send_time_avg'][i] * 100 < saved_values['send_time_worst'][i]:
                    json_content["message"].append("Network problem: worst send time is 100 times more than the avg send time. Send time (avg/worst):  {}/ {} ms".format(saved_values['send_time_avg'][i], saved_values['send_time_worst'][i]))

                    break

        # rule №11: detect error messages: VIDEO_OP_CODE_FORCE_IDR, Input Queue Full
        if 'code_force_idr' in saved_values and saved_values['code_force_idr']:
            json_content["message"].append("Application problem: VIDEO_OP_CODE_FORCE_IDR detected")
            if json_content["test_status"] != "error":
               json_content["test_status"] = "failed"

        if 'input_queue_full' in saved_values and saved_values['input_queue_full']:
            json_content["message"].append("Application problem: Input Queue Full detected")
            if json_content["test_status"] != "error":
               json_content["test_status"] = "failed"

        # rule №13: -resolution X,Y != Encode Resolution -> failed
        flag_resolution = get_resolution(case["prepared_keys"])
        if flag_resolution:
            for i in range(1, len(saved_values['encode_resolution'])):
                if not ((saved_values['encode_resolution'][i-1] == saved_values['encode_resolution'][i]) and (saved_values['encode_resolution'][i] == flag_resolution)):
                    json_content["message"].append("Application problem: Encode Resolution in Flags doesn't match to Encode Resolution from logs. Resolution from Flags: {}, from logs {}".format(flag_resolution, saved_values['encode_resolution'][i]))
                    if json_content["test_status"] != "error":
                       json_content["test_status"] = "failed"

        # rule №14: FPS > 150 -> warning
        if 'rx_rates' in saved_values:
            max_rx_rate = 0

            for i in range(len(saved_values['rx_rates'])):
                # find the worst value
                if saved_values['rx_rates'][i] > max_rx_rate:
                    max_rx_rate = saved_values['rx_rates'][i]

            if max_rx_rate > 150:
                json_content["message"].append("Application problem: too high RX Rate {}".format(max_rx_rate))

        # rule №14: FPS > 150 -> warning
        if 'rx_rates' in saved_values:
            max_rx_rate = 0

            for i in range(len(saved_values['rx_rates'])):
                # find the worst value
                if saved_values['rx_rates'][i] > max_rx_rate:
                    max_rx_rate = saved_values['rx_rates'][i]

            if max_rx_rate > 150:
                json_content["message"].append("Application problem: too high RX Rate {}".format(max_rx_rate))


    json_content["message"].extend(saved_errors)


def analyze_logs(work_dir, json_content, case, execution_type="server"):
    try:
        log_key = '{}_log'.format(execution_type)

        block_number = 0
        saved_values = {}
        results = {}
        saved_errors = []

        end_of_block = False
        connection_terminated = False

        if execution_type == "server" or execution_type == "android":
            if log_key in json_content:
                log_path = os.path.join(work_dir, json_content[log_key]).replace('/', os.path.sep).replace('\\', os.path.sep)
            else:
                log_path = os.path.join(work_dir, "tool_logs", json_content["test_case"] + "_server.log")

            if os.path.exists(log_path):
                framerate = get_framerate(case["prepared_keys"])

                with open(log_path, 'r') as log_file:
                    log = log_file.readlines()
                    for line in log:
                        if 'DEBUG ME!!! Client connection terminated' in line:
                            connection_terminated = True

                        # beginning of the new block
                        if 'Average latency' in line:
                            end_of_block = False
                            block_number += 1
                            connection_terminated = False

                        parse_line(line, saved_values)

                        # skip six first blocks of output with latency (it can contains abnormal data due to starting of Streaming SDK)
                        if block_number > 6:
                            if not end_of_block:
                                parse_block_line(line, saved_values)
                            elif line.strip():
                                #parse_error(line, saved_errors)
                                pass

                        if 'Queue depth' in line:
                            end_of_block = True

                        if 'Encode Resolution:' in line:
                            if 'encode_resolution' not in saved_values:
                                saved_values['encode_resolution'] = []
                            # Encode Resolution: 1920x1080@75fps
                            # Replace 'x' by ','
                            saved_values['encode_resolution'].append(line.split("Encode Resolution:")[1].split("@")[0].replace("x", ",").strip())

                    update_status(json_content, case, saved_values, saved_errors, framerate, execution_type)

            #if connection_terminated:
            #    json_content["message"].append("Application problem: Client connection terminated")
            #    json_content["test_status"] = "error"

            main_logger.info("Test case processed: {}".format(json_content["test_case"]))
            main_logger.info("Saved values: {}".format(saved_values))
            main_logger.info("Saved errors: {}".format(saved_errors))
        else:
            main_logger.info("Test case skipped: {}".format(json_content["test_case"]))
    except Exception as e:
        main_logger.error("Failed to analyze logs. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
