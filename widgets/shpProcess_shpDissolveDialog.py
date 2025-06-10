import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpDissolveDialog import Ui_shpDissolveDialog

from PyQt5.QtCore import Qt, QPoint,QVariant,QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QAbstractItemView
from PyQt5.QtGui import QFont,QCursor

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsWkbTypes,QgsRasterLayer,QgsVectorLayer,QgsField,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            MenuAnimationType, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc

PROJECT = QgsProject.instance()

class ShpDissolveDialogClass(Ui_shpDissolveDialog,QDialog):
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
        self.fields = None

        self.fieldStringList = []
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.selectShpCb.addItem(layer.name())
        self.selectSaveFilePB.setIcon(FIF.MORE)
        
        # 列表
        self.slm = QStringListModel()
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ListView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ListView.customContextMenuRequested.connect(self.on_custom_menu_requested)

        self.refreshFieldView()
    def connectFunc(self):
        self.selectShpCb.currentIndexChanged.connect(self.refreshFieldView)
        self.clearListViewPb.clicked.connect(self.refreshFieldView)
        self.addAllFieldPb.clicked.connect(self.addAllFieldPbClicked)

        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def on_custom_menu_requested(self,pos):
        cusMenu = RoundMenu(parent=self)
        cusMenu.setItemHeight(50)
        deleteSelected = Action(FIF.DELETE, self.yoyiTrs._translate('删除所选'))
        deleteSelected.triggered.connect(self.deleteField)
        cusMenu.addAction(deleteSelected)
        curPos : QPoint = QCursor.pos()
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    def deleteField(self):
        curIndex = self.ListView.currentIndex().row()
        if curIndex >=0:
            self.fieldStringList.pop(curIndex)
            self.slm.setStringList(self.fieldStringList)
        else:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('未选中字段'), self).exec_() 

    def refreshFieldView(self):
        self.fieldStringList = []
        self.slm.setStringList(self.fieldStringList)

        if self.selectShpCb.count() > 0:
            currentLayerName = self.selectShpCb.currentText()
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
            selectFieldMenu = RoundMenu(parent=self)
            for field in currentLayer.fields():
                field : QgsField
                action = Action(text=field.name())
                selectFieldMenu.addAction(action)
            self.selectFieldSPB.setFlyout(selectFieldMenu)
            selectFieldMenu.triggered.connect(self.addFieldByMenu)
    
    def addFieldByMenu(self,action):
        fieldName = action.text()
        if fieldName not in self.fieldStringList:
            self.fieldStringList.append(fieldName)
            self.slm.setStringList(self.fieldStringList)
            self.ListView.setCurrentIndex(self.slm.index(0,0))
    
    def addAllFieldPbClicked(self):
        self.fieldStringList = []
        self.slm.setStringList(self.fieldStringList)

        if self.selectShpCb.count() > 0:
            currentLayerName = self.selectShpCb.currentText()
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
            selectFieldMenu = RoundMenu(parent=self)
            for field in currentLayer.fields():
                field : QgsField
                action = Action(text=field.name())
                selectFieldMenu.addAction(action)
                self.fieldStringList.append(field.name())
            self.selectFieldSPB.setFlyout(selectFieldMenu)
            selectFieldMenu.triggered.connect(self.addFieldByMenu)

            self.slm.setStringList(self.fieldStringList)
            self.ListView.setCurrentIndex(self.slm.index(0,0))
    
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return

        currentLayerName = self.selectShpCb.currentText()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]

        self.shpPath = currentLayer.source()
        self.resPath = self.resLE.text()
        self.fields = self.fieldStringList

        self.close()
    

            
