#!/usr/bin/env python
# -*- coding: utf-8 -*-
# L. Penaud (https://github.com/lpenaud/markdown-editor-qt/)

from PyQt5.Qt import QDialog

def isRejected(dialogCode):
    return dialogCode == QDialog.Rejected

def isAccepted(dialogCode):
    return dialogCode == QDialog.Accepted
