import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpExportDialog import Ui_shpExportDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont,QIcon

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsVectorLayer,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc
PROJECT = QgsProject.instance()

class ShpExportDialogClass(Ui_shpExportDialog,QDialog):
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
        self.shpLayerName = None
        self.targetCrs = None
        self.onlyExportSelected = None
        self.encoding = None
        self.resPath = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.selectLayerCrsMenu = RoundMenu(parent=self)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.VectorLayer:
                self.selectShpCb.addItem(layer.name())
            action = Action(text=layer.name(),parent=self)
            action.setObjectName(f"action_{layer.name().split('.')[0]}")
            self.selectLayerCrsMenu.addAction(action)
        
        self.selectLayerCrsMenu.triggered.connect(self.setLayerCrs)
        self.selectLayerSPB.setFlyout(self.selectLayerCrsMenu)
        self.selectSaveFilePB.setIcon(FIF.MORE)

        self.encodeCb.addItems(["UTF-8","gbk"])
        self.encodeCb.setCurrentIndex(0)

        self.selectShpCbChanged()
    
    def connectFunc(self):
        self.selectShpCb.currentTextChanged.connect(self.selectShpCbChanged)
        self.selectMapcanvasCrsPB.clicked.connect(self.selectMapcanvasCrsPBClicked)
        self.selectMorePB.clicked.connect(self.selectMorePBClicked)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'extraShapeFile',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def setLayerCrs(self,action):
        currentLayerName = action.text()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
        currentCrs = currentLayer.crs().authid()
        self.targetCrsLE.setText(currentCrs)


    def selectShpCbChanged(self):
        currentLayerName = self.selectShpCb.currentText()
        if currentLayerName != "":
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
            currentCrs = currentLayer.crs().authid()
            self.sourceCrsLE.setText(currentCrs)
            self.targetCrsLE.setText(currentCrs)
    
    def selectMapcanvasCrsPBClicked(self):
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        self.targetCrsLE.setText(mapSetting.destinationCrs().authid())

    def selectMorePBClicked(self):
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        dialog = QgsProjectionSelectionDialog()
        dialog.setWindowIcon(QIcon(":/img/resources/logo.png"))
        dialog.setCrs(mapSetting.destinationCrs())
        dialog.exec()

        if dialog.hasValidSelection():
            self.targetCrsLE.setText(dialog.crs().authid())
        
        dialog.deleteLater()

    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        currentLayerName = self.selectShpCb.currentText()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
        
        if self.resLE.text() == currentLayer.source():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('不可覆盖原文件'), self).exec_()
            return
        
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        if self.targetCrsLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('坐标系无效'), self).exec_()
            return
        
        self.shpLayerName = self.selectShpCb.currentText()
        self.targetCrs = self.targetCrsLE.text()
        self.onlyExportSelected = self.onlyExportSelectedCb.isChecked()
        self.encoding = self.encodeCb.currentText()
        self.resPath = self.resLE.text()

        self.close()
        

        
    
        

    
