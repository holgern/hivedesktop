import shelve
import bz2
import sys
import pickle
from beem.account import Account
import re
import os
import json
from PyQt5.QtCore import QStandardPaths
from beem.instance import set_shared_steem_instance
from beem.nodelist import NodeList
from beem import Steem
from beem.utils import formatTimeString, addTzInfo
from beem.amount import Amount
from beem.blockchain import Blockchain
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


class DatabaseBlocks(object):
    def __init__(self, db_type, path):
        self.db_type = db_type
        self.path = path
        self.only_ops = False
        self.only_virtual_ops = False
        self.block_history = 20 * 60 * 24 * 7

    def stream_blocks(self, start=None):
        blockchain = Blockchain()
        current_block = blockchain.get_current_block_num()
        ops = []
        for op in blockchain.stream(start=start, stop=current_block, only_ops=self.only_ops, only_virtual_ops=self.only_virtual_ops):
            ops.append(op)
        return ops

    def get_filename(self):
        if self.db_type == "shelve":
            return os.path.join(self.path, "blocks.shelf")
        elif self.db_type == "pickle":
            return os.path.join(self.path, "blocks.pickle")
        elif self.db_type == "deepdish":
            return os.path.join(self.path, "blocks.h5")
        elif self.db_type == "sqlite":
            return os.path.join(self.path, "blocks.db")
    
    def create_table(self):
        filename = self.get_filename()
        if self.db_type == "sqlite":
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                db.create_table("ops", primary_id='row_id')

    def store_blocks(self, ops):
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
                table = db["ops"]
                for op in ops:
                    json_params = ["required_auths", "required_posting_auths", "extensions", "proposal_ids", "active",
                                   "posting", "props", "owner", "new_owner_authority", "recent_owner_authority"]
                    amount_params = ["reward_steem", "reward_sbd", "reward_vests", "fee", "max_accepted_payout", "amount",
                                     "sbd_amount", "steem_amount", "daily_pay", "min_to_receive", "amount_to_sell"]
                    datetime_params = ["start_date", "end_date", "escrow_expiration", "expiration", "ratification_deadline"]
                    price_params = ["exchange_rate"]
                    for key in op:
                        if key in json_params:
                            op[key] = json.dumps(op[key])
                        elif key in amount_params:
                            op[key] = str(Amount(op[key]))
                        elif key in datetime_params:
                            op[key] = formatTimeString(op[key])
                        elif key in price_params:
                            op[key] = str(Price(op[key]))
                    if "id" in op:
                        json_id = op.pop("id")
                        op["json_id"] = json_id
                    table.insert(op)
                    
    def load_blocks(self, start_block=0):
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
                table = db["ops"]
                ops = []
                for data in table.find(block_num={'>': start_block}, order_by="block_num"):
                    if "trx_id" not in data:
                        data["trx_id"] = "0" * 40
                    if "_id" not in data:
                        data["_id"] = "0" * 40
                    ops.append(data)
        return ops

    def get_last_op(self):
        filename = self.get_filename()
        if self.db_type != "sqlite":
            ops = self.load_blocks()
            return ops[-1]

        with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
            table = db["ops"]
            data = table.find_one(order_by=["-block_num", "-trx_num"])
            if data is None:
                return None
            if "trx_id" not in data:
                data["trx_id"] = "0" * 40
            if "_id" not in data:
                data["_id"] = "0" * 40
        return data     
    
    def append_blocks(self, new_ops):
        filename = self.get_filename()
        if self.db_type == "shelve":
            with shelve.open(filename, writeback=True) as db:
                db['ops'].extend(new_ops)
        elif self.db_type == "pickle":
            ops = self.load_blocks()
            ops.extend(new_ops)
            self.store_blocks(ops)
        elif self.db_type == "deepdish":
            ops = self.load_blocks()
            ops.extend(new_ops)
            self.store_blocks(ops)    
        elif self.db_type == "sqlite":
            self.store_blocks(new_ops)       
    
    def has_blocks(self):
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
            ops = self.load_blocks()
            count = len(ops)
        else:
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                table = db["ops"]
                count = table.count()
        return count

    def get_block_count(self):
        filename = self.get_filename()
        if self.db_type != "sqlite":
            ops = self.load_blocks()
            count = len(ops)
        else:
            with dataset.connect('sqlite:///%s?check_same_thread=False' % (filename)) as db:
                table = db["ops"]
                count = 0
                for block in table.distinct('block_num'):
                    count += 1
        return count

    def read_missing_block_data(self, start_block=None):
        # Go trough all transfer ops
        cnt = 0
        blockchain = Blockchain()
        current_block = blockchain.get_current_block_num()
        
        if start_block is not None:
            trx_num = start_block["trx_num"]
            block_num = start_block["block_num"]
            start_block = block_num
            
            # print("account %s - %d" % (account["name"], start_block))
        else:
            trx_num = 0
            block_num = 0
            start_block = current_block - self.block_history
    
        data = []
        for op in blockchain.stream(start=start_block, stop=current_block, only_ops=self.only_ops, only_virtual_ops=self.only_virtual_ops):
            if op["block_num"] < start_block:
                # last_block = op["block"]
                continue
            elif op["block_num"] == start_block:

                if op["trx_num"] <= trx_num:
                    continue
            data.append(op)
    
            cnt += 1    
        return data

if __name__ == "__main__":
    nodes = NodeList()
    nodes.update_nodes()
    stm = Steem(node=nodes.get_hive_nodes())
    set_shared_steem_instance(stm)
    
    blockchain = Blockchain()
    current_block = blockchain.get_current_block_num()    
    start_block = current_block - 20*60*24*7
    # path = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
    path = "D:\\temp"
    print(path)
    db_type = "sqlite"
    db = DatabaseBlocks(db_type, path)

    if not db.has_blocks():
        print("new blocks")
        ops = db.stream_blocks(start=start_block)
        db.store_blocks(ops)
    else:
        print("loading db")
        
        start_op = db.get_last_op()
        print(start_op)
        data = db.read_missing_block_data(start_op)
        print("finished")
        if len(data) > 0:
            # print(op["timestamp"])
            for d in data:
                print(d)
            db.append_blocks(data)
    print("%d entries" % db.get_count())
    ops = db.load_blocks()
    last_op = {}
    last_op["index"] = -1
    last_op["timestamp"] = formatTimeString('2000-12-29T10:07:45')
    lastest_index = 0
    error_index = -1
    for op in ops[-1000:]:
        lastest_index += 1               
        if (addTzInfo(op["timestamp"]) < addTzInfo(last_op["timestamp"])):
            if error_index < 0:
                error_index = lastest_index - 1
            print("error %s %s" % (formatTimeString(op["timestamp"]), formatTimeString(last_op["timestamp"])))
        last_op = op
    #if error_index > -1:
    #    store_account_hist(db_type, path, account_name, ops[:error_index])
