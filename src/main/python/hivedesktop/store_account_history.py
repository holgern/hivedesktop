import shelve
import bz2
import sys
import pickle
from beem.account import Account
from beem.utils import formatTimeString
import re
import os
from beem.instance import set_shared_steem_instance
from beem.nodelist import NodeList
from beem import Steem
import dataset
#from sqlitedict import SqliteDict
from contextlib import closing
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

def get_acc_hist(account, start=None, use_block_num=True):
    acc = Account(account)
    ops = []
    for op in acc.history(start=start, use_block_num=use_block_num):
        ops.append(op)
    return ops

def store_account_hist(db_type, path, account, ops):
    if db_type == "shelve":
        with shelve.open(path + "account-history-%s.shelf" % (account)) as db:
            db['ops'] = ops
    elif db_type == "pickle":
        db = {"ops": ops} 
        save(path + "account-history-%s.pickle" % (account), db)
    elif db_type == "deepdish":
        db = {"ops": ops}
        dd.io.save(path + "account-history-%s.h5" % (account), db, compression=None)
    elif db_type == "sqlite":
        db = dataset.connect('sqlite:///%s' % (path + "account-history.db"))
        table = db[account]
        table.insert()


def load_account_hist(db_type, path, account):
    if db_type == "shelve":
        with shelve.open(path + "account-history-%s.shelf" % (account)) as db:
            ops = db['ops']
    elif db_type == "pickle":
        ops = load(path + "account-history-%s.pickle" % (account))['ops']
    elif db_type == "deepdish":
        ops = dd.io.load(path + "account-history-%s.pickle" % (account))['ops']
    elif db_type == "sqlite":
        db = dataset.connect('sqlite:///%s' % (path + "account-history.db"))
        table = db[account]
        #table.insert()     
    return ops

def append_account_hist(db_type, path, account, new_ops):
    if db_type == "shelve":
        with shelve.open(path + "account-history-%s.shelf" % (account), writeback=True) as db:
            db['ops'].extend(new_ops)
    elif db_type == "pickle":
        db = load_account_hist(db_type, path, account)
        db['ops'].extend(new_ops)
        store_account_hist(db_type, path, account, db)
    elif db_type == "deepdish":
        db = load_account_hist(db_type, path, account)
        db['ops'].extend(new_ops)
        store_account_hist(db_type, path, account, db)    
    elif db_type == "sqlite":
        db = dataset.connect('sqlite:///%s' % (path + "account-history.db"))
        table = db[account]
        table.append()       

def has_account_hist(db_type, path, account):
    if db_type == "shelve":
        return os.path.isfile(path+"account-history-%s.shelf" % (account))
    elif db_type == "pickle":
        return os.path.isfile(path+"account-history-%s.pickle" % (account))
    elif db_type == "deepdish":
        return os.path.isfile(path+"account-history-%s.h5" % (account))    
    elif db_type == "sqlite":
        db = dataset.connect('sqlite:///%s' % (path + "account-history.db"))
        if account in db:
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
    path = "./"
    db_type = "shelve"

    if not has_account_hist(db_type, path, account_name):

        ops = get_acc_hist(account_name)
        store_account_hist(db_type, path, account_name, ops)
    else:
        ops = load_account_hist(db_type, path, account_name)
            
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
            append_account_hist(db_type, path, account["name"], data)
    
    print("checking %s " % account_name)
    ops = load_account_hist(db_type, path, account["name"])
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
