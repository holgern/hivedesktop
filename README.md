# steemdesktop
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
pip install fbs PyQt5==5.9.2 PyInstaller==3.4 beem cryptography
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