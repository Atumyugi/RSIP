import os
import os.path as osp

from appConfig import WebDrawQueryType

from ui.draw_dialog.web_selectProjectTypeDialog import Ui_selectWebProjectTypeDialog
from PyQt5.QtWidgets import QDialog


class WebSelectProjectTypeDialogClass(Ui_selectWebProjectTypeDialog,QDialog):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.parentWindow = parent
        self.setupUi(self)
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.resType = None

    def connectFunc(self):
        self.startPb.clicked.connect(self.startPbClicked)
    
    def startPbClicked(self):
        if self.DrawRb.isChecked():
            self.resType = WebDrawQueryType.Draw
        elif self.ReviewRb.isChecked():
            self.resType = WebDrawQueryType.Review
        elif self.RandomRb.isChecked():
            self.resType = WebDrawQueryType.Random
        
        self.close()