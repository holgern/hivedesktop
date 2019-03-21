from fbs_runtime.application_context import ApplicationContext, cached_property
from PyQt5.QtCore import Qt, QSettings, QSize, QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QMenu, \
     QSystemTrayIcon, QDialog, QMainWindow, QGridLayout, QCheckBox, QSizePolicy, QSpacerItem, \
     QLineEdit, QTabWidget
from beem import Steem
from beem.comment import Comment
from beem.account import Account
from beem.amount import Amount
from beem.nodelist import NodeList
from beem.utils import addTzInfo, resolve_authorperm, construct_authorperm, derive_permlink, formatTimeString
from datetime import datetime, timedelta
import click
import logging
import sys
import os
import io
import argparse
import re
import six

ORGANIZATION_NAME = 'holger80'
ORGANIZATION_DOMAIN = 'beempy.com'
APPLICATION_NAME = 'Steem Desktop'
SETTINGS_TRAY = 'settings/tray'
SETTINGS_ACCOUNT = 'settings/account'

class AppContext(ApplicationContext):
    def run(self):
        stylesheet = self.get_resource('styles.qss')
        self.app.setStyleSheet(open(stylesheet).read())
        self.window.show()
        return self.app.exec_()
    @cached_property
    def window(self):
        return MainWindow()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(480, 240))  # Set sizes
        self.setWindowTitle("Steem Desktop")  # Set a title
        central_widget = QWidget(self)  # Create a central widget
        self.setCentralWidget(central_widget)  # Set the central widget
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.resize(300,200)        
        # Add tabs
        self.tabs.addTab(self.tab1,"Account info")
        self.tabs.addTab(self.tab2,"bookkeeping")
        
        # Add tabs to widget
        layout.addWidget(self.tabs)
        
        gridlayout = QGridLayout()
        
        gridlayout.addWidget(QLabel("Steem account", self), 0, 0)
        self.lineEdit = QLineEdit(self)
        gridlayout.addWidget(self.lineEdit, 0, 1)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        
        # Add a checkbox, which will depend on the behavior of the program when the window is closed
        self.check_box = QCheckBox('Auto refresh')
        gridlayout.addWidget(self.check_box, 1, 0)
        gridlayout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)        
        
        
        self.text = QLabel()
        self.text.setWordWrap(True)      
        
        self.button = QPushButton('refresh account info')
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        layout.addWidget(self.button)
        layout.setAlignment(self.button, Qt.AlignHCenter)        
        
        gridlayout.addLayout(layout, 1, 1)
        self.tab1.setLayout(gridlayout)
        # Get settings
        settings = QSettings()
        # Get checkbox state with speciying type of checkbox:
        # type=bool is a replacement of toBool() in PyQt5
        check_state = settings.value(SETTINGS_TRAY, False, type=bool)
        account_state = settings.value(SETTINGS_ACCOUNT, "holger80", type=str)
        # Set state
        self.check_box.setChecked(check_state)
        if check_state:
            self.timer.start(5000)
        self.lineEdit.setText(account_state)
        # connect the slot to the signal by clicking the checkbox to save the state settings
        self.check_box.clicked.connect(self.save_check_box_settings)   
        self.lineEdit.editingFinished.connect(self.save_account_settings)
        
        gridlayout2 = QGridLayout()
        
        self.text2 = QLabel()
        self.text2.setWordWrap(True)      
        self.text2.setText("Please press the button to start!")
        self.button2 = QPushButton('Show Drugwars stats')
        layout2 = QVBoxLayout()
        layout2.addWidget(self.text2)
        layout2.addWidget(self.button2)
        layout2.setAlignment(self.button2, Qt.AlignHCenter)        
        
        gridlayout2.addLayout(layout2, 0, 0)
        self.tab2.setLayout(gridlayout2)
        
        menu = QMenu()
        aboutAction = menu.addAction("about")
        aboutAction.triggered.connect(self.about)
        exitAction = menu.addAction("exit")
        exitAction.triggered.connect(sys.exit)
        self.tray = QSystemTrayIcon()
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.setToolTip("Steem Desktop!")		
        
        account = account_state
        nodelist = NodeList()
        nodelist.update_nodes()
        self.stm = Steem(node=nodelist.get_nodes())
        self.hist_account = Account(account, steem_instance=self.stm)
        self.text.setText(self.hist_account.print_info(return_str=True))
        # self.button.clicked.connect(lambda: self.text.setText(_get_quote(self.hist_account, self.stm)))
        self.button.clicked.connect(self.refresh)
        self.lineEdit.editingFinished.connect(self.update_account_info)
        
        self.button2.clicked.connect(self.read_account_hist)

    def about(self):
        self.dialog = QDialog()
        self.dialog.setWindowTitle("About Dialog")
        gridlayout = QGridLayout()
        
        text = QLabel()
        text.setWordWrap(True)
        text.setText("Welcome to steemdesktop! This is the first release for testing qt5. Please vote for holger80 as witness, if you like this :).")
        layout = QVBoxLayout()
        layout.addWidget(text)
        
        gridlayout.addLayout(layout, 0, 0)
        self.dialog.setLayout(gridlayout)    
        self.dialog.show()

    # Slot checkbox to save the settings
    def save_check_box_settings(self):
        settings = QSettings()
        settings.setValue(SETTINGS_TRAY, self.check_box.isChecked())
        if self.check_box.isChecked():
            self.timer.start(5000)
        else:
            self.timer.stop()
        settings.sync()

    # Slot checkbox to save the settings
    def save_account_settings(self):
        settings = QSettings()
        settings.setValue(SETTINGS_ACCOUNT, self.lineEdit.text())
        settings.sync()

    def update_account_info(self):
        if self.hist_account["name"] != self.lineEdit.text():
            self.hist_account = Account(self.lineEdit.text(), steem_instance=self.stm)
            self.text.setText(self.hist_account.print_info(return_str=True))

    def refresh(self):
        self.text.setText(self.hist_account.print_info(return_str=True))

    def read_account_hist(self):
        self.tray.showMessage("Please wait", "reading account history")
        self.hist_account = Account(self.lineEdit.text(), steem_instance=self.stm)
        transfer_hist = []
        transfer_vest_hist = []
        n = 0
        for h in self.hist_account.history(only_ops=["transfer", "transfer_to_vesting"]):
            n += 1
            if h["type"] == "transfer":
                transfer_hist.append(h)
            elif h["type"] == "transfer_to_vesting":
                transfer_vest_hist.append(h)      
        self.tray.showMessage("Finished", "Read %d ops from %s" % (n, self.hist_account["name"]))
        self.text2.setText(_get_drugwars_info(transfer_hist, transfer_vest_hist, self.hist_account, self.stm))


