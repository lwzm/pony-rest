#!/usr/bin/env python

from setuptools import setup

name = "pony-rest"
author = "lwzm"

with open("README.md") as f:
    long_description = f.read()


setup(
    name=name,
    version="1.10",
    description="Restful API generated by ponyorm and tornado",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=author,
    author_email="{}@qq.com".format(author),
    keywords="rest restful pony tornado http api".split(),
    url="https://github.com/{}/{}".format(author, name),
    py_modules=["pony_rest"],
    install_requires="pony tornado pendulum pyyaml".split(),
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
    ],
)
