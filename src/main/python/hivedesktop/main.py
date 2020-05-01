from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property
from PyQt5.QtCore import Qt, QSettings, QSize, QCoreApplication, QTimer, QRunnable, pyqtSlot, QThreadPool, \
     QStandardPaths, QFile, QTextStream, QPoint, QEvent
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QMenu, \
     QSystemTrayIcon, QDialog, QMainWindow, QGridLayout, QCheckBox, QSizePolicy, QSpacerItem, \
     QLineEdit, QTabWidget, QSplashScreen, QMessageBox, QAction, QListWidgetItem, QTreeWidgetItem, QTableWidgetItem
from hivedesktop.ui_mainwindow import Ui_MainWindow
from hivedesktop import hivedesktop_rc
from hivedesktop import VERSION
from threading import Lock
from beem import Steem
from beem.comment import Comment
from beem.account import Account
from beem.amount import Amount
from beem.rc import RC
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from beem.instance import set_shared_blockchain_instance
from beem.vote import Vote
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
from hivedesktop import fix_qt_import_error
from hivedesktop import dialogs
from hivedesktop import threads
from hivedesktop import widgets
from hivedesktop.mdrenderer import MDRenderer
from hivedesktop import helpers
from hivedesktop import database
from hivedesktop import database_blocks
import qdarkstyle
import qdarkgraystyle
import breeze_resources

ORGANIZATION_NAME = 'holger80'
APPLICATION_NAME = 'Hive Desktop'
SETTINGS_TRAY = 'settings/tray'
SETTINGS_HIST_INFO = 'settings/hist_info'
SETTINGS_ACCOUNT = 'settings/account'
SETTINGS_SIZE = 'settings/size'
SETTINGS_POS = 'settings/pos'
SETTINGS_STYLE = 'settings/style'

