#!/usr/bin/env python

from distutils.core import setup

setup(
    name="netviz",
    version="0.01",
    description="Visualize NET graphs",
    author="Wouter van Atteveldt",
    author_email="wouter@vanatteveldt.com",
    packages=["netviz"],
    keywords = [],
    classifiers=[
        "License :: OSI Approved :: MIT License",
    ],
    install_requires=[
        "actionform",
    ]
)
