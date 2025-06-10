
import os
import os.path as osp

from ui.tif_process_dialog.rasterUint16to8Dialog import Ui_raster16to8Dialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,filterMultiBandTif
from yoyiUtils.yoyiTranslate import yoyiTrans

import appConfig
PROJECT = QgsProject.instance()

class Raster16to8Dialog(Ui_raster16to8Dialog,QDialog):
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
        self.clipPercent = None
        self.postName = None
        self.saveDir = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.RasterLayer and layer.source().split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                layerSourcePath: str = layer.source()
                rdp = layer.dataProvider()
                # 2 int16 3 uint16
                if rdp.dataType(1) in [2,3] and layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                    self.selectTifCb.addItem(layerSourcePath)
        
        self.postNameLE.setText("_uint8")

        self.selectInputFilePB.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.saveLE.setReadOnly(True)
    
    def connectFunc(self):
        self.selectInputFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileOrFileDirTriggered(self.selectTifCb,parent=self,lineEditType="ComboBox"))
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.saveLE,parent=self))
        self.runPB.clicked.connect(self.runPBClicked)

    def runPBClicked(self):
        if not osp.exists(self.selectTifCb.currentText()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        if not osp.exists(self.saveLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if self.postNameLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('请输入后缀'), self).exec_()
            return
        tifList = checkTifList(self.selectTifCb.currentText())
        tifList = filterMultiBandTif(tifList,'16')
        if len(tifList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        
        self.inputFileList = tifList
        self.clipPercent = self.DoubleSpinBox.value() * 0.01
        self.postName = self.postNameLE.text().strip()
        self.saveDir = self.saveLE.text()

        self.close()