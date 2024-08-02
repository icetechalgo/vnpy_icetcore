# -*- coding: utf-8 -*-
__author__ = 'ICE Technology'

import setuptools

setuptools.setup(
    name='vnpy_icetcore',
    version="1.0.8",
    description='vnpy icetcore gateway',
    author='zxlee',
    author_email='zxlee@icetech.com.cn',
    url='https://www.algostars.com.cn/',
    packages=setuptools.find_packages(exclude=["vnpy_icetcore.sample.*"]),
    install_requires=["icetcore>=6.6.18"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    include_package_data=True
)