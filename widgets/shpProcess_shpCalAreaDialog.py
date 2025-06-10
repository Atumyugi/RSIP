import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpCalAreaDialog import Ui_shpCalAreaDialog

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

class ShpCalAreaDialogClass(Ui_shpCalAreaDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.shpPath = None
        self.resPath = None
        self.fieldName = None
        self.fieldLength = None
        self.fieldPrecision = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.selectShpCb.addItem(layer.name())
        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.fieldNameLE.setText("area")
    
    def connectFunc(self):
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        if self.fieldNameLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('字段名称非法'), self).exec_()
            return
        
        currentLayerName = self.selectShpCb.currentText()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]

        self.shpPath = currentLayer.source()
        self.resPath = self.resLE.text()
        self.fieldName = self.fieldNameLE.text().strip()
        self.fieldLength = self.fieldLengthSpinBox.value()
        self.fieldPrecision = self.fieldPrecisionSpinBox.value()
        self.close()