from PyQt5.QtWidgets import QWidget, QDialog
from hivedesktop.dialogs.ui_options import Ui_Options


class Options(QDialog, Ui_Options):
    def __init__(self, parent = None, **kwargs):
        super(Options, self).__init__()
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.parent = parent
