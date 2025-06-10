import os
import os.path as osp

from ui.tif_process_dialog.raster2shpDialog import Ui_raster2VectorDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout

from qgis.core import QgsProject,QgsMapLayer

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans

import appConfig
PROJECT = QgsProject.instance()

class Raster2ShpDialog(Ui_raster2VectorDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()

    def initMember(self):
        self.inputFileList = []
        self.fieldName = None
        self.use8Connect = None
        self.postName = None
        self.saveDir = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                self.inputComboBox.addItem(layerSourcePath)

        self.fieldNameLE.setText("Value")
        self.postNameLE.setText("_trans")
        self.use8ConnectCB.setChecked(True)

        self.selectInputFilePB.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)
        #self.inputComboBox.insertItem()
        self.saveLE.setReadOnly(True)

    def connectFunc(self):
        self.selectInputFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileOrFileDirTriggered(self.inputComboBox,parent=self,lineEditType="ComboBox"))
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.saveLE,parent=self))
        self.runPB.clicked.connect(self.runPBClicked)

    def runPBClicked(self):
        if not osp.exists(self.inputComboBox.currentText()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        if not osp.exists(self.saveLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if self.postNameLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('请输入后缀'), self).exec_()
            return
        tifList = checkTifList(self.inputComboBox.currentText())
        if len(tifList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return

        self.inputFileList = tifList
        self.fieldName = self.fieldNameLE.text()
        self.use8Connect = 1 if self.use8ConnectCB.isChecked() else 0
        self.postName = self.postNameLE.text().strip()
        self.saveDir = self.saveLE.text()

        self.close()