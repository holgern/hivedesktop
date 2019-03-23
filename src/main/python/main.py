from fbs_runtime.application_context import ApplicationContext, cached_property
from PyQt5.QtCore import Qt, QSettings, QSize, QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QMenu, \
     QSystemTrayIcon, QDialog, QMainWindow, QGridLayout, QCheckBox, QSizePolicy, QSpacerItem, \
     QLineEdit, QTabWidget
from ui_mainwindow import Ui_MainWindow
from beem import Steem
from beem.comment import Comment
from beem.account import Account
from beem.amount import Amount
from beem.rc import RC
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from beem.utils import addTzInfo, resolve_authorperm, construct_authorperm, derive_permlink, formatTimeString, formatTimedelta
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

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()
        # Set up the user interface from Designer.
        self.setupUi(self)

        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_account)
        
        self.timer2 = QTimer()
        self.timer2.timeout.connect(self.update_account_hist)        
      
        # Get settings
        settings = QSettings()
        # Get checkbox state with speciying type of checkbox:
        # type=bool is a replacement of toBool() in PyQt5
        check_state = settings.value(SETTINGS_TRAY, False, type=bool)
        account_state = settings.value(SETTINGS_ACCOUNT, "holger80", type=str)
        # Set state
        self.autoRefreshCheckBox.setChecked(check_state)
        if check_state:
            self.timer.start(5000)
            self.timer2.start(30000)
        self.accountLineEdit.setText(account_state)
        # connect the slot to the signal by clicking the checkbox to save the state settings
        self.autoRefreshCheckBox.clicked.connect(self.save_check_box_settings)   
        self.accountLineEdit.editingFinished.connect(self.save_account_settings)
                
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
        self.refresh_account()
        self.update_account_hist()
        # self.button.clicked.connect(lambda: self.text.setText(_get_quote(self.hist_account, self.stm)))
        self.refreshPushButton.clicked.connect(self.refresh_account)
        self.refreshPushButton.clicked.connect(self.update_account_hist)
        self.accountLineEdit.editingFinished.connect(self.update_account_info)
        
        self.drugwarsPushButton.clicked.connect(self.read_account_hist)

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
        settings.setValue(SETTINGS_TRAY, self.autoRefreshCheckBox.isChecked())
        if self.autoRefreshCheckBox.isChecked():
            self.timer.start(5000)
            self.timer2.start(30000)
        else:
            self.timer.stop()
            self.timer2.stop()
        settings.sync()

    # Slot checkbox to save the settings
    def save_account_settings(self):
        settings = QSettings()
        settings.setValue(SETTINGS_ACCOUNT, self.accountLineEdit.text())
        settings.sync()

    def update_account_info(self):
        if self.hist_account["name"] != self.accountLineEdit.text():
            self.hist_account = Account(self.accountLineEdit.text(), steem_instance=self.stm)
            self.refresh_account()
            self.update_account_hist()

    def refresh_account(self):
        self.hist_account.refresh()
        self.accountInfoGroupBox.setTitle("%s (%.3f)" % (self.hist_account["name"], self.hist_account.rep))
        self.votePowerProgressBar.setValue(int(self.hist_account.vp))
        self.votePowerProgressBar.setFormat("%.2f %%, full in %s" % (self.hist_account.vp, self.hist_account.get_recharge_time_str()))
        rc_manabar = self.hist_account.get_rc_manabar()
        self.RCProgressBar.setValue(int(rc_manabar["current_pct"]))
        self.RCProgressBar.setFormat("%.2f %%, full in %s" % (rc_manabar["current_pct"], self.hist_account.get_manabar_recharge_time_str(rc_manabar)))
        self.votePowerLabel.setText("Vote Power, a 100%% vote is %.3f $" % (self.hist_account.get_voting_value_SBD()))
        rc = self.hist_account.get_rc()
        estimated_rc = int(rc["max_rc"]) * rc_manabar["current_pct"] / 100
        rc_calc = RC(steem_instance=self.stm)
        self.RCLabel.setText("RC (%.0f G RC of %.0f G RC)" % (estimated_rc / 10**9, int(rc["max_rc"]) / 10**9))
        self.STEEMLabel.setText(str(self.hist_account["balance"]))
        self.SBDLabel.setText(str(self.hist_account["sbd_balance"]))
        self.SPLabel.setText("%.3f SP" % self.stm.vests_to_sp(self.hist_account["vesting_shares"]))
        
        ret = "--- Approx Costs ---\n"
        ret += "comment - %.2f G RC - enough RC for %d comments\n" % (rc_calc.comment() / 10**9, int(estimated_rc / rc_calc.comment()))
        ret += "vote - %.2f G RC - enough RC for %d votes\n" % (rc_calc.vote() / 10**9, int(estimated_rc / rc_calc.vote()))
        ret += "transfer - %.2f G RC - enough RC for %d transfers\n" % (rc_calc.transfer() / 10**9, int(estimated_rc / rc_calc.transfer()))
        ret += "custom_json - %.2f G RC - enough RC for %d custom_json\n" % (rc_calc.custom_json() / 10**9, int(estimated_rc / rc_calc.custom_json()))
        self.text.setText(ret)

    def update_account_hist(self):
        b = Blockchain(steem_instance=self.stm)
        latest_block_num = b.get_current_block_num()
        start_block_num = latest_block_num - (20 * 60 * 24)
        votes = []
        self.lastUpvotesListWidget.clear()
        self.lastCurationListWidget.clear()
        self.lastAuthorListWidget.clear()
        daily_curation = 0
        daily_author_SP = 0
        daily_author_SBD = 0
        daily_author_STEEM = 0
        for op in self.hist_account.history_reverse(stop=start_block_num, only_ops=["vote", "curation_reward", "author_reward"]):
            if op["type"] == "vote":
                if op["voter"] == self.hist_account["name"]:
                    continue
                votes.append(op)
                op_timedelta = formatTimedelta(addTzInfo(datetime.utcnow()) - formatTimeString(op["timestamp"]))
                self.lastUpvotesListWidget.addItem("%s - %s (%.2f %%) upvote %s" % (op_timedelta, op["voter"], op["weight"] / 100, op["permlink"]))
            elif op["type"] == "curation_reward":
                curation_reward = self.stm.vests_to_sp(Amount(op["reward"], steem_instance=self.stm))
                daily_curation += curation_reward
                op_timedelta = formatTimedelta(addTzInfo(datetime.utcnow()) - formatTimeString(op["timestamp"]))
                self.lastCurationListWidget.addItem("%s - %.3f SP for %s" % (op_timedelta, curation_reward, construct_authorperm(op["comment_author"], op["comment_permlink"])))
            elif op["type"] == "author_reward":
                sbd_payout = (Amount(op["sbd_payout"], steem_instance=self.stm))
                steem_payout = (Amount(op["steem_payout"], steem_instance=self.stm))
                sp_payout = self.stm.vests_to_sp(Amount(op["vesting_payout"], steem_instance=self.stm))
                daily_author_SP += sp_payout
                daily_author_STEEM += float(steem_payout)
                daily_author_SBD += float(sbd_payout)
                op_timedelta = formatTimedelta(addTzInfo(datetime.utcnow()) - formatTimeString(op["timestamp"]))
                self.lastAuthorListWidget.addItem("%s - %s %s %.3f SP for %s" % (op_timedelta, str(sbd_payout), str(steem_payout), sp_payout, op["permlink"]))
        reward_text = "Curation reward (last 24 h): %.3f SP\n" % daily_curation
        reward_text += "Author reward (last 24 h):\n"
        reward_text += "%.3f SP - %.3f STEEM - %.3f SBD" % (daily_author_SP, (daily_author_STEEM), (daily_author_SBD))
        self.text2.setText(reward_text)
            
    def read_account_hist(self):
        self.tray.showMessage("Please wait", "reading account history")
        self.hist_account = Account(self.accountLineEdit.text(), steem_instance=self.stm)
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
        self.bookkeepingLabel.setText(_get_drugwars_info(transfer_hist, transfer_vest_hist, self.hist_account, self.stm))


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