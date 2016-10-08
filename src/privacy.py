#!usr/bin/env
# -*- coding: utf-8 -*-

import re

def hide_address(place):
    if place is None:
        return None
    return re.sub('\d+', '***', place)
    