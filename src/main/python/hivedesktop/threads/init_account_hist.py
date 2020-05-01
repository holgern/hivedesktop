#!/usr/bin/env python
# -*- coding: utf-8 -*-
# L. Penaud (https://github.com/lpenaud/markdown-editor-qt/)

from .thread import Thread
from PyQt5.QtCore import pyqtSignal

class IAHThread(Thread):
    val = pyqtSignal(int)
    def __init__(self, parent, db):
        super(IAHThread, self).__init__(parent)
        self.val.connect(parent.set_loading_progress)
        self.sig.connect(parent.cIAHThread)
        self.db = db

    def run(self):
        start_op = None
        if self.db.has_account_hist():
            start_op = self.db.get_last_op()        
        
        if start_op is None:
            acc = self.db.get_account()
            max_index = acc.virtual_op_count()
            ops = []
            i = 0
            for op in acc.history():
                ops.append(op)
                i += 1
                self.val.emit(i)
                if len(ops) % 10000 == 0:
                    self.db.store_account_hist(ops)
                    ops = []
            self.db.store_account_hist(ops)
        else:
            # ops = self.db.read_missing_account_history_data(start_op)
            cnt = self.db.get_count()
            account = self.db.get_account()
            
            if start_op is not None:
                trx_in_block = start_op["trx_in_block"]
                op_in_trx = start_op["op_in_trx"]
                virtual_op = start_op["virtual_op"]        
                start_block = start_op["block"]
                
                # print("account %s - %d" % (account["name"], start_block))
            else:
                start_block = 0
                trx_in_block = 0
                op_in_trx = 0
                virtual_op = 0
        
            data = []
            last_block = 0
            last_trx = trx_in_block
            for op in account.history(start=start_block - 3, use_block_num=True):
                if op["block"] < start_block:
                    # last_block = op["block"]
                    continue
                elif op["block"] == start_block:
                    if op["virtual_op"] == 0:
                        if op["trx_in_block"] < trx_in_block:
                            last_trx = op["trx_in_block"]
                            continue
                        if op["op_in_trx"] <= op_in_trx and (trx_in_block != last_trx or last_block == 0):
                            continue
                    else:
                        if op["virtual_op"] <= virtual_op and (trx_in_block == last_trx):
                            continue
                start_block = op["block"]
                virtual_op = op["virtual_op"]
                trx_in_block = op["trx_in_block"]
        
                if trx_in_block != last_trx or op["block"] != last_block:
                    op_in_trx = op["op_in_trx"]
                else:
                    op_in_trx += 1
                if virtual_op > 0:
                    op_in_trx = 0
                    if trx_in_block > 255:
                        trx_in_block = 0
        
                last_block = op["block"]
                last_trx = trx_in_block
                data.append(op)
                cnt += 1
                self.val.emit(cnt)
                if len(data) % 10000 == 0:
                    self.db.store_account_hist(data)
                    data = []
            self.db.store_account_hist(data)
        self.sig.emit("Ready")