# Setup logging
level = logging.WARNING
log = logging.getLogger(APPLICATION_NAME)
log.setLevel(level)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)8s %(name)s | %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)





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
        settings = QSettings()
        style = settings.value(SETTINGS_STYLE, "default", type=str)
        if style == "dark":
            stylesheet = QFile(":/dark.qss")
            
            stylesheet.open(QFile.ReadOnly | QFile.Text)
            stream = QTextStream(stylesheet)
            self.app.setStyleSheet(stream.readAll()) 
        elif style == "light":
            stylesheet = QFile(":/light.qss")
            
            stylesheet.open(QFile.ReadOnly | QFile.Text)
            stream = QTextStream(stylesheet)
            self.app.setStyleSheet(stream.readAll())        
        elif style == "dark2":
            self.app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        elif style == "darkgray":
            self.app.setStyleSheet(qdarkgraystyle.load_stylesheet())
        else:
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
        
        self.setAccessibleName("Hive Desktop")
        self.redrawLock = Lock()
        self.updateLock = Lock()
        
        self.optionsDialog = dialogs.Options(self)
        self.aboutDialog = dialogs.About(self,
            copyright='holger80',
            programName='Hive Desktop',
            version=VERSION,
            website='https://github.com/holgern/hivedesktop',
            websiteLabel='Github',
            comments='"Welcome to Hive desktop!\n This is the first release for testing qt5.\n Please vote for holger80 as witness, if you like this :).',
            licenseName='GPL-3.0',
            # licenseUrl=helpers.joinpath_to_cwd('LICENSE').as_uri(),
            authors=('holger80',),
            # dependencies=[l.strip() for l in requirements.readlines()],
        )		
        self.mdrenderer = MDRenderer(str(helpers.joinpath_to_cwd('themes')))

        # tmpfile = helpers.mktemp(prefix='hivedesktop', suffix='.html')
        
        self.post = {"body": "##test", "authorperm": "@test/test"}
        self.thread = threads.MDThread(self)
        
        
        # self.webview.url = tmpfile.as_uri()
        
        
        self.feedListWidget.currentRowChanged.connect(self.change_displayed_post, Qt.QueuedConnection)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_account_thread)
        
        self.timer2 = QTimer()
        self.timer2.timeout.connect(self.update_account_hist_thread)

        self.timer3 = QTimer()
        self.timer3.timeout.connect(self.update_account_feed_thread)
        
        self.cache_path = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
        self.db_type = "shelve"
        self.db_type = "sqlite"
        self.feed = []
        self.post = None
        # Get settings
        settings = QSettings()
        # Get checkbox state with speciying type of checkbox:
        # type=bool is a replacement of toBool() in PyQt5
        check_state = settings.value(SETTINGS_TRAY, True, type=bool)
        hist_info_check_state = settings.value(SETTINGS_HIST_INFO, True, type=bool)
        account_state = settings.value(SETTINGS_ACCOUNT, "", type=str)
        self.resize(settings.value(SETTINGS_SIZE, QSize(1053, 800)))
        self.move(settings.value(SETTINGS_POS, QPoint(50, 50)))
        
        #self.accountHistTableWidget.setColumnCount(5)
        #self.accountHistTableWidget.setHorizontalHeaderLabels(["type", "1", "2", "3", "timestamp"])
        
        self.update_account_refreshtime = 5000
        
        # Set state
        self.accountHistNotificationCheckBox.setChecked(hist_info_check_state)
        self.autoRefreshCheckBox.setChecked(check_state)
        if check_state:
            self.timer.start(self.update_account_refreshtime)
            self.timer2.start(15000)
            self.timer3.start(60000)
        self.accountLineEdit.setText(account_state)
        # connect the slot to the signal by clicking the checkbox to save the state settings
        self.autoRefreshCheckBox.clicked.connect(self.save_check_box_settings)   
        self.accountHistNotificationCheckBox.clicked.connect(self.save_check_box_settings)  
        self.accountLineEdit.editingFinished.connect(self.save_account_settings)
        self.actionAbout.triggered.connect(self.about)
        self.actionOptions.triggered.connect(self.options)
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
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(self.closeApp)
        
        self.tray = QSystemTrayIcon(QIcon(':/icons/icon.ico'))
        
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.trayAction)
        
        self.tray.setToolTip("Hive Desktop!")
        self.tray.setObjectName("Hive Desktop")
        self.setWindowTitle("Hive Desktop")
        self.tray.show()
        
        splash_pix = QPixmap(':/icons/splash.png')
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        splash.setEnabled(False)
        
        #splash.show()
        #splash.showMessage("<h1><font color='green'>starting...</font></h1>", Qt.AlignTop | Qt.AlignCenter, Qt.black)        
        
        account = account_state
        nodelist = NodeList()
        nodelist.update_nodes()
        self.stm = Steem(node=nodelist.get_nodes(hive=True))
        set_shared_blockchain_instance(self.stm)
        if account != "":
            try:
                self.hist_account = Account(account, steem_instance=self.stm)
            except:
                self.hist_account = None
        else:
            self.hist_account = None
            
        self.refreshPushButton.clicked.connect(self.refresh_account)
        self.refreshPushButton.clicked.connect(self.update_account_hist_thread)
        self.accountLineEdit.editingFinished.connect(self.update_account_info)        
        if self.hasFocus is not None:
            self.init_new_account()
            self.init_new_blocks()
        splash.deleteLater()

    def triggeredPreview(self):
        self.authorLabel.setText(self.post["author"])
        self.titleLabel.setText(self.post["title"])
        self.auhorpermLineEdit.setText(construct_authorperm(self.post["author"], self.post["permlink"]))
        self.thread.start()

    @pyqtSlot(str)
    def cbMDThread(self, html):
        self.webview.setHtml(html)

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def trayAction(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.showNormal()
            else:
                self.hide()

    def closeEvent(self, event):
        if self.tray.isVisible():
            #QMessageBox.information(self, "Hive Desktop",
            #        "The program will keep running in the system tray. To "
            #        "terminate the program, choose <b>Quit</b> in the "
            #        "context menu of the system tray entry.")
            self.tray.showMessage("Hive Desktop",
                    "The program will keep running in the system tray. To "
                    "terminate the program, choose Quit in the "
                    "context menu of the system tray entry.")           
            self.hide()
            event.ignore()

    def hide(self):
        self.update_account_refreshtime = 60000
        self.timer.start(self.update_account_refreshtime)
        QMainWindow.hide(self)
        

    def showNormal(self):
        self.update_account_refreshtime = 5000
        self.timer.start(self.update_account_refreshtime)
        QMainWindow.showNormal(self)

    def showMaximized(self):
        self.update_account_refreshtime = 5000
        self.timer.start(self.update_account_refreshtime)
        QMainWindow.showMaximized(self)

    def closeApp(self):
        settings = QSettings()
        settings.setValue(SETTINGS_SIZE, self.size())
        settings.setValue(SETTINGS_POS, self.pos())
        settings.sync()
        sys.exit()

    def about(self):
        self.aboutDialog.exec_()

    def options(self):
        self.optionsDialog.exec_()

    # Slot checkbox to save the settings
    def save_check_box_settings(self):
        settings = QSettings()
        settings.setValue(SETTINGS_HIST_INFO, self.accountHistNotificationCheckBox.isChecked())
        settings.setValue(SETTINGS_TRAY, self.autoRefreshCheckBox.isChecked())
        if self.autoRefreshCheckBox.isChecked():
            self.timer.start(self.update_account_refreshtime)
            self.timer2.start(15000)
            self.timer3.start(60000)
        else:
            self.timer.stop()
            self.timer2.stop()
            self.timer3.stop()
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
        self.update_account_feed()
        if self.hist_account is not None:
            self.db = database.Database(self.db_type, self.cache_path, self.hist_account["name"])
            self.loadingProgressBar.setMaximum(self.db.get_account().virtual_op_count())
            self.iah_thread = threads.IAHThread(self, self.db)
            self.timer.stop()
            self.timer2.stop()
            self.refreshPushButton.setEnabled(False)
            self.accountLineEdit.setEnabled(False)            
            self.iah_thread.start()
        else:
            self.init_account_hist()
            self.update_account_hist()

    def init_new_blocks(self):
        blockchain = Blockchain()
        self.block_db = database_blocks.DatabaseBlocks(self.db_type, self.cache_path)
        self.loadingBlocksProgressBar.setMaximum(self.block_db.block_history)
        self.blocks_thread = threads.BlocksThread(self, self.block_db, blockchain)
        self.blocks_thread.start()

    @pyqtSlot(str)
    def cIAHThread(self, dummy):
        self.init_account_hist()
        self.update_account_hist()
        self.refreshPushButton.setEnabled(True)
        self.accountLineEdit.setEnabled(True)
        self.tray.showMessage("Ready", "Account history loaded!")     
        self.timer.start(self.update_account_refreshtime)
        self.timer2.start(15000)

    @pyqtSlot(str)
    def cBlocksThread(self, dummy):
        self.init_blocks()
        self.update_blocks()
           
        #self.timer.start(self.update_account_refreshtime)
        #self.timer2.start(15000)

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

    @pyqtSlot(int)
    def set_loading_progress(self, val):
        with self.redrawLock:
            self.loadingProgressBar.setValue(val)

    @pyqtSlot(int)
    def set_loading_blocks_progress(self, val):
        with self.redrawLock:
            self.loadingBlocksProgressBar.setValue(val)

    def init_blocks(self):
        self.blockCountLabel.setText("%d entries" % self.block_db.get_block_count())

    def init_account_hist(self):
        if self.hist_account is None:
            return
        self.account_hist_info = {"start_block": 0}
        self.append_hist_info = {"start_block": 0}

        #if not self.db.has_account_hist():
        #    ops = self.db.get_acc_hist()
        #    self.db.store_account_hist(ops)
        #else:
        #    start_op = self.db.get_last_op()
        #    ops = self.db.read_missing_account_history_data(start_op)
        #    self.db.store_account_hist(ops)
        self.accountHistoryLabel.setText("%d entries" % self.db.get_count())
        self.accountHistTableWidget.clear()

    def append_blocks(self):
        start_op = self.block_db.get_last_op()
        data = self.block_db.read_missing_block_data(start_op)
        # print("finished")
        if len(data) > 0:
            # print(op["timestamp"])
            self.block_db.append_blocks(data)
            self.blockCountLabel.setText("%d entries" % self.block_db.get_block_count())        

    def append_account_hist(self):
        if self.hist_account is None:
            return
        
        # print("loading db")
        
        start_op = self.db.get_last_op()
        data = self.db.read_missing_account_history_data(start_op)
        # print("finished")
        if len(data) > 0:
            # print(op["timestamp"])
            self.db.append_account_hist(data)
            self.accountHistoryLabel.setText("%d entries" % self.db.get_count())

    def update_account_hist_thread(self):
        worker = Worker(self.update_account_hist)
        self.threadpool.start(worker)

    def update_account_feed_thread(self):
        worker = Worker(self.update_account_feed)
        self.threadpool.start(worker)

    @pyqtSlot(int)
    def change_displayed_post(self, row):
        if row < 0:
            return
        if len(self.feed) == 0:
            return
        if len(self.feed) <= row:
            return
        #index = self.feedListWidget.currentIndex()
        #row = index.row()
        self.post = self.feed[row]
        with self.updateLock:
            self.triggeredPreview()
        replies = Comment(self.post).get_all_replies()
        is_shown = [0] * len(replies)
        max_depth = 0
        for i in range(len(replies)):
            if replies[i].depth > max_depth:
                max_depth = replies[i].depth
        self.commentsTreeWidget.clear()
        
        def create_item(reply):
            item = QTreeWidgetItem()
            item.setText(0, reply["author"])
            item.setText(1, reply["body"])
            item.setToolTip(1, reply["body"])
            return item

      
        for i in range(len(replies)):
            if is_shown[i] == 1:
                continue
            reply = replies[i]
            if reply.depth == 1:
                is_shown[i] = 1
                item = create_item(reply)
                
                for j in range(len(replies)):
                    rr = replies[j]
                    if is_shown[j] == 1:
                        continue
                    if rr.depth == 2:
                        is_shown[j] = 1
                        if rr.parent_author == reply["author"] and rr.parent_permlink == reply["permlink"]:
                            rr_item = create_item(rr)
                            if max_depth >= 3:
                                for k in range(len(replies)):
                                    rrr = replies[k]
                                    if is_shown[k] == 1:
                                        continue
                                    if rrr.depth == 3:
                                        is_shown[k] = 1
                                        if rrr.parent_author == rr["author"] and rrr.parent_permlink == rr["permlink"]:
                                            rrr_item = create_item(rrr)
                                            if max_depth >= 4:
                                                for l in range(len(replies)):
                                                    rrrr = replies[l]
                                                    if is_shown[l] == 1:
                                                        continue
                                                    if rrrr.depth == 4:
                                                        is_shown[l] = 1
                                                        if rrrr.parent_author == rrr["author"] and rrrr.parent_permlink == rrr["permlink"]:
                                                            rrrr_item = create_item(rrrr)
                                                            rrr_item.addChild(rrrr_item)
                                        
                                        rr_item.addChild(rrr_item)
                            item.addChild(rr_item)
                
                self.commentsTreeWidget.addTopLevelItem(item)

    def update_account_feed(self):
        if self.hist_account is None:
            return
        try:
            updated_feed = self.hist_account.get_account_posts()
        except:
            print("could not update feed")
            return
        if len(self.feed) == 0:
            self.feed = updated_feed
        else:
            for post in updated_feed[::-1]:
                found = False
                for p in self.feed:
                    if post["authorperm"] == p["authorperm"]:
                        found = True
                if not found:
                    self.feed.insert(0, post)
                    if (addTzInfo(datetime.utcnow()) - post["created"]).total_seconds() / 60 < 5:
                        self.tray.showMessage(post["author"], post["title"])
        with self.updateLock:
            if self.post is None:
                self.post = self.feed[0]
                self.triggeredPreview()

            self.feedListWidget.currentRowChanged.disconnect(self.change_displayed_post)
            self.feedListWidget.clear()
            for post in self.feed[::-1]:
                post_text = "%s - %s" % (post["author"], post["title"])
                post_item = QListWidgetItem()
                post_item.setText(post_text)
                post_item.setToolTip(post["author"])
                self.feedListWidget.insertItem(0, post_item)   
            self.feedListWidget.currentRowChanged.connect(self.change_displayed_post, Qt.QueuedConnection)

    def update_blocks(self):
        return

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
            b = Blockchain()
            start_block = b.get_current_block_num() - 20 * 60 * 24 * 7
            self.account_hist_info["start_block"] = start_block
        else:
            first_call = False

        ops = self.db.load_account_hist(start_block)
     
        for op in ops:
            if op["block"] < start_block:
                # last_block = op["block"]
                continue

            start_block = op["block"]
            new_op_found = True
            tray_item = None
            op_timedelta = formatTimedelta(addTzInfo(datetime.utcnow()) - addTzInfo(op["timestamp"]))
            op_local_time = addTzInfo(op["timestamp"]).astimezone(tz.tzlocal())
            # print("Read %d" % op["index"])
            self.accountHistTableWidget.insertRow(0)
            self.accountHistTableWidget.setItem(0, 4, QTableWidgetItem(str(op_local_time)))
            if op["type"] == "vote":
                
                
                if op["voter"] == self.hist_account["name"]:
                    self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem("Vote"))
                    self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem(op["author"]))
                    
                elif op["weight"] >= 0:
                    self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem("Vote Post"))
                    self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem(op["voter"]))
                    tray_item = "%s - %s (%.2f %%) vote %s" % (op["type"], op["voter"], op["weight"] / 100, op["permlink"])
                else:
                    self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem("Dowvote Post"))
                    self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem(op["voter"]))
                    # hist_item.setToolTip(0, op["permlink"])
                    tray_item = "%s - %s (%.2f %%) downvote %s" % (op["type"], op["voter"], op["weight"] / 100, op["permlink"])
                
                
                self.accountHistTableWidget.setItem(0, 2, QTableWidgetItem("%.2f %%" % (op["weight"] / 100)))
                
            elif op["type"] == "curation_reward":
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                
                curation_reward = self.stm.vests_to_sp(Amount(op["reward"], steem_instance=self.stm))
                self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem("%.3f HP" % curation_reward))
                self.accountHistTableWidget.setItem(0, 2, QTableWidgetItem(construct_authorperm(op["comment_author"], op["comment_permlink"])))
                hist_item = "%s - %s - %.3f HP for %s" % (op_local_time, op["type"], curation_reward, construct_authorperm(op["comment_author"], op["comment_permlink"]))
                tray_item = "%s - %.3f HP for %s" % (op["type"], curation_reward, construct_authorperm(op["comment_author"], op["comment_permlink"]))
            elif op["type"] == "author_reward":
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                sbd_payout = (Amount(op["sbd_payout"], steem_instance=self.stm))
                steem_payout = (Amount(op["steem_payout"], steem_instance=self.stm))
                sp_payout = self.stm.vests_to_sp(Amount(op["vesting_payout"], steem_instance=self.stm))
                
                hist_item = "%s - %s - %s %s %.3f SP for %s" % (op_local_time, op["type"], str(sbd_payout), str(steem_payout), sp_payout, op["permlink"])
                tray_item = "%s - %s %s %.3f SP for %s" % (op["type"], str(sbd_payout), str(steem_payout), sp_payout, op["permlink"])
            elif op["type"] == "custom_json":
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem(op["json_id"]))
                json_data = QTableWidgetItem(op["json"])
                json_data.setToolTip(op["json"])
                self.accountHistTableWidget.setItem(0, 2, json_data)
                hist_item = "%s - %s - %s" % (op_local_time, op["type"], op["id"])
                tray_item = "%s - %s" % (op["type"], op["json_id"])
            elif op["type"] == "transfer":
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                hist_item = "%s - %s - %s from %s" % (op_local_time, op["type"], str(Amount(op["amount"], steem_instance=self.stm)), op["from"])
                tray_item = "%s - %s from %s" % (op["type"], str(Amount(op["amount"], steem_instance=self.stm)), op["from"])
            elif op["type"] == "comment":
                
                
                if op["parent_author"] != "":
                    comment_type = "comment"
                    hist_item = "%s - comment on %s - %s from %s" % (op_local_time, construct_authorperm(op["parent_author"], op["parent_permlink"]), op["title"], op["author"])
                    tray_item = "comment from %s: %s on %s" % (op["author"], op["body"][:100], op["title"])
                    self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                    self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem(op["author"]))
                    body = QTableWidgetItem(op["body"])
                    body.setToolTip(op["body"])
                    self.accountHistTableWidget.setItem(0, 2, body)
                else:
                    comment_type = "post"
                    hist_item = "%s - post - %s from %s" % (op_local_time, op["title"], op["author"])
                    tray_item = "post from %s: %s" % (op["author"], op["title"])
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(comment_type))
            elif op["type"] == "producer_reward":
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                self.accountHistTableWidget.setItem(0, 1, QTableWidgetItem(" %.3f HP" % float(self.stm.vests_to_sp(Amount(op["vesting_shares"])))))
                hist_item = "%s - %s" % (op_local_time, op["type"])
                tray_item = "%s - %.3f HP" % (op["type"], float(self.stm.vests_to_sp(Amount(op["vesting_shares"]))))               
            else:
                self.accountHistTableWidget.setItem(0, 0, QTableWidgetItem(op["type"]))
                hist_item = "%s - %s" % (op_local_time, op["type"])
                tray_item = "%s" % (op["type"])
            
            if self.accountHistNotificationCheckBox.isChecked() and not first_call and tray_item is not None:
                self.tray.showMessage(self.hist_account["name"], tray_item)

        if new_op_found:
            self.account_hist_info["start_block"] = start_block
            
            for op in ops:
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
        
            
            reward_text = "Curation reward (last 24 h): %.3f HP\n" % daily_curation
            reward_text += "Author reward (last 24 h):\n"
            reward_text += "%.3f HP - %.3f HIVE - %.3f HBD" % (daily_author_SP, (daily_author_STEEM), (daily_author_SBD))
            self.text2.setText(reward_text)

def main():
    # To ensure that every time you call QSettings not enter the data of your application, 
    # which will be the settings, you can set them globally for all applications
    QCoreApplication.setOrganizationDomain(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)
    
    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)    

if __name__ == '__main__':
    main()