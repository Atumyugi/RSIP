import os
import os.path as osp

from ui.draw_dialog.web_inputBookmarkNameDialog import Ui_web_inputBookmarkNameDialog
from PyQt5.QtWidgets import QDialog
from qfluentwidgets import MessageBox

class WebInpuBookmarkNameDialogClass(Ui_web_inputBookmarkNameDialog,QDialog):
    def __init__(self,preText,parent=None):
        super().__init__(parent=parent)
        self.preText = preText
        self.parentWindow = parent
        self.setupUi(self)
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.bookmarkNameLE.setText(self.preText)
        self.bookmarkName = None
    
    def connectFunc(self):
        self.okPb.clicked.connect(self.okPbClicked)
        self.cancelPb.clicked.connect(self.close)
    
    def okPbClicked(self):

        currentText = self.bookmarkNameLE.text().strip()
        
        self.bookmarkName = currentText+"@"
        self.close()