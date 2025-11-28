"""
setup of the sym_phony package.

This is used to define the package creation and installation steps.

"""
from setuptools import setup, find_packages

setup(
    name="symphony",
    version="1.0.0",
    description="McKibbin Software Group Symphony Definition Language for G-Cubed models",
    author="Geoff Shuetrim",
    author_email="gshuetrim@gcubed.com",
    url="https://documentation.gcubed.com/",
    license="McKibbin Software Group :: All rights reserved",
    packages=find_packages(),
    package_data={"symphony": ["*.lark"]},
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "numpy",
        "pandas",
        "regex",
        "ordered_set",
        "lark",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: McKibbin Software Group :: All rights reserved",
        "Operating System :: OS Independent",
    ],
)
