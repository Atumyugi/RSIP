import sys
import os
import os.path as osp

from ui.draw_dialog.shpLabelingDialog import Ui_shpLabelingDialog

from PyQt5.QtCore import Qt, QPoint,QVariant
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QColor

from qgis.core import QgsLabeling,QgsProject,QgsAbstractVectorLayerLabeling,QgsPalLayerSettings,QgsTextFormat,QgsVectorLayerSimpleLabeling,QgsVectorLayer,QgsField,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (ColorPickerButton, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc

PROJECT = QgsProject.instance()

class ShpLabelingDialogClass(Ui_shpLabelingDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,layer,mapcanvas,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.layer: QgsVectorLayer = layer
        self.mapcanvas: QgsMapCanvas = mapcanvas
        self.setupUi(self)
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        
        # 颜色选择 btn
        self.colorBtn = ColorPickerButton(QColor(255, 0, 0), 'color select', self, enableAlpha=False)
        self.horizontalLayout_3.addWidget(self.colorBtn)

        # 字段cb 初始化
        self.fieldNames = []
        for field in self.layer.fields():
            self.fieldNames.append(field.name())
        self.labelingFieldCb.addItems(self.fieldNames)

        # 
        self.shpLabeling : QgsAbstractVectorLayerLabeling = self.layer.labeling()
        if self.shpLabeling:
            if self.layer.labelsEnabled():
                self.openLabelingChb.setChecked(True)

            labelSetting :QgsPalLayerSettings  = self.shpLabeling.settings()
            
            if labelSetting:
                if labelSetting.fieldName and labelSetting.fieldName in self.fieldNames:
                    self.labelingFieldCb.setCurrentText(labelSetting.fieldName)

            textFrom : QgsTextFormat = labelSetting.format()
            if textFrom:
                if textFrom.color():
                    self.colorBtn.setColor(textFrom.color())
                if textFrom.size() and 0<textFrom.size()<100:
                    self.fontSizeSpinBox.setValue(int(textFrom.size()))
    
    def connectFunc(self):
        self.saOk.clicked.connect(lambda: self.updateLabeling(True))
        self.saCancel.clicked.connect(self.close)

    def updateLabeling(self,close=False):
        if self.labelingFieldCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('字段名称非法'), self).exec_()
            return
        
        if self.openLabelingChb.isChecked():
            textFrom = QgsTextFormat()
            textFrom.setColor(self.colorBtn.color)
            textFrom.setSize(self.fontSizeSpinBox.value())
            labelSetting = QgsPalLayerSettings()
            labelSetting.fieldName = self.labelingFieldCb.currentText()
            labelSetting.setFormat(textFrom)
            labelSetting.centroidInside = True
            labeling = QgsVectorLayerSimpleLabeling(labelSetting)
            
            self.layer.setLabeling(labeling)
            self.layer.setLabelsEnabled(True)
        else:
            self.layer.setLabelsEnabled(False)
        
        self.layer.triggerRepaint()
        self.mapcanvas.refresh()

        if close:
            self.close()




            

    
