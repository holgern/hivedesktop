import shelve
import bz2
import sys
import pickle
from beem.account import Account
from beem.utils import formatTimeString
import re
import os
from PyQt5.QtCore import QStandardPaths
from beem.instance import set_shared_steem_instance
from beem.nodelist import NodeList
from beem import Steem
import dataset
import deepdish as dd

def save(filename, myobj):
    """
    save object to file using pickle
    
    @param filename: name of destination file
    @type filename: str
    @param myobj: object to save (has to be pickleable)
    @type myobj: obj
    """

    try:
        f = bz2.BZ2File(filename, 'wb')
    except IOError:
        sys.stderr.write('File ' + filename + ' cannot be written\n')
        return

    pickle.dump(myobj, f, protocol=2)
    f.close()



def load(filename):
    """
    Load from filename using pickle
    
    @param filename: name of file to load from
    @type filename: str
    """

    try:
        f = bz2.BZ2File(filename, 'rb')
    except IOError:
        sys.stderr.write('File ' + filename + ' cannot be read\n')
        return

    myobj = pickle.load(f)
    f.close()
    return myobj


class Database(object):
    def __init__(self, db_type, path, account):
        self.db_type = db_type
        self.path = path
        self.account = account

    def get_acc_hist(self, start=None, use_block_num=True):
        acc = Account(self.account)
        ops = []
        for op in acc.history(start=start, use_block_num=use_block_num):
            ops.append(op)
        return ops

    def get_filename(self):
        if self.db_type == "shelve":
            return os.path.join(self.path, "account-history-%s.shelf" % (self.account))
        elif self.db_type == "pickle":
            return os.path.join(self.path, "account-history-%s.pickle" % (self.account))
        elif self.db_type == "deepdish":
            return os.path.join(self.path, "account-history-%s.h5" % (self.account))
        elif self.db_type == "sqlite":
            return os.path.join(self.path, "account-history.db")
    
    def store_account_hist(self, ops, trx):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename) as db:
                db['ops'] = ops
                db['trx'] = trx
        elif self.db_type == "pickle":
            db = {"ops": ops, "trx": trx} 
            save(filename, db)
        elif self.db_type == "deepdish":
            db = {"ops": ops, "trx": trx}
            dd.io.save(filename, db, compression=None)
        elif self.db_type == "sqlite":
            db = dataset.connect('sqlite:///%s' % (filename))
            table = db[self.account]
            table.insert()
    
    def load_account_hist(self):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename) as db:
                ops = db['ops']
                trx = db['trx']
        elif self.db_type == "pickle":
            data = load(filename)
            ops = data['ops']
            trx = data['trx']
        elif self.db_type == "deepdish":
            data = dd.io.load(filename)
            ops = data['ops']
            trx = data['trx']
            
        elif self.db_type == "sqlite":
            db = dataset.connect('sqlite:///%s' % (filename))
            table = db[self.account]
            #table.insert()     
        return ops, trx
    
    def append_account_hist(self, new_ops, new_trx):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename, writeback=True) as db:
                db['ops'].extend(new_ops)
                db['trx'].extend(new_trx)
        elif self.db_type == "pickle":
            ops, trx = self.load_account_hist()
            ops.extend(new_ops)
            trx.extend(new_trx)
            self.store_account_hist(ops, trx)
        elif db_type == "deepdish":
            ops, trx = self.load_account_hist()
            ops.extend(new_ops)
            trx.extend(new_trx)
            self.store_account_hist(ops, trx)    
        elif db_type == "sqlite":
            db = dataset.connect('sqlite:///%s' % (filename))
            table = db[self.account]
            table.append()       
    
    def has_account_hist(self):
        filename = self.get_filename()
        if self.db_type == "shelve":
            return os.path.isfile(filename + '.dat')
        elif self.db_type == "pickle":
            return os.path.isfile(filename)
        elif self.db_type == "deepdish":
            return os.path.isfile(filename)    
        elif self.db_type == "sqlite":
            db = dataset.connect('sqlite:///%s' % (filename))
            if self.account in db:
                return True
            else:
                return False


if __name__ == "__main__":
    nodes = NodeList()
    nodes.update_nodes()
    stm = Steem(node=nodes.get_hive_nodes())
    set_shared_steem_instance(stm)
    account_name = "holger80"
    account = Account(account_name, steem_instance=stm)
    path = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
    print(path)
    db_type = "shelve"
    db = Database(db_type, path, account_name)

    if not db.has_account_hist():
        print("new account")
        ops = db.get_acc_hist()
        db.store_account_hist(ops)
    else:
        print("loading db")
        ops = db.load_account_hist()
        print("finished")
            
        # Go trough all transfer ops
        cnt = 0

        start_block = ops[-1]
        if start_block is not None:
            trx_in_block = start_block["trx_in_block"]
            op_in_trx = start_block["op_in_trx"]
            virtual_op = start_block["virtual_op"]        
            start_block = start_block["block"]
            
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
        if len(data) > 0:
            # print(op["timestamp"])
            db.append_account_hist(data)
    
    print("checking %s " % account_name)
    ops = db.load_account_hist()
    last_op = {}
    last_op["index"] = -1
    last_op["timestamp"] = '2000-12-29T10:07:45'
    lastest_index = 0
    error_index = -1
    for op in ops:
        lastest_index += 1
        if (op["index"] - last_op["index"]) != 1:
            print("error %s %d %d" % (account_name, op["index"], last_op["index"]))
            if error_index < 0:
                error_index = lastest_index - 1                    
        if (formatTimeString(op["timestamp"]) < formatTimeString(last_op["timestamp"])):
            if error_index < 0:
                error_index = lastest_index - 1
            print("error %s %s %s" % (account_name, op["timestamp"], last_op["timestamp"]))
        last_op = op
    #if error_index > -1:
    #    store_account_hist(db_type, path, account_name, ops[:error_index])
