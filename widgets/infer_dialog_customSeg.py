import os
import os.path as osp

from ui.infer_dialog.customSegDialog import Ui_customSegDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from qgis.core import QgsProject,QgsMapLayer

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

class InferCustomSegDialog(Ui_customSegDialog,QDialog):
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
        self.saveDir = None
        self.configPath = None
        self.checkpointPath = None
        self.imgSize = None
        self.batchSize = None
        self.overlap = None
        self.tolerance = None
        self.removeArea = None
        self.removeHole = None
        self.gpuId = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        # 设置解译类型相关参数
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                self.inputComboBox.addItem(layerSourcePath)
        
        # 找寻GPU
        self.deviceDict = {}
        for deviceId in range(torch.cuda.device_count()):
            self.deviceDict[torch.cuda.get_device_name(deviceId) + f"_{deviceId}"] = deviceId
            self.selectGpuComboBox.addItem(torch.cuda.get_device_name(deviceId) + f"_{deviceId}")
        self.deviceDict['cpu'] = -1
        self.selectGpuComboBox.addItem('cpu')
        
        self.selectInputFilePB.setIcon(FIF.MORE)
        self.selectConfigPb.setIcon(FIF.MORE)
        self.selectCheckpointPb.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.selectConfigLE.setReadOnly(True)
        self.selectCheckpointLE.setReadOnly(True)
        self.saveLE.setReadOnly(True)
        
    def connectFunc(self):
        self.selectInputFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileOrFileDirTriggered(self.inputComboBox,parent=self,lineEditType="ComboBox"))
        self.selectConfigPb.clicked.connect(lambda: qtTriggeredCommonDialog().addFileTriggered(self.selectConfigLE,'py',parent=self))
        self.selectCheckpointPb.clicked.connect(lambda: qtTriggeredCommonDialog().addFileTriggered(self.selectCheckpointLE,'pth',parent=self))
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.saveLE,parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
    
    def runPBClicked(self):
        if not osp.exists(self.inputComboBox.currentText()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        
        if not osp.exists(self.selectConfigLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.selectConfigLabel.text()} {self.yoyiTrs._translate('地址非法')}", self).exec_()
            return
        
        if not osp.exists(self.selectCheckpointLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.selectCheckpointLabel.text()} {self.yoyiTrs._translate('地址非法')}", self).exec_()
            return

        if not osp.exists(self.saveLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), f"save Dir {self.yoyiTrs._translate('地址非法')}", self).exec_()
            return
        
        tifList = checkTifList(self.inputComboBox.currentText())
        tifList = filterMultiBandTif(tifList=tifList)
        if len(tifList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.yoyiTrs._translate('没有有效影像')} {self.yoyiTrs._translate('请检查波段数量大于3,数据类型为Uint8')}", self).exec_()
            return
        
        self.inputFileList = tifList
        self.configPath = self.selectConfigLE.text()
        self.checkpointPath = self.selectCheckpointLE.text()
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
        self.postName = "_extract"
        self.saveDir = self.saveLE.text()
        self.gpuId = self.deviceDict[self.selectGpuComboBox.currentText()]
        print(self.gpuId)

        self.close()
        

