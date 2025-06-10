import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpReprojectDialog import Ui_shpReprojectDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont,QIcon

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsVectorLayer,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc
PROJECT = QgsProject.instance()

class ShpReprojectDialogClass(Ui_shpReprojectDialog,QDialog):
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
        self.resPath = None
        self.targetCrs = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.menu = RoundMenu(parent=self)

        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.VectorLayer:
                self.selectShpCb.addItem(layer.name())
            
            action = Action(text=layer.name(),parent=self)
            self.menu.addAction(action)
        
        self.menu.triggered.connect(self.setLayerCrs)
        self.selectLayerSPB.setFlyout(self.menu)

        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.selectShpCbChanged()
    
    def connectFunc(self):
        self.selectShpCb.currentTextChanged.connect(self.selectShpCbChanged)
        self.selectMorePB.clicked.connect(self.selectMorePBClicked)
        self.selectMapcanvasCrsPB.clicked.connect(self.selectMapcanvasCrsPBClicked)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)

    def setLayerCrs(self,action):
        currentLayerName = action.text()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
        currentCrs = currentLayer.crs().authid()
        self.targetCrsLE.setText(currentCrs)
    
    def selectShpCbChanged(self):
        if self.selectShpCb.currentText() != "":
             currentLayerName = self.selectShpCb.currentText()
             currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
             currentCrs = currentLayer.crs().authid()
             self.sourceCrsLE.setText(currentCrs)
    
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
        
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.targetCrsLE.text() == self.sourceCrsLE.text():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('目标坐标系和源坐标系相同'), self).exec_()
            return
        
        if self.targetCrsLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('坐标系无效'), self).exec_()
            return
        
        self.shpPath = self.selectShpCb.currentText()
        self.resPath = self.resLE.text()
        self.targetCrs =self.targetCrsLE.text()
        
        self.close()
    