def _get_drugwars_info(transfer_hist, transfer_vest_hist, hist_account, stm):


    included_accounts = ["drugwars", "drugwars-dealer"]
    steem_spent = 0
    steem_received = 0
    steem_heist = 0
    steem_daily = 0
    steem_referral = 0
    sbd_spent = 0
    sbd_received = 0
    nothing_found_steem = True
    nothing_found_sbd = True
    startdate = None
    steem_received_5_days = 0
    
    for h in transfer_hist:
        age_days = (addTzInfo(datetime.utcnow()) - formatTimeString(h["timestamp"])).total_seconds() / 60 / 60 / 24
        if h["from"] in included_accounts and ("daily" in h["memo"].lower() or "drug production" in h["memo"].lower()):
            amount = Amount(h["amount"], steem_instance=stm)
            
            if startdate is None:
                startdate = formatTimeString(h["timestamp"])                            
            if amount.symbol == "STEEM":
                nothing_found_steem = False
                steem_daily += float(amount)
                if age_days <= 5:
                    steem_received_5_days += float(amount)
            elif amount.symbol == "SBD":
                nothing_found_sbd = False
                sbd_received += float(amount)
        elif h["from"] in included_accounts and "heist" in h["memo"].lower():
            amount = Amount(h["amount"], steem_instance=stm)
            if startdate is None:
                startdate = formatTimeString(h["timestamp"])            
            if amount.symbol == "STEEM":
                nothing_found_steem = False
                steem_heist += float(amount)
                if age_days <= 5:
                    steem_received_5_days += float(amount)                                
            elif amount.symbol == "SBD":
                nothing_found_sbd = False
                sbd_received += float(amount)
        elif h["from"] in included_accounts and "referral" in h["memo"].lower():
            amount = Amount(h["amount"], steem_instance=stm)
            if startdate is None:
                startdate = formatTimeString(h["timestamp"])                            
            if amount.symbol == "STEEM":
                nothing_found_steem = False
                steem_referral += float(amount)
                if age_days <= 5:
                    steem_received_5_days += float(amount)                                
            elif amount.symbol == "SBD":
                nothing_found_sbd = False
                sbd_received += float(amount)                          
        elif h["from"] in included_accounts:
            amount = Amount(h["amount"], steem_instance=stm)
            if startdate is None:
                startdate = formatTimeString(h["timestamp"])                            
            if amount.symbol == "STEEM":
                nothing_found_steem = False
                steem_received += float(amount)
                if age_days <= 5:
                    steem_received_5_days += float(amount)                                
            elif amount.symbol == "SBD":
                nothing_found_sbd = False
                sbd_received += float(amount)
        elif h["to"] in included_accounts:
            amount = Amount(h["amount"], steem_instance=stm)
            if startdate is None:
                startdate = formatTimeString(h["timestamp"])                            
            if amount.symbol == "STEEM":
                nothing_found_steem = False
                steem_spent += float(amount)
            elif amount.symbol == "SBD":
                nothing_found_sbd = False
                sbd_spent += float(amount)

    reply_body = "drugwars\n"
    if nothing_found_steem:
        reply_body += "* No related STEEM transfer were found.\n"
    else:
        duration = (addTzInfo(datetime.utcnow()) - startdate).total_seconds()
        duration_days = duration / 60 / 60 / 24                          
        reply_body += "Received:\n"
        if steem_received > 0:
            reply_body += "* %.3f STEEM\n" % (steem_received)
        reply_body += "* %.3f STEEM from daily\n" % (steem_daily)
        reply_body += "* %.3f STEEM from heist\n" % (steem_heist)
        reply_body += "* %.3f STEEM from referral\n" % (steem_referral)
        reply_body += "Spent:\n"
        reply_body += "* %.3f STEEM\n" % (steem_spent)
        reply_body += "Total:\n"
        reply_body += "* %.3f STEEM\n\n" % (steem_received-steem_spent + steem_daily + steem_heist + steem_referral)
        reply_body += "First transfer was before %.2f days.\n" % duration_days
        total = steem_received-steem_spent + steem_daily + steem_heist + steem_referral
        steem_per_day = ((steem_received + steem_daily + steem_heist + steem_referral) / duration_days)
        if steem_spent > 0:
            reply_body += "Your ROI per day is %.2f %% and you are earning approx. %.2f STEEM per day.\n" % ((steem_per_day / steem_spent * 100), steem_per_day)
        if total < 0 and steem_per_day > 0 and steem_spent > 0:
            reply_body += "Break even in approx. %.1f days.\n" % abs(total / steem_per_day)
        if duration_days > 5:
            steem_per_day_5_days = steem_received_5_days / 5
            if steem_spent > 0:
                reply_body += "ROI when taking only the last 5 days into account\n"
                reply_body += "Your ROI per day is %.2f %% and you are earning approx. %.2f STEEM per day.\n" % ((steem_per_day_5_days / steem_spent * 100), steem_per_day_5_days)
            if total < 0 and steem_per_day > 0 and steem_spent > 0:
                reply_body += "Break even in approx. %.1f days.\n" % abs(total / steem_per_day_5_days)    

    return reply_body

if __name__ == '__main__':
    # To ensure that every time you call QSettings not enter the data of your application, 
    # which will be the settings, you can set them globally for all applications
    QCoreApplication.setApplicationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(APPLICATION_NAME)    
    
    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)