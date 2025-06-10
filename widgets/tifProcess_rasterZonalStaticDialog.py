import os
import os.path as osp

from ui.tif_process_dialog.rasterZonalStaticDialog import Ui_rasterZonalStaticDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import appConfig
class RasterZonalStaticDialog(Ui_rasterZonalStaticDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()

    def initMember(self):
        self.inputFile = None
        self.inputShp = None
        self.saveFile = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.selectInputFilePB.setIcon(FIF.MORE)
        self.selectInputShpPB.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)

        self.inputLE.setReadOnly(True)
        self.saveLE.setReadOnly(True)

    def connectFunc(self):
        self.selectInputFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileTriggered(self.inputLE,filterType='tif',parent=self))
        self.selectInputShpPB.clicked.connect(lambda: qtTriggeredCommonDialog().addFileTriggered(self.inputShpLE,filterType='shp', parent=self))
        self.selectSaveFilePB.clicked.connect(lambda : qtTriggeredCommonDialog().selectSaveFileTriggered(self.saveLE,filterType='shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)

    def runPBClicked(self):
        if not osp.exists(self.inputLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
            return
        if not osp.exists(self.inputShpLE.text()):
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        # if not osp.exists(self.saveLE.text()):
        #     MessageBox('警告', f'不存在的保存路径', self).exec_()
        #     return

        self.inputFile = self.inputLE.text()
        self.inputShp = self.inputShpLE.text()
        self.saveFile = self.saveLE.text()

        self.close()