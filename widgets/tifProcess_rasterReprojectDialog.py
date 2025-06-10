import sys
import os
import os.path as osp

from ui.tif_process_dialog.rasterReprojectDialog import Ui_rasterReprojectDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont,QIcon

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc
import appConfig
PROJECT = QgsProject.instance()

class RasterReprojectDialogClass(Ui_rasterReprojectDialog,QDialog):
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
        self.tifPath = None
        self.resPath = None
        self.targetCrs = None
        self.resampleMode = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.menu = RoundMenu(parent=self)
        self.crsDict = {}
        self.sourceCrsDict = {}
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                self.selectTifCb.addItem(layerSourcePath)
                self.sourceCrsDict[layerSourcePath] = f"{layer.crs().authid()}"
            
            action = Action(text=layer.name(),parent=self)
            action.setObjectName(f"action_{layer.name().split('.')[0]}")
            self.menu.addAction(action)
            self.crsDict[layer.name()] = f"{layer.crs().authid()}"
        
        self.menu.triggered.connect(self.setLayerCrs)
        self.selectLayerSPB.setFlyout(self.menu)

        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.selectTifCbChanged()
    
    def connectFunc(self):
        self.selectTifCb.currentTextChanged.connect(self.selectTifCbChanged)
        self.selectMorePB.clicked.connect(self.selectMorePBClicked)
        self.selectMapcanvasCrsPB.clicked.connect(self.selectMapcanvasCrsPBClicked)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.saveLE,'tif',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)

    def setLayerCrs(self,action):
        crs = self.crsDict[action.text()]
        self.targetCrsLE.setText(crs)
    
    def selectTifCbChanged(self):
        if self.selectTifCb.currentText() != "":
            self.sourceCrsLE.setText( self.sourceCrsDict[self.selectTifCb.currentText()] )
    
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
        if self.saveLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.selectTifCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        
        if self.targetCrsLE.text() == self.sourceCrsLE.text():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('目标坐标系和源坐标系相同'), self).exec_()
            return
        
        if self.targetCrsLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('坐标系无效'), self).exec_()
            return
        
        self.tifPath = self.selectTifCb.currentText()
        self.resPath = self.saveLE.text()
        self.targetCrs = self.targetCrsLE.text()
        if self.nearestCHB.isChecked():
            self.resampleMode = 0
        elif self.linearCHB.isChecked():
            self.resampleMode = 1
        else:
            self.resampleMode = 2
        
        self.close()
    
