import json
import os
import sys
from time import time


def signal_handler(var1, var2):
    """ Signal handler for cloud server management (e.g. SIGTERM)."""
    # logger.info("Handled signal")
    sys.exit()


def repair_corrupt_json(file):
    """Something to do with SIGTERM handling(?) corrupts the JSON, band-aid fix below:"""
    try:
        submissions = json.load(file)
    except json.decoder.JSONDecodeError:
        # Seek to end of file for writing and back to start for reading
        file.seek(0, os.SEEK_END)
        file.write("]}")
        file.seek(0)
        submissions = json.load(file)
    return submissions


def format_elapsed_time(start_time):
    """Pretty format the elapsed time e.g. 3600 -> 01:00:00"""
    t = round(time() - start_time)
    h = t // 3600
    m = (t - (h * 3600)) // 60
    s = t - (h * 3600) - (m * 60)
    time_formatted = "{:0>2}:{:0>2}:{:0>2}".format(h, m, s)
    if h == 0:
        time_formatted = time_formatted[3:]
    return time_formatted
