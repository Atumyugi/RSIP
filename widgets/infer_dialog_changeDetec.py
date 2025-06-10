import os
import os.path as osp

from ui.infer_dialog.changeDetecDialog import Ui_changeDetecDialog

from PyQt5.QtCore import Qt, QPoint,pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from qgis.core import QgsProject,QgsMapLayer,QgsMapSettings,QgsCoordinateTransform,QgsGeometry,QgsRectangle
from qgis.gui import QgsMapCanvas
from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

import torch

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,filterMultiBandTif
from yoyiUtils.yoyiDefault import InferType,InferTypeName
from yoyiUtils.custom_maptool import RectangleSelectExtentMapTool
from yoyiUtils.yoyiTranslate import yoyiTrans

PROJECT = QgsProject.instance()

class InferChangeDetecDialog(Ui_changeDetecDialog,QDialog):
    isReady = pyqtSignal(list)
    def __init__(self,yoyiTrs:yoyiTrans,inferType:InferType,typeName:InferTypeName,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.parentMapCanvas : QgsMapCanvas = self.parentWindow.mapCanvas
        self.inferType = inferType
        self.typeName = typeName

        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.tifPath = None
        self.tifIIPath = None
        self.saveDir = None
        self.postName = None
        self.imgSize = None
        self.batchSize = None
        self.overlap = None
        self.tolerance = None
        self.removeArea = None
        self.removeHole = None
        self.gpuId = None
        self.drawedExtentTuple = None
        self.extraExtent = None
        # sp
        self.minArea = 2000000
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        # 设置解译类型相关参数
        self.setWindowTitle(f"{self.yoyiTrs._translate(self.typeName.value)}{self.yoyiTrs._translate(self.inferType.value)}")
        
        # 找寻GPU
        self.deviceDict = {}
        for deviceId in range(torch.cuda.device_count()):
            self.deviceDict[torch.cuda.get_device_name(deviceId) + f"_{deviceId}"] = deviceId
            self.selectGpuComboBox.addItem(torch.cuda.get_device_name(deviceId) + f"_{deviceId}")
        self.deviceDict['cpu'] = -1
        self.selectGpuComboBox.addItem('cpu')

        self.refreshLayers()

        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.saveLE.setReadOnly(True)
    
    def connectFunc(self):
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.saveLE,parent=self))
        self.drawExtentPb.clicked.connect(self.drawExtentPbClicked)
        self.runPB.clicked.connect(self.runPBClicked)
        # sp
        PROJECT.layersAdded.connect(self.refreshLayers)
        PROJECT.layersRemoved.connect(self.refreshLayers)
    
    def refreshLayers(self):
        self.preTifComboBox.clear()
        self.lateTifComboBox.clear()
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in ["tif", "TIF", "TIFF", "GTIFF"]:
                self.preTifComboBox.addItem(layer.name())
                self.lateTifComboBox.addItem(layer.name())
         
    
    def drawExtentPbClicked(self):
        if self.preTifComboBox.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return

        if self.preTifComboBox.currentText() == self.lateTifComboBox.currentText():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('前后期影像一致'), self).exec_()
            return
        
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        mapCrs = mapSetting.destinationCrs()
        preLayer = PROJECT.mapLayersByName(self.preTifComboBox.currentText())[0]
        preLayerExtent = preLayer.extent()
        if preLayer.crs().authid() != mapCrs.authid():
            xform = QgsCoordinateTransform(preLayer.crs(),mapCrs,PROJECT.transformContext())
            tempGeo = QgsGeometry.fromRect(preLayerExtent)
            tempGeo.transform(xform)
            preLayerExtent = tempGeo.boundingBox()

        lateLayer = PROJECT.mapLayersByName(self.lateTifComboBox.currentText())[0]
        lateLayerExtent = lateLayer.extent()
        if lateLayer.crs().authid() != mapCrs.authid():
            xform = QgsCoordinateTransform(lateLayer.crs(),mapCrs,PROJECT.transformContext())
            tempGeo = QgsGeometry.fromRect(lateLayerExtent)
            tempGeo.transform(xform)
            lateLayerExtent = tempGeo.boundingBox()
        
        if not preLayerExtent.intersects(lateLayerExtent):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('前后期影像没有相交'), self).exec_()
            return
        
        intersectExtent = preLayerExtent.intersect(lateLayerExtent)

        self.drawExtentMapTool = RectangleSelectExtentMapTool(self.parentMapCanvas,
                                                              containExtent=intersectExtent,
                                                              minArea=self.minArea,
                                                              extraCrs=preLayer.crs(),
                                                              parent=self.parentWindow)
        self.drawExtentMapTool.drawed.connect(self.drawExtentMapToolDrawed)
        self.drawExtentMapTool.deactivated.connect(lambda: self.setVisible(True))
        if self.parentMapCanvas.mapTool():
            self.parentMapCanvas.mapTool().deactivate()
        self.parentMapCanvas.setMapTool(self.drawExtentMapTool)
        self.setVisible(False)
    
    def drawExtentMapToolDrawed(self,extentStr:str):
        self.extentLE.setText(extentStr)
        self.drawedExtentTuple = self.drawExtentMapTool.extraTuple
        if self.parentMapCanvas.mapTool():
            self.drawExtentMapTool.deactivated.disconnect()
            self.parentMapCanvas.mapTool().deactivate()
            self.parentMapCanvas.unsetMapTool(self.parentMapCanvas.mapTool())
            del self.drawExtentMapTool
        self.setVisible(True)
        
    def runPBClicked(self):
        if self.saveLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return

        if self.preTifComboBox.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return

        if self.preTifComboBox.currentText() == self.lateTifComboBox.currentText():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('前后期影像一致'), self).exec_()
            return

        preLayer = PROJECT.mapLayersByName(self.preTifComboBox.currentText())[0]
        lateLayer = PROJECT.mapLayersByName(self.lateTifComboBox.currentText())[0]
        self.tifPath = preLayer.source()
        self.tifIIPath = lateLayer.source()

        if preLayer.crs().authid() != lateLayer.crs().authid():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('前后期影像坐标系不一致'), self).exec_()
            return

        preLayerExtent = preLayer.extent()
        lateLayerExtent = lateLayer.extent()
        if not preLayerExtent.intersects(lateLayerExtent):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('前后期影像没有相交'), self).exec_()
            return
        
        if self.onlyInferExtentCb.isChecked():
            if not self.drawedExtentTuple:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('未选择感兴趣范围'), self).exec_()
                return
            else:
                self.extraExtent = self.drawedExtentTuple
        
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
        self.postName = self.typeName.value + self.yoyiTrs._translate('变化检测')
        self.saveDir = self.saveLE.text()
        self.gpuId = self.deviceDict[self.selectGpuComboBox.currentText()]
        self.isReady.emit([self.tifPath,self.tifIIPath,self.saveDir,self.postName,
            self.typeName,self.imgSize,self.batchSize,self.overlap,self.tolerance,
            self.removeArea,self.removeHole,self.gpuId,self.extraExtent])
        try:
            PROJECT.layersAdded.disconnect(self.refreshLayers)
            PROJECT.layersRemoved.disconnect(self.refreshLayers)
        except Exception as e:
            pass
        self.close()
        

