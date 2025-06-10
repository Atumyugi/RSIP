import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpClipDialog import Ui_shpClipDialog

from PyQt5.QtCore import Qt, QPoint,pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont

from qgis.core import QgsProject,QgsMapLayer,QgsVectorLayer,QgsMapLayerType,QgsWkbTypes,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
from yoyiUtils.custom_maptool import RectangleSelectExtentMapTool

PROJECT = QgsProject.instance()

class ShpClipDialogClass(Ui_shpClipDialog,QDialog):
    isReady = pyqtSignal(list)
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.parentMapCanvas : QgsMapCanvas = self.parentWindow.mapCanvas
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.runMode = None
        self.shpPath = None
        self.resPath = None
        self.extent = None
        self.maskPath = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.tabWidget.tabBar().hide()
        self.tabWidget.setCurrentIndex(0)
        self.extentModePb.setChecked(True)

        font = QFont()
        font.setPointSize(8)
        self.extentLE.setFont(font)

        self.refreshLayers()

        self.selectSaveFilePB.setIcon(FIF.MORE)
    
    def connectFunc(self):
        
        self.modePbGroup.buttonClicked.connect(self.modePbGroupClicked)
        self.selectMapcanvasExtentPb.clicked.connect(self.selectMapcanvasExtentPbClicked)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.drawExtentPb.clicked.connect(self.drawExtentPbClicked)
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
        # sp
        PROJECT.layersAdded.connect(self.refreshLayers)
        PROJECT.layersRemoved.connect(self.refreshLayers)

    def refreshLayers(self):
        self.selectShpCb.clear()
        self.selectMaskLayerCb.clear()

        menu = RoundMenu(parent=self)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            action = Action(text=layer.name(),parent=self)
            menu.addAction(action)
            if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.selectMaskLayerCb.addItem(layer.name())
                self.selectShpCb.addItem(layer.name())
        self.selectLayerExtentPb.setFlyout(menu)
        menu.triggered.connect(self.setLayerExtentStr)

    def setLayerExtentStr(self,action):
        currentLayerName = action.text()
        currentLayer = PROJECT.mapLayersByName(currentLayerName)[0]
        currentExtent = f"{currentLayer.extent().xMinimum():.4f},{currentLayer.extent().xMaximum():.4f},{currentLayer.extent().yMinimum():.4f},{currentLayer.extent().yMaximum():.4f} [{currentLayer.crs().authid()}]"
        self.extentLE.setText(currentExtent)
    
    def modePbGroupClicked(self):
        if self.extentModePb.isChecked():
            self.tabWidget.setCurrentIndex(0)
        else:
            self.tabWidget.setCurrentIndex(1)
    
    def selectMapcanvasExtentPbClicked(self):
        extent : QgsRectangle = self.parentMapCanvas.extent()

        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        crs = mapSetting.destinationCrs().authid()
        extentStr = f"{extent.xMinimum():.4f},{extent.xMaximum():.4f},{extent.yMinimum():.4f},{extent.yMaximum():.4f} [{crs}]"
        self.extentLE.setText(extentStr)
    
    def drawExtentPbClicked(self):
        self.drawExtentMapTool = RectangleSelectExtentMapTool(self.parentMapCanvas)
        self.drawExtentMapTool.drawed.connect(self.drawExtentMapToolDrawed)
        self.drawExtentMapTool.deactivated.connect(lambda: self.setVisible(True))
        if self.parentMapCanvas.mapTool():
            self.parentMapCanvas.mapTool().deactivate()
        self.parentMapCanvas.setMapTool(self.drawExtentMapTool)
        self.setVisible(False)
    
    def drawExtentMapToolDrawed(self,extentStr):
        self.extentLE.setText(extentStr)
        if self.parentMapCanvas.mapTool():
            self.drawExtentMapTool.deactivated.disconnect()
            self.parentMapCanvas.mapTool().deactivate()
            self.parentMapCanvas.unsetMapTool(self.parentMapCanvas.mapTool())
            del self.drawExtentMapTool
        self.setVisible(True)
        

    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return

        if self.extentModePb.isChecked():
            if self.extentLE.text() == "":
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('范围无效'), self).exec_()
                return

            self.runMode = "extent"
            self.shpPath = PROJECT.mapLayersByName(self.selectShpCb.currentText())[0].source()
            self.resPath = self.resLE.text()
            self.extent = self.extentLE.text()
        else:
            if self.selectMaskLayerCb.count() == 0:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
                return
            
            self.runMode = "mask"
            self.shpPath = PROJECT.mapLayersByName(self.selectShpCb.currentText())[0].source()
            self.resPath = self.resLE.text()
            self.maskPath = PROJECT.mapLayersByName(self.selectMaskLayerCb.currentText())[0].source()
        
        print(type(self.parentMapCanvas.mapTool()))
        if self.parentMapCanvas.mapTool() and type(self.parentMapCanvas.mapTool())==RectangleSelectExtentMapTool:
            self.parentMapCanvas.mapTool().deactivate()
            self.parentMapCanvas.unsetMapTool(self.parentMapCanvas.mapTool())

        self.isReady.emit([self.runMode,self.shpPath,self.resPath,self.extent,self.maskPath])
        try:
            PROJECT.layersAdded.disconnect(self.refreshLayers)
            PROJECT.layersRemoved.disconnect(self.refreshLayers)
        except Exception as e:
            pass
        self.close()
