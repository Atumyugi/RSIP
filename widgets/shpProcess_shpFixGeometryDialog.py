import os
import os.path as osp

from ui.shp_process_dialog.shpFixGeometryDialog import Ui_shpFixGeoDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout, QWidget

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,checkAllFileList
from yoyiUtils.yoyiTranslate import yoyiTrans
PROJECT = QgsProject.instance()

class ShpFixGeometryDialogClass(Ui_shpFixGeoDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.inputFileList = []
        self.postName = None
        self.saveDir = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layer.type() == QgsMapLayerType.VectorLayer:
                self.inputComboBox.addItem(layerSourcePath)
            
        self.postNameLE.setText("_fix")

        self.selectInputFilePB.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)
        self.resLE.setReadOnly(True)
        
        
    def connectFunc(self):
        self.selectInputFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileOrFileDirTriggered(self.inputComboBox,filterType="shp",parent=self,lineEditType="ComboBox"))
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.resLE,parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
    
    def runPBClicked(self):
        if not osp.exists(self.inputComboBox.currentText()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if not osp.exists(self.resLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if self.postNameLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('请输入后缀'), self).exec_()
            return

        shpList = checkAllFileList(self.inputComboBox.currentText(),postType="shp")
        if len(shpList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        self.inputFileList = shpList
        self.postName = self.postNameLE.text().strip()
        self.saveDir = self.resLE.text()

        self.close()