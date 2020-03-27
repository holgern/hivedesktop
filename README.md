# hivedesktop
[![Build status](https://ci.appveyor.com/api/projects/status/gr0cpgpsi6u97d3p?svg=true)](https://ci.appveyor.com/project/holger80/hivedesktop)
[![Build Status](https://travis-ci.org/holgern/hivedesktop.svg?branch=master)](https://travis-ci.org/holgern/hivedesktop)
A pyqt5 based desktop app for the hive blockchain

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

Activate the virtual environment
```
<path>\env\Scripts\activate
```

Install the packages:
```
pip install fbs PyQt5==5.12.3 PyInstaller==3.4 beem cryptography  python-dateutil
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