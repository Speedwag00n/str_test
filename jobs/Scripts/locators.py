class FSServerLocators:
    TAB_TEMPLATE = '//*[@id="tabs"]//b[text() = "<tab_name>"]'
    BOOLEAN_OPTION_TEMPLATE = '//*[@id="settings"]//h3[text() = "<option_name>"]/following-sibling::input'
    SELECT_OPTION_TEMPLATE = '//*[@id="settings"]//h3[text() = "<option_name>"]/following-sibling::select'
    INPUT_OPTION_TEMPLATE = '//*[@id="settings"]//h3[text() = "<option_name>"]/following-sibling::input'
    INPUT_OPTION_TEMPLATE_FIRST = '//*[@id="settings"]//h3[text() = "<option_name>"]/following-sibling::div/input[1]'
    INPUT_OPTION_TEMPLATE_SECOND = '//*[@id="settings"]//h3[text() = "<option_name>"]/following-sibling::div/input[2]'
    APPLY_BUTTON = '//img[contains(@src, "apply")]'
