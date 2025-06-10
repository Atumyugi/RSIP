import os
import os.path as osp

from ui.tif_process_dialog.rasterRecombineDialog import Ui_rasterRecombineDialog

from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt

from qgis.core import QgsProject,QgsMapLayer

from qfluentwidgets import MessageBox
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiTranslate import yoyiTrans
import appConfig
PROJECT = QgsProject.instance()

class TifRecombineDialog(Ui_rasterRecombineDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.recombineList = None
        self.tifPath = None
        self.resPath = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                self.selectTifCb.addItem(layerSourcePath)
        
        self.selectSaveFilePB.setIcon(FIF.MORE)
    
    def connectFunc(self):
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.saveLE,'tif',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
    
    def runPBClicked(self):
        if self.saveLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.selectTifCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        
        if self.recombineLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('重组合顺序非法'), self).exec_()
            return

        recombineLEText : str = self.recombineLE.text().strip()
        recombineLEText = recombineLEText.replace("，",",")
        recombineList : list[str] = recombineLEText.split(",")
        if len(recombineList) < 1:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('重组合顺序非法'), self).exec_()
            return
        for recombineContent in recombineList:
            if not recombineContent.isdigit():
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('重组合顺序非法'), self).exec_()
                return

        self.recombineList = recombineList
        self.tifPath = self.selectTifCb.currentText()
        self.resPath = self.saveLE.text()

        self.close()