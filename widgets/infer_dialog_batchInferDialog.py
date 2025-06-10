import os
import os.path as osp

from ui.infer_dialog.batchInferDialog import Ui_batchInferDialog

from PyQt5.QtCore import Qt, QPoint,QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QAbstractItemView
from PyQt5.QtGui import QFont,QCursor
from qgis.core import QgsProject,QgsMapLayer

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            MenuAnimationType, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

import torch

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,filterMultiBandTif
from yoyiUtils.yoyiDefault import InferType,InferTypeName
from yoyiUtils.yoyiTranslate import yoyiTrans
import appConfig
PROJECT = QgsProject.instance()

class BatchInferDialog(Ui_batchInferDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,segList,insSegList,detecList,obbDetecList,mode='gpu',parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.segList = segList
        self.insSegList = insSegList
        self.detecList = detecList
        self.obbDetecList = obbDetecList
        self.mode = mode

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
        self.confThres = None
        self.nmsThres = None
        self.gpuId = None

        self.inferTypeList = []
        self.inferTypeNameList = []

        self.selectModelList = []
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        # 设置解译类型相关参数
        self.setWindowTitle(f"{self.yoyiTrs._translate('设置')}")
        
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
        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.saveLE.setReadOnly(True)

        #因为有建筑啥的，所以初始remove hole 调小一些
        self.removeHoleSpinBox.setValue(50)

        self.allModelList = []
        selectModelMenu = RoundMenu(parent=self)
        for segModel in self.segList:
            segModel : InferTypeName
            modelCh = segModel.value
            actionText= f"{InferType.Segmentation.value}:{modelCh}<{InferType.Segmentation.name}:{segModel.name}>"
            action = Action(text=actionText)
            selectModelMenu.addAction(action)
            self.allModelList.append(actionText)
        
        for insSegModel in self.insSegList:
            insSegModel : InferTypeName
            modelCh = insSegModel.value
            actionText = f"{InferType.InstanceSegmentation.value}:{modelCh}<{InferType.InstanceSegmentation.name}:{insSegModel.name}>"
            action = Action(text=actionText)
            selectModelMenu.addAction(action)
            self.allModelList.append(actionText)
        
        for detecModel in self.detecList:
            detecModel : InferTypeName
            modelCh = detecModel.value
            actionText = f"{InferType.Detection.value}:{modelCh}<{InferType.Detection.name}:{detecModel.name}>"
            action = Action(text=actionText)
            selectModelMenu.addAction(action)
            self.allModelList.append(actionText)
        
        for obbDetecModel in self.obbDetecList:
            obbDetecModel : InferTypeName
            imodelCh = obbDetecModel.value
            actionText = f"{InferType.ObbDetection.value}:{modelCh}<{InferType.ObbDetection.name}:{obbDetecModel.name}>"
            action = Action(text=actionText)
            selectModelMenu.addAction(action)
            self.allModelList.append(actionText)
        
        self.selectModelSPB.setFlyout(selectModelMenu)
        selectModelMenu.triggered.connect(self.addModelByMenu)
        

        self.slm = QStringListModel()
        self.slm.setStringList(self.selectModelList)
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ListView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ListView.customContextMenuRequested.connect(self.on_custom_menu_requested)

        
    def connectFunc(self):
        self.clearListViewPb.clicked.connect(self.clearListViewPbClicked)

        self.selectInputFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileOrFileDirTriggered(self.inputComboBox,parent=self,lineEditType="ComboBox"))
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.saveLE,parent=self))
        
        self.addAllModelPb.clicked.connect(self.allAllModelPbClicked)

        self.runPB.clicked.connect(self.runPBClicked)
    
    def addModelByMenu(self,action):
        actionText = action.text()
        if actionText not in self.selectModelList:
            self.selectModelList.append(actionText)
            self.slm.setStringList(self.selectModelList)
            self.ListView.setCurrentIndex(self.slm.index(0,0))

    def on_custom_menu_requested(self,pos):
        cusMenu = RoundMenu(parent=self)
        cusMenu.setItemHeight(50)
        deleteSelected = Action(FIF.DELETE, self.yoyiTrs._translate('删除所选'))
        deleteSelected.triggered.connect(self.deleteModel)
        cusMenu.addAction(deleteSelected)
        curPos : QPoint = QCursor.pos()
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    def deleteModel(self):
        curIndex = self.ListView.currentIndex().row()
        if curIndex >=0:
            self.selectModelList.pop(curIndex)
            self.slm.setStringList(self.selectModelList)
        else:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('未选中'), self).exec_()
    
    def clearListViewPbClicked(self):
        self.selectModelList = []
        self.slm.setStringList(self.selectModelList)

    def allAllModelPbClicked(self):
        self.selectModelList = []
        for content in self.allModelList:
            self.selectModelList.append(content)
        
        self.slm.setStringList(self.selectModelList)

    
    def runPBClicked(self):
        
        # 判断需要做哪些模型
        if len(self.selectModelList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.yoyiTrs._translate('模型列表为空')}", self).exec_()
            return
        
        for modelString in self.selectModelList:
            modelEnContent = modelString.split("<")[1][:-1]
            print(modelEnContent)
            modelInferType,modelInferTypeName = modelEnContent.split(":")

            self.inferTypeList.append(InferType[modelInferType])
            self.inferTypeNameList.append(InferTypeName[modelInferTypeName])
        
        print(self.inferTypeList)
        print(self.inferTypeNameList)

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
        self.confThres = self.confSpinBox_2.value()
        self.nmsThres = self.nmsSpinBox.value()
        self.saveDir = self.saveLE.text()
        self.gpuId = self.deviceDict[self.selectGpuComboBox.currentText()]

        self.close()
        

