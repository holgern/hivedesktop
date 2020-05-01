#!/usr/bin/env python
# -*- coding: utf-8 -*-
# L. Penaud (https://github.com/lpenaud/markdown-editor-qt/)

from .thread import Thread
from PyQt5.QtCore import pyqtSignal

class BlocksThread(Thread):
    val = pyqtSignal(int)
    def __init__(self, parent, db, blockchain):
        super(BlocksThread, self).__init__(parent)
        self.val.connect(parent.set_loading_blocks_progress)
        self.sig.connect(parent.cBlocksThread)
        self.db = db
        self.blockchain = blockchain

    def run(self):
        start_op = None
        if self.db.has_blocks():
            start_op = self.db.get_last_op()        
        
        if start_op is None:
            ops = []
            i = 0
            current_block = self.blockchain.get_current_block_num()
            
            start_block = current_block - self.db.block_history
            last_block = start_block
            for op in self.blockchain.stream(start=start_block, stop=current_block, only_ops=self.db.only_ops, only_virtual_ops=self.db.only_virtual_ops):
                ops.append(op)
                if op["block_num"] > last_block:
                    i += 1
                    self.val.emit(i)
                    last_block = op["block_num"]
                if len(ops) % 10000 == 0:
                    self.db.store_blocks(ops)
                    ops = []
            self.db.store_blocks(ops)
        else:
            # ops = self.db.read_missing_account_history_data(start_op)
            cnt = self.db.get_block_count()
            current_block = self.blockchain.get_current_block_num()
            if start_op is not None:
                trx_num = start_op["trx_num"]        
                block_num = start_op["block_num"]
                start_block = block_num
                
                # print("account %s - %d" % (account["name"], start_block))
            else:
                trx_num = 0
                block_num = 0
                start_block = current_block - self.db.block_history
        
            data = []
            last_block = start_block
            for op in self.blockchain.stream(start=start_block, stop=current_block, only_ops=self.db.only_ops, only_virtual_ops=self.db.only_virtual_ops):
                if op["block_num"] < start_block:
                    # last_block = op["block"]
                    continue
                elif op["block_num"] == start_block:
    
                    if op["trx_num"] <= trx_num:
                        continue            
                 
                data.append(op)
                if op["block_num"] > last_block:
                    last_block = op["block_num"]
                    cnt += 1
                    self.val.emit(cnt)
                if len(data) % 10000 == 0:
                    self.db.store_blocks(data)
                    data = []
            self.db.store_blocks(data)
        self.sig.emit("Ready")

