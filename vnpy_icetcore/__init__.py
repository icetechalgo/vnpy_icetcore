#!/usr/bin/env python
#  -*- coding: utf-8 -*-
__author__ = 'zxlee'
name = "vnpy_icetcore"
import importlib_metadata

from .icetcore_datafeed import IceTCoreDatafeed as Datafeed
from .icetcore_gateway import IceTCoreGateway


try:
    __version__ = importlib_metadata.version("vnpy_icetcore")
except importlib_metadata.PackageNotFoundError:
    __version__ = "dev"
