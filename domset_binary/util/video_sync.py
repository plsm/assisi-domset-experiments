import time

import assisipy.casu

__NUMBER_FLASHES = 5
__FLASH_LENGTH = 1
LENGTH = (2 * __NUMBER_FLASHES - 1) * __FLASH_LENGTH

def flash_casu (casu):
    """
    Flash the CASU led to allow synchronisation between video data and CASU logs.
    :type casu: assisipy.casu.Casu
    """
    for _ in range (__NUMBER_FLASHES - 1):
        casu.set_diagnostic_led_rgb (r = 1)
        time.sleep (__FLASH_LENGTH)
        casu.diagnostic_led_standby ()
        time.sleep (__FLASH_LENGTH)
    casu.set_diagnostic_led_rgb (r = 1)
    time.sleep (__FLASH_LENGTH)
    casu.diagnostic_led_standby ()
