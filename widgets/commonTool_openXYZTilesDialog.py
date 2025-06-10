import os
import os.path as osp
import re
from ui.common_dialog.openXYZTilesDialog import Ui_openXYZTilesDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout

from qgis.core import QgsProject,QgsMapLayer

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.qgisLayerUtils import loadWmsasLayer
from yoyiUtils.yoyiTranslate import yoyiTrans
PROJECT = QgsProject.instance()

class OpenXYZTilesDialogClass(Ui_openXYZTilesDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initUI()
        self.connectFunc()

    def initUI(self):
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.layerName = None
        self.wmsPath = None

    def connectFunc(self):
        self.runPB.clicked.connect(self.runPBClicked)

    def runPBClicked(self):
        pattern = r"[^a-zA-Z0-9\u4e00-\u9fa5]"
        layerName = re.sub(pattern,"",self.layerNameLE.text())
        print(layerName)
        if layerName == "" :
            MessageBox(self.yoyiTrs._translate("警告"), self.yoyiTrs._translate("项目名非法或为空"), self).exec_()
            return

        wms = self.xyzPathLE.text()
        if wms == "" :
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('XYZ切片地址非法或为空'), self).exec_()
            return

        self.layerName = layerName
        self.wmsPath = wms
        
        self.close()