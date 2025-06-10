import sys
import os
import os.path as osp

from ui.shp_process_dialog.shp2rasterDialog import Ui_shp2rasterDialog

from PyQt5.QtCore import Qt, QPoint,QVariant
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsLayerTreeGroup,QgsRasterLayer,QgsVectorLayer,QgsField,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc

PROJECT = QgsProject.instance()

class Shp2RasterDialogClass(Ui_shp2rasterDialog,QDialog):
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
        self.shpPath = None
        self.fieldName = None
        self.pixelWidth = None
        self.pixelHeight = None
        self.dataType = None
        self.resPath = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.selectTemplateTifMenu = RoundMenu(parent=self)
        self.widthHeightDict = {}
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layer.type() == QgsMapLayerType.VectorLayer:
                self.selectShpCb.addItem(layer.name())
            if layerSourcePath.split(".")[-1] in ["tif", "TIF", "TIFF", "GTIFF"]:
                action = Action(text=layer.name(),parent=self)
                action.setObjectName(f"action_{layer.name().split('.')[0]}")
                self.selectTemplateTifMenu.addAction(action)
                self.widthHeightDict[layer.name()] = [layer.width(),layer.height()]
        self.selectTemplateTifMenu.triggered.connect(self.setLayerWidthHeight)
        self.selectLayerTemplatePb.setFlyout(self.selectTemplateTifMenu)

        self.selectSaveFilePB.setIcon(FIF.MORE)
        # other
        dataTypeList = ["Int8","Int16","UInt16","UInt32","Int32","Float32","Float64"]
        self.selectDataTypeCb.addItems(dataTypeList)
        self.selectDataTypeCb.setCurrentIndex(0)
        self.updateFieldCb()
    
    def connectFunc(self):
        self.selectShpCb.currentIndexChanged.connect(self.updateFieldCb)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'tif',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def setLayerWidthHeight(self,action):
        layerName = action.text()
        width,height = self.widthHeightDict[layerName]
        self.WidthSpinBox.setValue(width)
        self.HeightSpinBox.setValue(height)
    
    def updateFieldCb(self):
        currentLayerName = self.selectShpCb.text()
        if currentLayerName != "":
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
            self.selectFieldCb.clear()
            for field in currentLayer.fields():
                field : QgsField
                if field.type() in [QVariant.Type.Int,QVariant.Type.UInt,QVariant.Type.LongLong,QVariant.Type.ULongLong]:
                    self.selectFieldCb.addItem(text=field.name(),icon=":/img/resources/int.png")
                elif field.type() in [QVariant.Type.Double]:
                    self.selectFieldCb.addItem(text=field.name(),icon=":/img/resources/float.png")
        self.selectFieldCb.setCurrentIndex(0)
    
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        if self.selectFieldCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有数值型字段'), self).exec_()
            return
        
        currentLayerName = self.selectShpCb.text()
        self.shpPath = PROJECT.mapLayersByName(currentLayerName)[0].source()
        self.fieldName = self.selectFieldCb.text()
        self.pixelWidth = self.WidthSpinBox.value()
        self.pixelHeight = self.HeightSpinBox.value()
        self.dataType = self.selectDataTypeCb.currentIndex()
        self.resPath = self.resLE.text()
        self.close()

