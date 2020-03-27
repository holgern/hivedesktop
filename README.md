# hivedesktop
[![Build status](https://ci.appveyor.com/api/projects/status/gr0cpgpsi6u97d3p?svg=true)](https://ci.appveyor.com/project/holger80/hivedesktop)
[![Build Status](https://travis-ci.org/holgern/steemhive.svg?branch=master)](https://travis-ci.org/holgern/steemdesktop)

A pyqt5 based desktop app for the steem blockchain

## Setup 
Install python 3.6
Upgrade pip and install virtualenv (replace python by python3 or python.exe, depending on the installation and the system)
```
python -m pip install pip --upgrade
python -m pip install virtualenv
```

Create a virtual environment:
```
python -m virtualenv env
```

Install the packages:
```
pip install fbs PyQt5==5.12.3 PyInstaller==3.6 beem cryptography
```

For windows
```
pip install pywin32
```
is necessary

## Run the app
```
fbs run
```

## Freezing the app
```
fbs freeze
```
## Build an installer
```
fbs installer
```