import os
import os.path as osp

from ui.infer_dialog.segDialog import Ui_segDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsRasterLayer

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

import torch

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,filterMultiBandTif
from yoyiUtils.yoyiDefault import InferType,InferTypeName
from yoyiUtils.yoyiTranslate import yoyiTrans
import appConfig
PROJECT = QgsProject.instance()

class InferSegDialog(Ui_segDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,inferType:InferType,typeName:InferTypeName,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.inferType = inferType
        self.typeName = typeName

        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.inputFileList = []
        self.saveDir = None
        self.imgSize = None
        self.batchSize = None
        self.overlap = None
        self.tolerance = None
        self.removeArea = None
        self.removeHole = None
        self.gpuId = None
    
    def checkResValid(self):
        if self.inputFileList and self.saveDir and self.imgSize \
            and self.batchSize and self.overlap and self.tolerance and self.removeArea \
            and self.removeHole:
            return True
        else:
            return False
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        # 设置解译类型相关参数
        # {self.yoyiTrs._translate(self.typeName.value)}
        self.setWindowTitle(f"{self.yoyiTrs._translate(self.inferType.value)} {self.yoyiTrs._translate('设置')}")
        
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layer.type() == QgsMapLayerType.RasterLayer and layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                self.inputComboBox.addItem(layerSourcePath)
        
        # 建筑特殊设置
        if self.typeName == InferTypeName.Building:
            self.imgSizeRb_512.setChecked(True)
            self.removeAreaSpinBox.setValue(20)

        # 找寻GPU
        self.deviceDict = {}
        for deviceId in range(torch.cuda.device_count()):
            self.deviceDict[torch.cuda.get_device_name(deviceId) + f"_{deviceId}"] = deviceId
            self.selectGpuComboBox.addItem(torch.cuda.get_device_name(deviceId) + f"_{deviceId}")
        self.deviceDict['cpu'] = -1
        self.selectGpuComboBox.addItem('cpu')
        
        self.selectInputFilePB.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)
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

        tifList = checkTifList(self.inputComboBox.currentText())
        tifList = filterMultiBandTif(tifList=tifList)
        if len(tifList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.yoyiTrs._translate('没有有效影像')} {self.yoyiTrs._translate('请检查波段数量大于3,数据类型为Uint8')}", self).exec_()
            return
        
        self.inputFileList = tifList
        if self.imgSizeRb_512.isChecked():
            self.imgSize = 512
            self.batchSize = 8
        elif self.imgSizeRb_1024.isChecked():
            self.imgSize = 1024
            self.batchSize = 4
        else:
            self.imgSize = 2048
            self.batchSize = 1
        
        if self.simplyRb_low.isChecked():
            self.tolerance = 1
        elif self.simplyRb_mid.isChecked():
            self.tolerance = 2
        elif self.simplyRb_high.isChecked():
            self.tolerance = 3
        else:
            self.tolerance = 2
        
        self.overlap = self.overlapSpinBox.value() * 0.01
        self.removeArea = self.removeAreaSpinBox.value()
        self.removeHole = self.removeHoleSpinBox.value()
        self.postName = self.typeName.value + self.yoyiTrs._translate('语义分割')
        self.saveDir = self.saveLE.text()
        self.gpuId = self.deviceDict[self.selectGpuComboBox.currentText()]
        print(self.gpuId)

        self.close()
        

