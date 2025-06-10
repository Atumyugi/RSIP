import sys
import os
import os.path as osp

from ui.common_dialog.createFishNetDialog import Ui_createFishNetDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout

from qgis.core import QgsProject,QgsMapLayer,QgsLayerTree,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans

PROJECT = QgsProject.instance()

def checkAllTifs(layers):
    if len(layers) == 0:
        return False
    for layer in layers:
        if type(layer) is not QgsRasterLayer:
            return False
        elif layer.source().split(".")[-1] not in ["tif", "TIF", "TIFF", "GTIFF"]:
            return False
    return True

def checkTifGroupExtent(layers):
    xMin = sys.maxsize
    xMax = -sys.maxsize
    yMin = sys.maxsize
    yMax = -sys.maxsize
    for layer in layers:
        extent : QgsRectangle = layer.extent()
        xMinTemp = extent.xMinimum()
        xMaxTemp = extent.xMaximum()
        yMinTemp = extent.yMinimum()
        yMaxTemp = extent.yMaximum()
        if xMinTemp < xMin:
            xMin = xMinTemp
        if xMaxTemp > xMax:
            xMax = xMaxTemp
        if yMinTemp < yMin:
            yMin = yMinTemp
        if yMaxTemp > yMax:
            yMax = yMaxTemp
    return (xMin,xMax,yMin,yMax)

class CreateFishNetDialogClass(Ui_createFishNetDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()

    def initMember(self):
        self.runMode = None

        self.groupExtent = None #组的extent
        self.tifPath = None
        self.fishNetSize = None
        self.resPath = None

        self.xyCrs = None
        self.xyExtent = None
        self.xyXNum = None
        self.xyYNum = None

    def initUI(self):
        self.tabWidget.tabBar().hide()
        self.tabWidget.setCurrentIndex(0)
        self.tifModePb.setChecked(True)

        self.selectSaveFilePB.setIcon(FIF.MORE)

        #PROJECT.mapLayersByName()
        self.providerDict = {}
        self.layerDict = {}
        self.qgsLayerTree: QgsLayerTree = PROJECT.layerTreeRoot()
        groups = self.qgsLayerTree.findGroups()
        for group in groups:
            self.selectTifCB.addItem("Group: "+group.name())

        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if self.selectExtentCB.count() < 50:
                self.selectExtentCB.addItem(layerSourcePath)
                self.selectExtentCB2.addItem(layerSourcePath)
                self.layerDict[layer.source()] = layer
            if layerSourcePath.split(".")[-1] in ["tif", "TIF", "TIFF", "GTIFF"]:
                self.selectTifCB.addItem(layerSourcePath)
                self.providerDict[layer.source()] = layer.dataProvider()

        self.showSize()
        self.showLayerExtent()
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

    def connectFunc(self):
        self.modePbGroup.buttonClicked.connect(self.modePbGroupClicked)
        self.selectTifCB.currentIndexChanged.connect(self.showSize)
        self.selectExtentCB2.currentIndexChanged.connect(self.showLayerExtent)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def modePbGroupClicked(self):
        if self.tifModePb.isChecked():
            self.tabWidget.setCurrentIndex(0)
        elif self.wmsModePb.isChecked():
            self.tabWidget.setCurrentIndex(1)
        else:
            self.tabWidget.setCurrentIndex(2)
    
    def showSize(self):
        if self.selectTifCB.currentText() in self.providerDict.keys():
            self.pixelSizeLabel.setText(f"{self.providerDict[self.selectTifCB.currentText()].xSize()} X {self.providerDict[self.selectTifCB.currentText()].ySize()}")

    def showLayerExtent(self):
        if self.selectExtentCB2.currentText() in self.layerDict.keys():
            tempLayer : QgsMapLayer = self.layerDict[self.selectExtentCB2.currentText()]
            tempExtent = tempLayer.extent()
            self.LayerExtentLabel.setText(f"X:{(tempExtent.xMaximum() - tempExtent.xMinimum()):.4f} Y:{(tempExtent.yMaximum() - tempExtent.yMinimum()):.4f}")
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if self.tifModePb.isChecked():
            if self.selectTifCB.count() == 0:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
                return
        
            if "组: " in self.selectTifCB.currentText():
                selectGroup: QgsLayerTreeGroup = self.qgsLayerTree.findGroup(self.selectTifCB.currentText()[3:])
                selectLayers = selectGroup.findLayers()
                for layer,index in zip(selectLayers,range(len(selectLayers))):
                    selectLayers[index] = layer.layer()
                if not checkAllTifs(selectLayers):
                    MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
                    return
                xMin,xMax,yMin,yMax = checkTifGroupExtent(selectLayers)
                self.runMode = "group"
                self.groupExtent = [xMin,xMax,yMin,yMax]
                self.tifPath = selectLayers[0].source()
                self.fishNetSize = self.selectFishNetSizeSB.value()
                self.resPath = self.resLE.text()
            
            else:
                minXy = min(self.providerDict[self.selectTifCB.currentText()].xSize(),
                            self.providerDict[self.selectTifCB.currentText()].ySize())
                if minXy < (self.selectFishNetSizeSB.value()*2):
                    MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('输入格式非法'), self).exec_()
                    return
                self.runMode = "tif"
                self.tifPath = self.selectTifCB.currentText()
                self.fishNetSize = self.selectFishNetSizeSB.value()
                self.resPath = self.resLE.text()
            
            self.close()

        elif self.wmsModePb.isChecked():
            if self.selectExtentCB.count() == 0:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效图层'), self).exec_()
                return

            extentLayer = self.layerDict[self.selectExtentCB.currentText()]

            self.runMode = "extent"
            self.xyCrs = extentLayer.crs()
            self.xyExtent = extentLayer.extent()
            self.xyXNum = self.xSegNumSB.value()
            self.xyYNum = self.ySegNumSB.value()
            self.resPath = self.resLE.text()

            self.close()
        else:
            if self.selectExtentCB2.count() == 0:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效图层'), self).exec_()
                return
            
            selectedLayer: QgsMapLayer = self.layerDict[self.selectExtentCB2.currentText()]
            layerExtent = selectedLayer.extent()

            # x y 方向上的总距离
            xTotalDistance = layerExtent.xMaximum() - layerExtent.xMinimum()
            yTotalDistance = layerExtent.yMaximum() - layerExtent.yMinimum()

            xDistance = self.xDistanceSB.value()
            yDistance = self.yDistanceSB.value()

            if xDistance*2 > xTotalDistance or yDistance*2 > yTotalDistance:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('x或y的距离太大，至少需要是图层距离的两倍以上'), self).exec_()
                return
            
            xyXNum = int(xTotalDistance/xDistance)
            xyYNum = int(yTotalDistance/yDistance) 
            if xyXNum*xyYNum > 100000:
                w = MessageBox(self.yoyiTrs._translate('警告'),self.yoyiTrs._translate('预估格网数量已超过10万，是否要继续？'),self)
                w.yesButton.setText(self.yoyiTrs._translate('确认'))
                w.cancelButton.setText(self.yoyiTrs._translate('取消'))
                if w.exec():
                    pass
                else:
                    return
            self.runMode = "extent"
            self.xyCrs = selectedLayer.crs()
            self.xyExtent = layerExtent
            self.xyXNum = int(xTotalDistance/xDistance)
            self.xyYNum = int(yTotalDistance/yDistance) 
            self.resPath = self.resLE.text()

            self.close()
