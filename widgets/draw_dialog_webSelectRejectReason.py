import os
import os.path as osp

from appConfig import WebDrawQueryType

from ui.draw_dialog.web_selectRejectReason import Ui_web_selectRejectReasonDialog
from PyQt5.QtWidgets import QDialog


class WebSelectRejectReasonDialogClass(Ui_web_selectRejectReasonDialog,QDialog):
    def __init__(self,defaultReason="",parent=None):
        super().__init__(parent=parent)
        self.parentWindow = parent
        self.defaultReason = defaultReason
        self.setupUi(self)
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.rejectString = None
        self.reasonLE.setText(self.defaultReason)
        self.reasonLE.clearFocus()

        if self.parentWindow.rejectMissIsChecked:
            self.missCb.setChecked(True)
        else:
            self.missCb.setChecked(False)
        
        if self.parentWindow.rejectFaultIsChecked:
            self.faultCb.setChecked(True)
        else:
            self.faultCb.setChecked(False)

        if self.parentWindow.rejectTrimIsChecked:
            self.trimCb.setChecked(True)
        else:
            self.trimCb.setChecked(False)
        
        if self.parentWindow.rejectClassIsChecked:
            self.classFaultCb.setChecked(True)
        else:
            self.classFaultCb.setChecked(False)

    
    def connectFunc(self):
        self.okPb.clicked.connect(self.okPbClicked)
        self.cancelPb.clicked.connect(self.close)
    
    def okPbClicked(self):

        initString = self.reasonLE.text() + ","

        if self.missCb.isChecked():
            missString = "目标遗漏,"
            self.parentWindow.rejectMissIsChecked = True
        else:
            missString = ""
            self.parentWindow.rejectMissIsChecked = False
        
        if self.faultCb.isChecked():
            faultString = "错误删除,"
            self.parentWindow.rejectFaultIsChecked = True
        else:
            faultString = ""
            self.parentWindow.rejectFaultIsChecked = False
        
        if self.trimCb.isChecked():
            trimString = "修正边界,"
            self.parentWindow.rejectTrimIsChecked = True
        else:
            trimString = ""
            self.parentWindow.rejectTrimIsChecked = False
        
        if self.classFaultCb.isChecked():
            classFaultString = "类别错误,"
            self.parentWindow.rejectClassIsChecked = True
        else:
            classFaultString = ""
            self.parentWindow.rejectClassIsChecked = False
        
        self.rejectString = initString+missString+faultString+trimString+classFaultString
        
        self.close()