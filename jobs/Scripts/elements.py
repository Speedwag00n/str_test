import os


class ElementLocation:
    def __init__(self, location, element_name):
        self.location = location
        self.element_name = element_name

    def build_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Elements", self.location, self.element_name) + ".png")


class GameElementLocation(ElementLocation):
    def __init__(self, game_name, element_name):
        super().__init__(os.path.join("Games", game_name), element_name)


class CSGOElementLocation(GameElementLocation):
    def __init__(self, element_name):
        super().__init__("CSGO", element_name)


class CSGOElements:
    PLAY_BUTTON = CSGOElementLocation("play_button")
    MODE_SELECTION = CSGOElementLocation("mode_selection")
    WORKSHOP_MAPS = CSGOElementLocation("workshop_maps")
    TRAINING_MAP = CSGOElementLocation("training_map")
    SELECT_MAP_BUTTON = CSGOElementLocation("select_map_button")
    GO_BUTTON = CSGOElementLocation("go_button")


class PUBGElementLocation(GameElementLocation):
    def __init__(self, element_name):
        super().__init__("PUBG", element_name)


class PUBGElements:
    CONFIRM_EXIT_TO_LOBBY = PUBGElementLocation("confirm_exit_to_lobby")
    EXIT_TO_LOBBY = PUBGElementLocation("exit_to_lobby")
    PLAY_BUTTON = PUBGElementLocation("play_button")
    RIGHT_ARROW = PUBGElementLocation("right_arrow")


class Dota2ElementLocation(GameElementLocation):
    def __init__(self, element_name):
        super().__init__("Dota2", element_name)


class Dota2Elements:
    ARCADE = Dota2ElementLocation("arcade")
    DEMO_HERO = Dota2ElementLocation("demo_hero")
    EXIT_BUTTON = Dota2ElementLocation("exit_button")
    FREE_SPELLS = Dota2ElementLocation("free_spells")
    HEROES = Dota2ElementLocation("heroes")
    LVL_MAX = Dota2ElementLocation("lvl_max")
    RENDER_API_SELECTION = Dota2ElementLocation("render_api_selection")
    RENDER_API_DX11_OPTION = Dota2ElementLocation("rendering_api_dx11_option")
    RENDER_API_VULKAN_OPTION = Dota2ElementLocation("rendering_api_vulkan_option")
    SETTINGS_BUTTON = Dota2ElementLocation("settings_button")
    VIDEO_TAB = Dota2ElementLocation("video_tab")
    YES_BUTTON = Dota2ElementLocation("yes_button")


class HeavenElementLocation(GameElementLocation):
    def __init__(self, element_name):
        super().__init__("Heaven", element_name)



class HeavenElements:
    API_LABEL = HeavenElementLocation("api_label")
    RUN_BUTTON = HeavenElementLocation("run_button")
    RUN_BUTTON_UBUNTU = HeavenElementLocation("run_button_ubuntu")
    FULL_SCREEN = HeavenElementLocation("full_screen")
    WINDOWED = HeavenElementLocation("windowed")


class LoLElementLocation(GameElementLocation):
    def __init__(self, element_name):
        super().__init__("LoL", element_name)


class LoLElements:
    CONFIRM_BUTTON = LoLElementLocation("confirm_button")
    LOCK_IN_BUTTON = LoLElementLocation("lock_in_button")
    MALPHITE_ICON = LoLElementLocation("malphite_icon")
    PLAY_BUTTON = LoLElementLocation("play_button")
    PRACTICE_TOOL = LoLElementLocation("practice_tool")
    START_GAME = LoLElementLocation("start_game")
    START_GAME_ACTIVE = LoLElementLocation("start_game_active")
    TRAINING_BUTTON = LoLElementLocation("training_button")


class ValleyElementLocation(GameElementLocation):
    def __init__(self, element_name):
        super().__init__("Valley", element_name)


class ValleyElements:
    API_LABEL = ValleyElementLocation("api_label")
    RUN_BUTTON = ValleyElementLocation("run_button")
    RUN_BUTTON_UBUNTU = ValleyElementLocation("run_button_ubuntu")
    FULL_SCREEN = ValleyElementLocation("full_screen")
    WINDOWED = ValleyElementLocation("windowed")


class IconElementLocation(ElementLocation):
    def __init__(self, element_name):
        super().__init__("Icons", element_name)


class IconElements:
    CSGO = IconElementLocation("CSGO")
    DOTA2 = IconElementLocation("Dota2")
    HEAVEN = IconElementLocation("Heaven")
    LATENCY_TOOL = IconElementLocation("LatencyTool")
    LOL = IconElementLocation("LoL")
    VALLEY = IconElementLocation("Valley")
    VALORANT = IconElementLocation("Valorant")
    ADRENALIN_ICON = IconElementLocation("Adrenalin")


