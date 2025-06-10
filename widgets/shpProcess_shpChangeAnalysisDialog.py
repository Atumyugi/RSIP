import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpChangeAnalysisDialog import Ui_shpChangeAnalysisDialog

from PyQt5.QtCore import Qt, QPoint,QVariant
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsWkbTypes,QgsRasterLayer,QgsVectorLayer,QgsField,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc

PROJECT = QgsProject.instance()

class ShpChangeAnalysisDialogClass(Ui_shpChangeAnalysisDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.preShpPath = None
        self.lastShpPath = None
        self.resPath = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.selectPreShpCb.addItem(layer.name())
                self.selectLastShpCb.addItem(layer.name())
        self.selectSaveFilePB.setIcon(FIF.MORE)
    
    def connectFunc(self):
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.selectPreShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return

        if self.selectLastShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        preLayerName = self.selectPreShpCb.currentText()
        preLayer : QgsVectorLayer = PROJECT.mapLayersByName(preLayerName)[0]

        lastLayerName = self.selectLastShpCb.currentText()
        lastLayer : QgsVectorLayer = PROJECT.mapLayersByName(lastLayerName)[0]

        if preLayerName == lastLayerName:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('路径重复'), self).exec_()
            return

        self.preShpPath = preLayer.source()
        self.lastShpPath = lastLayer.source()
        del preLayer
        del lastLayer
        self.resPath = self.resLE.text()
        
        self.close()



        
