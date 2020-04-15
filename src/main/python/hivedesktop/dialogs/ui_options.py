# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui\options.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Options(object):
    def setupUi(self, Options):
        Options.setObjectName("Options")
        Options.resize(722, 474)
        self.gridLayout = QtWidgets.QGridLayout(Options)
        self.gridLayout.setObjectName("gridLayout")
        self.frame = QtWidgets.QFrame(Options)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.frame)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.filterLineEdit = QtWidgets.QLineEdit(self.frame)
        self.filterLineEdit.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filterLineEdit.sizePolicy().hasHeightForWidth())
        self.filterLineEdit.setSizePolicy(sizePolicy)
        self.filterLineEdit.setStatusTip("")
        self.filterLineEdit.setWhatsThis("")
        self.filterLineEdit.setText("")
        self.filterLineEdit.setObjectName("filterLineEdit")
        self.gridLayout_2.addWidget(self.filterLineEdit, 0, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.frame)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 0, 1, 1, 1)
        self.listWidget = QtWidgets.QListWidget(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy)
        self.listWidget.setObjectName("listWidget")
        item = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(item)
        self.gridLayout_2.addWidget(self.listWidget, 1, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(self.frame)
        self.tabWidget.setObjectName("tabWidget")
        self.notificationsTab = QtWidgets.QWidget()
        self.notificationsTab.setObjectName("notificationsTab")
        self.notifyVoteCheckBox = QtWidgets.QCheckBox(self.notificationsTab)
        self.notifyVoteCheckBox.setEnabled(False)
        self.notifyVoteCheckBox.setGeometry(QtCore.QRect(10, 20, 81, 20))
        self.notifyVoteCheckBox.setChecked(True)
        self.notifyVoteCheckBox.setObjectName("notifyVoteCheckBox")
        self.tabWidget.addTab(self.notificationsTab, "")
        self.gridLayout_2.addWidget(self.tabWidget, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.frame, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Options)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(Options)
        self.tabWidget.setCurrentIndex(0)
        self.buttonBox.accepted.connect(Options.accept)
        self.buttonBox.rejected.connect(Options.reject)
        QtCore.QMetaObject.connectSlotsByName(Options)

    def retranslateUi(self, Options):
        _translate = QtCore.QCoreApplication.translate
        Options.setWindowTitle(_translate("Options", "Dialog"))
        self.label.setText(_translate("Options", "Notifications"))
        __sortingEnabled = self.listWidget.isSortingEnabled()
        self.listWidget.setSortingEnabled(False)
        item = self.listWidget.item(0)
        item.setText(_translate("Options", "Notificatons"))
        self.listWidget.setSortingEnabled(__sortingEnabled)
        self.notifyVoteCheckBox.setText(_translate("Options", "votes"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.notificationsTab), _translate("Options", "notifications"))