class AMDLinkElementLocation(ElementLocation):
    def __init__(self, element_name):
        super().__init__("AMDLink", element_name)


class AMDLinkElements:
    RESOLUTION_2K = AMDLinkElementLocation("2k")
    RESOLUTION_4K = AMDLinkElementLocation("4k")
    RESOLUTION_480P = AMDLinkElementLocation("480p")
    RESOLUTION_720P = AMDLinkElementLocation("720p")
    RESOLUTION_1080P = AMDLinkElementLocation("1080p")
    ACCEPT_ALL_CONNECTIONS = AMDLinkElementLocation("accept_all_connections")
    ADRENALIN_ICON = AMDLinkElementLocation("adrenalin_icon")
    AMD_LINK_ICON = AMDLinkElementLocation("amd_link_icon")
    AMD_LINK_SERVER = AMDLinkElementLocation("amd_link_server")
    AMD_LINK_STATUS = AMDLinkElementLocation("amd_link_status")
    APPLY_FULL_SCREEN = AMDLinkElementLocation("apply_full_screen")
    AVC = AMDLinkElementLocation("avc")
    CLOSE_INVITE_CODE_WINDOW = AMDLinkElementLocation("close_invite_code_window")
    CONNECT_TO_PC = AMDLinkElementLocation("connect_to_pc")
    COPY_TEXT = AMDLinkElementLocation("copy_text")
    DISABLED = AMDLinkElementLocation("disabled")
    DISCONNECT_BUTTON = AMDLinkElementLocation("disconnect_button")
    ENABLE_AMD_LINK = AMDLinkElementLocation("enable_amd_link")
    ENABLED = AMDLinkElementLocation("enabled")
    FULL_ACCESS = AMDLinkElementLocation("full_access")
    FULL_ACCESS_FRESH_LINK = AMDLinkElementLocation("full_access_fresh_link")
    HEVC = AMDLinkElementLocation("hevc")
    HOME_ACTIVE = AMDLinkElementLocation("home_active")
    HOME_INACTIVE = AMDLinkElementLocation("home_inactive")
    AMD_LINK_ACTIVE = AMDLinkElementLocation("amd_link_active")
    LINK_GAME_INVITE_CLIENT = AMDLinkElementLocation("link_game_invite_client")
    LINK_GAME_INVITE_SERVER = AMDLinkElementLocation("link_game_invite_server")
    MULTI_PLAY = AMDLinkElementLocation("multi_play")
    MULTI_PLAY_FRESH_LINK = AMDLinkElementLocation("multi_play_fresh_link")
    PC_ICON = AMDLinkElementLocation("pc_icon")
    SKIP_OPTIMIZATION = AMDLinkElementLocation("skip_optimization")
    START_STREAMING = AMDLinkElementLocation("start_streaming")
    START_STREAMING_2 = AMDLinkElementLocation("start_streaming_2")
    START_STREAMING_BUTTON = AMDLinkElementLocation("start_streaming_button")
    STOP_STREAMING_BUTTON = AMDLinkElementLocation("stop_streaming_button")
    STREAM_RESOLUTION = AMDLinkElementLocation("stream_resolution")
    SUBMIT_CONNECT = AMDLinkElementLocation("submit_connect")
    SUBMIT_CONNECT_DISABLED = AMDLinkElementLocation("submit_connect_disabled")
    USE_ENCRYPTION = AMDLinkElementLocation("use_encryption")
    VIDEO_ENCODING_TYPE = AMDLinkElementLocation("video_encoding_type")
    LOBBY_ICON = AMDLinkElementLocation("lobby_icon")
    LOBBY_ICON_2 = AMDLinkElementLocation("lobby_icon_2")

    DROPDOWN_OPTIONS_LABELS = {
        "resolution": STREAM_RESOLUTION,
        "encoding_type": VIDEO_ENCODING_TYPE,
        "accept_all_connections": ACCEPT_ALL_CONNECTIONS,
        "use_encryption": USE_ENCRYPTION
    }

    DROPDOWN_OPTIONS_VALUES = {
        "resolution": {
            "2k": RESOLUTION_2K,
            "4k": RESOLUTION_4K,
            "480p": RESOLUTION_480P,
            "720p": RESOLUTION_720P,
            "1080p": RESOLUTION_1080P
        },

        "encoding_type": {
            "avc": AVC,
            "hevc": HEVC
        }
    }


class FSElementLocation(ElementLocation):
    def __init__(self, element_name):
        super().__init__("FullSamples", element_name)


class FSElements:
    CONNECT = FSElementLocation("connect")
    CONNECT_TO = FSElementLocation("connect_to")
