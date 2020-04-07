from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property
from PyQt5.QtCore import Qt, QSettings, QSize, QCoreApplication, QTimer, QRunnable, pyqtSlot, QThreadPool, \
     QStandardPaths
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QMenu, \
     QSystemTrayIcon, QDialog, QMainWindow, QGridLayout, QCheckBox, QSizePolicy, QSpacerItem, \
     QLineEdit, QTabWidget, QSplashScreen, QMessageBox, QAction
from ui_mainwindow import Ui_MainWindow
import hivedesktop_rc
from threading import Lock
from beem import Steem
from beem.comment import Comment
from beem.account import Account
from beem.amount import Amount
from beem.rc import RC
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from beem.utils import addTzInfo, resolve_authorperm, construct_authorperm, derive_permlink, formatTimeString, formatTimedelta
from datetime import datetime, timedelta
from dateutil import tz
import click
import logging
import sys
import os
import io
import argparse
import re
import six
import fix_qt_import_error
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

ORGANIZATION_NAME = 'holger80'
ORGANIZATION_DOMAIN = 'beempy.com'
APPLICATION_NAME = 'Hive Desktop'
SETTINGS_TRAY = 'settings/tray'
SETTINGS_HIST_INFO = 'settings/hist_info'
SETTINGS_ACCOUNT = 'settings/account'


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        self.fn(*self.args, **self.kwargs)


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

        self.redrawLock = Lock()
		
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_account_thread)
        
        self.timer2 = QTimer()
        self.timer2.timeout.connect(self.update_account_hist_thread)

        self.timer3 = QTimer()
        self.timer3.timeout.connect(self.update_account_feed_thread)
        
        self.cache_path = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
      
        # Get settings
        settings = QSettings()
        # Get checkbox state with speciying type of checkbox:
        # type=bool is a replacement of toBool() in PyQt5
        check_state = settings.value(SETTINGS_TRAY, True, type=bool)
        hist_info_check_state = settings.value(SETTINGS_HIST_INFO, True, type=bool)
        account_state = settings.value(SETTINGS_ACCOUNT, "", type=str)
        # Set state
        self.accountHistNotificationCheckBox.setChecked(hist_info_check_state)
        self.autoRefreshCheckBox.setChecked(check_state)
        if check_state:
            self.timer.start(5000)
            self.timer2.start(15000)
        self.accountLineEdit.setText(account_state)
        # connect the slot to the signal by clicking the checkbox to save the state settings
        self.autoRefreshCheckBox.clicked.connect(self.save_check_box_settings)   
        self.accountHistNotificationCheckBox.clicked.connect(self.save_check_box_settings)  
        self.accountLineEdit.editingFinished.connect(self.save_account_settings)
        self.actionAbout.triggered.connect(self.about)
        self.threadpool = QThreadPool()
        
        self.minimizeAction = QAction("Mi&nimize", self, triggered=self.hide)
        self.maximizeAction = QAction("Ma&ximize", self,
                triggered=self.showMaximized)
        self.restoreAction = QAction("&Restore", self,
                triggered=self.showNormal)        
        
        menu = QMenu()
        menu.addAction(self.minimizeAction)
        menu.addAction(self.maximizeAction)
        menu.addAction(self.restoreAction)
        menu.addSeparator()        
        # aboutAction = menu.addAction("about")
        # aboutAction.triggered.connect(self.about)
        exitAction = menu.addAction("exit")
        exitAction.triggered.connect(sys.exit)
        self.tray = QSystemTrayIcon(QIcon(':/icons/icon.ico'))
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.setToolTip("Hive Desktop!")
        splash_pix = QPixmap(':/icons/splash.png')
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        splash.setEnabled(False)
        
        splash.show()
        splash.showMessage("<h1><font color='green'>starting...</font></h1>", Qt.AlignTop | Qt.AlignCenter, Qt.black)        
        
        account = account_state
        nodelist = NodeList()
        nodelist.update_nodes()
        self.stm = Steem(node=nodelist.get_nodes(hive=True))
        if account != "":
            try:
                self.hist_account = Account(account, steem_instance=self.stm)
            except:
                self.hist_account = None
        else:
            self.hist_account = None
        if self.hasFocus is not None:
            self.init_new_account()
        # self.button.clicked.connect(lambda: self.text.setText(_get_quote(self.hist_account, self.stm)))
        self.refreshPushButton.clicked.connect(self.refresh_account_thread)
        self.refreshPushButton.clicked.connect(self.update_account_hist_thread)
        self.accountLineEdit.editingFinished.connect(self.update_account_info)

    def closeEvent(self, event):
        if self.tray.isVisible():
            QMessageBox.information(self, "Hive Desktop",
                    "The program will keep running in the system tray. To "
                    "terminate the program, choose <b>Quit</b> in the "
                    "context menu of the system tray entry.")
            self.hide()
            event.ignore()

    def about(self):
        self.dialog = QDialog()
        self.dialog.setWindowTitle("About Dialog")
        gridlayout = QGridLayout()
        
        text = QLabel()
        text.setWordWrap(True)
        text.setText("Welcome to Hive desktop! This is the first release for testing qt5. Please vote for holger80 as witness, if you like this :).")
        layout = QVBoxLayout()
        layout.addWidget(text)
        
        gridlayout.addLayout(layout, 0, 0)
        self.dialog.setLayout(gridlayout)    
        self.dialog.show()

    # Slot checkbox to save the settings
    def save_check_box_settings(self):
        settings = QSettings()
        settings.setValue(SETTINGS_HIST_INFO, self.accountHistNotificationCheckBox.isChecked())
        settings.setValue(SETTINGS_TRAY, self.autoRefreshCheckBox.isChecked())
        if self.autoRefreshCheckBox.isChecked():
            self.timer.start(5000)
            self.timer2.start(15000)
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
        if self.hist_account is None or self.hist_account["name"] != self.accountLineEdit.text():
            try:
                self.hist_account = Account(self.accountLineEdit.text(), steem_instance=self.stm)
            except:
                self.hist_account = None
            self.init_new_account()

    def init_new_account(self):
        self.refresh_account()
        self.init_account_hist()
        self.update_account_hist()


    def refresh_account_thread(self):
        worker = Worker(self.refresh_account)
        self.threadpool.start(worker)        

    def refresh_account(self):
        if self.hist_account is None:
            return
        self.hist_account.refresh()
        self.accountInfoGroupBox.setTitle("%s (%.3f)" % (self.hist_account["name"], self.hist_account.rep))
        with self.redrawLock:
            self.votePowerProgressBar.setValue(int(self.hist_account.vp))
            if self.hist_account.vp == 100:
                self.votePowerProgressBar.setFormat("%.2f %%" % (self.hist_account.vp))
            else:
                self.votePowerProgressBar.setFormat("%.2f %%, full in %s" % (self.hist_account.vp, self.hist_account.get_recharge_time_str()))
        down_vp = self.hist_account.get_downvoting_power()
        with self.redrawLock:
            self.downvotePowerProgressBar.setValue(int(down_vp))
            if down_vp == 100:
                self.downvotePowerProgressBar.setFormat("%.2f %%" % (down_vp))
            else:
                self.downvotePowerProgressBar.setFormat("%.2f %%, full in %s" % (down_vp, self.hist_account.get_recharge_time(starting_voting_power=down_vp)))
        
        self.votePowerLabel.setText("Vote Power, a 100%% vote is %.3f $" % (self.hist_account.get_voting_value_SBD()))
        self.downvotePowerLabel.setText("DownVote Power")
        self.STEEMLabel.setText(str(self.hist_account["balance"]))
        self.SBDLabel.setText(str(self.hist_account["sbd_balance"]))
        self.SPLabel.setText("%.3f HP" % self.stm.vests_to_sp(self.hist_account["vesting_shares"]))
        try:
            rc_manabar = self.hist_account.get_rc_manabar()
            with self.redrawLock:
                self.RCProgressBar.setValue(int(rc_manabar["current_pct"]))
                self.RCProgressBar.setFormat("%.2f %%, full in %s" % (rc_manabar["current_pct"], self.hist_account.get_manabar_recharge_time_str(rc_manabar)))
        
            rc = self.hist_account.get_rc()
            estimated_rc = int(rc["max_rc"]) * rc_manabar["current_pct"] / 100
            rc_calc = RC(steem_instance=self.stm)
            self.RCLabel.setText("RC (%.0f G RC of %.0f G RC)" % (estimated_rc / 10**9, int(rc["max_rc"]) / 10**9))
            ret = "--- Approx Costs ---\n"
            ret += "comment - %.2f G RC - enough RC for %d comments\n" % (rc_calc.comment() / 10**9, int(estimated_rc / rc_calc.comment()))
            ret += "vote - %.2f G RC - enough RC for %d votes\n" % (rc_calc.vote() / 10**9, int(estimated_rc / rc_calc.vote()))
            ret += "transfer - %.2f G RC - enough RC for %d transfers\n" % (rc_calc.transfer() / 10**9, int(estimated_rc / rc_calc.transfer()))
            ret += "custom_json - %.2f G RC - enough RC for %d custom_json\n" % (rc_calc.custom_json() / 10**9, int(estimated_rc / rc_calc.custom_json()))
            self.text.setText(ret)
        except:
            rc_manabar = None

    def init_account_hist(self):
        if self.hist_account is None:
            return
        b = Blockchain(steem_instance=self.stm)
        latest_block_num = b.get_current_block_num()
        start_block_num = latest_block_num - (20 * 60 * 24)
        self.account_history = []
        self.account_hist_info = {"start_block": 0, "trx_ids": []}
        self.append_hist_info = {"start_block": 0, "trx_ids": []}
        self.lastUpvotesListWidget.clear()
        self.lastCurationListWidget.clear()
        self.lastAuthorListWidget.clear()
        self.accountHistListWidget.clear()
        start_block = 0
        trx_ids = []
        for op in self.hist_account.history(start=start_block_num):
            if op["block"] < start_block:
                continue
            elif op["block"] == start_block:
                if op["trx_id"] in trx_ids:
                    continue
                else:
                    trx_ids.append(op["trx_id"])
            else:
                trx_ids = [op["trx_id"]]
            start_block = op["block"]
            self.account_history.append(op)
        self.append_hist_info["start_block"] = start_block
        self.append_hist_info["trx_ids"] = trx_ids
        
        
    def append_account_hist(self):
        if self.hist_account is None:
            return        
        start_block = self.append_hist_info["start_block"]
        trx_ids = self.append_hist_info["trx_ids"]
        for op in self.hist_account.history(start=start_block - 20, use_block_num=True):
            if op["block"] < start_block:
                continue
            elif op["block"] == start_block:
                if op["trx_id"] in trx_ids:
                    continue
                else:
                    trx_ids.append(op["trx_id"])
            else:
                trx_ids = [op["trx_id"]]

            start_block = op["block"]
            # print("Write %d" % op["index"])
            self.account_history.append(op)        
        self.append_hist_info["start_block"] = start_block
        self.append_hist_info["trx_ids"] = trx_ids

    def update_account_hist_thread(self):
        worker = Worker(self.update_account_hist)
        self.threadpool.start(worker)

    def update_account_hist(self):
        if self.hist_account is None:
            return        
        votes = []
        daily_curation = 0
        daily_author_SP = 0
        daily_author_SBD = 0
        daily_author_STEEM = 0
        self.append_account_hist()
        
        new_op_found = False
        
        start_block = self.account_hist_info["start_block"]
        if start_block == 0:
            first_call = True
        else:
            first_call = False
        trx_ids = self.account_hist_info["trx_ids"]
     
        for op in self.account_history:
            if op["block"] < start_block:
                # last_block = op["block"]
                continue
            elif op["block"] == start_block:
                if op["trx_id"] in trx_ids:
                    continue
                else:
                    trx_ids.append(op["trx_id"])
            else:
                trx_ids = [op["trx_id"]]
            start_block = op["block"]
            new_op_found = True
            op_timedelta = formatTimedelta(addTzInfo(datetime.utcnow()) - formatTimeString(op["timestamp"]))
            op_local_time = formatTimeString(op["timestamp"]).astimezone(tz.tzlocal())
            # print("Read %d" % op["index"])
            if op["type"] == "vote":
                if op["voter"] == self.hist_account["name"]:
                    continue
                self.lastUpvotesListWidget.insertItem(0,"%s - %s (%.2f %%) upvote %s" % (op_timedelta, op["voter"], op["weight"] / 100, op["permlink"]))
                hist_item = "%s - %s - %s (%.2f %%) upvote %s" % (op_local_time, op["type"], op["voter"], op["weight"] / 100, op["permlink"])
                self.accountHistListWidget.insertItem(0, hist_item)
            elif op["type"] == "curation_reward":
                curation_reward = self.stm.vests_to_sp(Amount(op["reward"], steem_instance=self.stm))
                self.lastCurationListWidget.insertItem(0, "%s - %.3f HP for %s" % (op_timedelta, curation_reward, construct_authorperm(op["comment_author"], op["comment_permlink"])))
                hist_item = "%s - %s - %.3f HP for %s" % (op_local_time, op["type"], curation_reward, construct_authorperm(op["comment_author"], op["comment_permlink"]))
                self.accountHistListWidget.insertItem(0, hist_item)
            elif op["type"] == "author_reward":
                sbd_payout = (Amount(op["sbd_payout"], steem_instance=self.stm))
                steem_payout = (Amount(op["steem_payout"], steem_instance=self.stm))
                sp_payout = self.stm.vests_to_sp(Amount(op["vesting_payout"], steem_instance=self.stm))
                self.lastAuthorListWidget.insertItem(0, "%s - %s %s %.3f HP for %s" % (op_timedelta, str(sbd_payout), str(steem_payout), sp_payout, op["permlink"]))
                hist_item = "%s - %s - %s %s %.3f SP for %s" % (op_local_time, op["type"], str(sbd_payout), str(steem_payout), sp_payout, op["permlink"])
                self.accountHistListWidget.insertItem(0, hist_item)
            elif op["type"] == "custom_json":
                hist_item = "%s - %s - %s" % (op_local_time, op["type"], op["id"])
                self.accountHistListWidget.insertItem(0, hist_item)
            elif op["type"] == "transfer":
                hist_item = "%s - %s - %s from %s" % (op_local_time, op["type"], str(Amount(op["amount"], steem_instance=self.stm)), op["from"])
                self.accountHistListWidget.insertItem(0, hist_item)
            elif op["type"] == "comment":
                comment_type = "post"
                if op["parent_author"] != "":
                    hist_item = "%s - comment on %s - %s from %s" % (op_local_time, construct_authorperm(op["parent_author"], op["parent_permlink"]), op["title"], op["author"])
                else:
                    hist_item = "%s - post - %s from %s" % (op_local_time, op["title"], op["author"])
                self.accountHistListWidget.insertItem(0, hist_item)
            else:
                hist_item = "%s - %s" % (op_local_time, op["type"])
                self.accountHistListWidget.insertItem(0, hist_item)
            
            if self.accountHistNotificationCheckBox.isChecked() and not first_call:
                self.tray.showMessage(self.hist_account["name"], hist_item)

        if new_op_found:
            self.account_hist_info["start_block"] = start_block
            self.account_hist_info["trx_ids"] = trx_ids
            
            for op in self.account_history:
                if op["type"] == "vote":
                    if op["voter"] == self.hist_account["name"]:
                        continue
                    votes.append(op)
                elif op["type"] == "curation_reward":
                    curation_reward = self.stm.vests_to_sp(Amount(op["reward"], steem_instance=self.stm))
                    daily_curation += curation_reward
                elif op["type"] == "author_reward":
                    sbd_payout = (Amount(op["sbd_payout"], steem_instance=self.stm))
                    steem_payout = (Amount(op["steem_payout"], steem_instance=self.stm))
                    sp_payout = self.stm.vests_to_sp(Amount(op["vesting_payout"], steem_instance=self.stm))
                    daily_author_SP += sp_payout
                    daily_author_STEEM += float(steem_payout)
                    daily_author_SBD += float(sbd_payout)        
        
            
            reward_text = "Curation reward (last 24 h): %.3f SP\n" % daily_curation
            reward_text += "Author reward (last 24 h):\n"
            reward_text += "%.3f HP - %.3f HIVE - %.3f HBD" % (daily_author_SP, (daily_author_STEEM), (daily_author_SBD))
            self.text2.setText(reward_text)
  

if __name__ == '__main__':
    # To ensure that every time you call QSettings not enter the data of your application, 
    # which will be the settings, you can set them globally for all applications
    QCoreApplication.setApplicationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(APPLICATION_NAME)    
    
    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)