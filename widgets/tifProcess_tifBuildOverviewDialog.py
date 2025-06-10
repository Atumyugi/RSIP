import os
import os.path as osp

from ui.tif_process_dialog.rasterBuildOverviewDialog import Ui_buildOverviewDialog

from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt

from qgis.core import QgsProject,QgsMapLayer

from qfluentwidgets import MessageBox
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiTranslate import yoyiTrans
import appConfig
PROJECT = QgsProject.instance()

class TifBuildOverviewDialog(Ui_buildOverviewDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.tifPath = None
        self.buildIn = None
        self.clean = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                self.selectTifCb.addItem(layerSourcePath)
        
    def connectFunc(self):
        self.runPB.clicked.connect(self.runPBClicked)
    
    def runPBClicked(self):
        if self.selectTifCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        
        self.tifPath = self.selectTifCb.currentText()
        self.buildIn = self.buildInMyselfCb.isChecked()
        self.clean = self.cleanCb.isChecked()

        self.close()