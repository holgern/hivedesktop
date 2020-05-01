import shelve
import bz2
import sys
import pickle
from beem.account import Account
from beem.utils import formatTimeString
import re
import os
import json
from PyQt5.QtCore import QStandardPaths
from beem.instance import set_shared_steem_instance
from beem.nodelist import NodeList
from beem import Steem
from beem.utils import formatTimeString
from beem.amount import Amount
from beem.price import Price
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

    def get_account(self):
        return Account(self.account)

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
            return os.path.join(self.path, "%s.db" % (self.account))
    
    def create_table_hist(self):
        filename = self.get_filename()
        if self.db_type == "sqlite":
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                db.create_table("history", primary_id='row_id')

    def store_account_hist(self, ops):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename) as db:
                db['ops'] = ops
        elif self.db_type == "pickle":
            db = {"ops": ops} 
            save(filename, db)
        elif self.db_type == "deepdish":
            db = {"ops": ops}
            dd.io.save(filename, db, compression=None)
        elif self.db_type == "sqlite":
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                table = db["history"]
                for op in ops:
                    if "index" not in op:
                        print(op)
                        index = None
                    else:
                        index = op.pop("index")
                    _id = op.pop("_id")
                    _type = op.pop("type")
                    virtual_op = op.pop("virtual_op")
                    block = op.pop("block")
                    trx_in_block = op.pop("trx_in_block")
                    if trx_in_block < 0:
                        trx_in_block = 0
                    
                    if "trx_id" in op:
                        trx_id = op.pop("trx_id")
                        if trx_id == "0000000000000000000000000000000000000000":
                            trx_in_block = 0
                    else:
                        print(op)
                        trx_id = None
                    
                    timestamp = formatTimeString(op.pop("timestamp"))
                    op_in_trx = op.pop("op_in_trx")                    
                    
                    parameter_list = ["from", "to", "memo", "voter", "permlink", "account", "weight",
                                      "author", "json_metadata", "curator", "reward", "comment_permlink",
                                      "comment_author", "amount", "parent_author", "parent_permlink",
                                      "title", "body", "reward_steem", "reward_sbd", "reward_vests",
                                      "id", "json", "delegator", "delegatee", "vesting_shares",
                                      "witness", "approve", "sbd_payout", "steem_payout", "vesting_payout",
                                      "owner", "orderid", "amount_to_sell", "min_to_receive", "fill_or_kill",
                                      "expiration", "current_owner", "current_orderid", "current_pays",
                                      "open_owner", "open_orderid", "open_pays", "benefactor", "producer",
                                      "publisher", "exchange_rate", "required_auths", "required_posting_auths", "max_accepted_payout",
                                      "percent_steem_dollars", "allow_votes", "allow_curation_rewards", "extensions",
                                      "proposal_ids", "fee", "creator", "new_account_name", "active", "posting",
                                      "delegation", "memo_key", "props", "url", "requestid", "amount_in", "amount_out",
                                      "posting_json_metadata", "account_to_recover", "new_recovery_account",
                                      "block_signing_key", "maximum_block_size", "sbd_interest_rate", "proxy",
                                      "from_account", "to_account", "withdrawn", "deposited", "interest", "request_id",
                                      "recovery_account", "new_owner_authority", "recent_owner_authority",
                                      "percent", "auto_vest"
                                      ]
                    amount_params = ["amount", "reward", "reward_steem", "reward_sbd", "reward_vests", "vesting_shares",
                                     "sbd_payout", "steem_payout", "vesting_payout", "amount_to_sell", "min_to_receive",
                                     "current_pays", "open_pays", "max_accepted_payout", "fee", "delegation", "amount_in",
                                     "amount_out", "withdrawn", "deposited", "interest"]
                    price_params = ["exchange_rate"]
                    json_params = ["required_auths", "required_posting_auths", "extensions", "proposal_ids", "active",
                                   "posting", "props", "owner", "new_owner_authority", "recent_owner_authority"]
                    extracted_op_values = {}
                    for param in parameter_list:
                        extracted_op_values[param] = None
                        if param in op:
                            if param == "id":
                                extracted_op_values["json_id"] = op.pop("id")
                            elif param in amount_params:
                                extracted_op_values[param] = str(Amount(op.pop(param)))
                            elif param in price_params:
                                extracted_op_values[param] = str(Price(op.pop(param)))
                            elif param in json_params:
                                extracted_op_values[param] = json.dumps(op.pop(param))
                            else:
                                extracted_op_values[param] = op.pop(param)
                    if len(op) > 0:
                        print(op)
                    db_row = {"index": index, "_id": _id, "type": _type, "virtual_op": virtual_op, "block": block,
                              "trx_in_block": trx_in_block, "trx_id": trx_id, "timestamp": timestamp,
                              "op_in_trx": op_in_trx, "op": op}
                    for param in extracted_op_values:
                        if extracted_op_values[param] is None:
                            continue
                        db_row[param] = extracted_op_values[param]
                    table.insert(db_row)
                    
    def load_account_hist(self, start_block=0):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename) as db:
                ops = db['ops']
        elif self.db_type == "pickle":
            data = load(filename)
            ops = data['ops']
        elif self.db_type == "deepdish":
            data = dd.io.load(filename)
            ops = data['ops']
            
        elif self.db_type == "sqlite":
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                table = db["history"]
                ops = []
                for data in table.find(block={'>': start_block}, order_by="block"):
                    op = data.pop("op")
                    for key in list(op.keys()):
                        data[key] = op[key]
                    if "trx_id" not in data:
                        data["trx_id"] = "0" * 40
                    if "_id" not in data:
                        data["_id"] = "0" * 40
                    ops.append(data)
        return ops

    def get_last_op(self):
        filename = self.get_filename()
        if self.db_type != "sqlite":
            ops = self.load_account_hist()
            return ops[-1]

        with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
            table = db["history"]
            data = table.find_one(order_by=["-block", "-virtual_op", "-trx_in_block", "-op_in_trx"])
            if data is None:
                return None
            op = data.pop("op")
            for key in list(op.keys()):
                data[key] = op[key]
            if "trx_id" not in data:
                data["trx_id"] = "0" * 40
            if "_id" not in data:
                data["_id"] = "0" * 40
        return data     
    
    def append_account_hist(self, new_ops):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename, writeback=True) as db:
                db['ops'].extend(new_ops)
        elif self.db_type == "pickle":
            ops = self.load_account_hist()
            ops.extend(new_ops)
            self.store_account_hist(ops)
        elif self.db_type == "deepdish":
            ops = self.load_account_hist()
            ops.extend(new_ops)
            self.store_account_hist(ops)    
        elif self.db_type == "sqlite":
            self.store_account_hist(new_ops)       
    
    def has_account_hist(self):
        filename = self.get_filename()
        if self.db_type == "shelve":
            return os.path.isfile(filename + '.dat')
        elif self.db_type == "pickle":
            return os.path.isfile(filename)
        elif self.db_type == "deepdish":
            return os.path.isfile(filename)    
        elif self.db_type == "sqlite":
            return os.path.isfile(filename)

    def get_count(self):
        filename = self.get_filename()
        if self.db_type != "sqlite":
            ops = self.load_account_hist()
            count = len(ops)
        else:
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                table = db["history"]
                count = table.count()
        return count

    def read_missing_account_history_data(self, start_block=None):
        # Go trough all transfer ops
        cnt = 0
        account = Account(self.account)
        
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
                    if op["trx_in_block"] <= trx_in_block:
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
        return data

if __name__ == "__main__":
    nodes = NodeList()
    nodes.update_nodes()
    stm = Steem(node=nodes.get_hive_nodes())
    set_shared_steem_instance(stm)
    account_name = "holger80"
    account = Account(account_name, steem_instance=stm)
    # path = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
    path = "D:\\temp"
    print(path)
    db_type = "shelve"
    db = Database(db_type, path, account_name)

    if not db.has_account_hist():
        print("new account")
        ops = db.get_acc_hist()
        db.store_account_hist(ops)
    else:
        print("loading db")
        
        start_op = db.get_last_op()
        print(start_op)
        data = db.read_missing_account_history_data(start_op)
        print("finished")
        if len(data) > 0:
            # print(op["timestamp"])
            for d in data:
                print(d)
            db.append_account_hist(data)
    print("%d entries" % db.get_count())
    print("checking %s " % account_name)
    ops = db.load_account_hist()
    last_op = {}
    last_op["index"] = -1
    last_op["timestamp"] = '2000-12-29T10:07:45'
    lastest_index = 0
    error_index = -1
    for op in ops[-1000:]:
        lastest_index += 1
        if (op["index"] - last_op["index"]) != 1 and last_op["index"] != -1:
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
