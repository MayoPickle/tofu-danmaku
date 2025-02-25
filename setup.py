# setup.py
from setuptools import setup, find_packages

setup(
    name="tofu-danmaku",
    version="0.1.0",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    author="nayutaa",
    author_email="me@boyangyu.cn",
    description="handy bilibili live danmaku app",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Nayutaa/Tofu-Danmaku",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
