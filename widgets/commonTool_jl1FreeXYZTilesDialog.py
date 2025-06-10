import os
import os.path as osp
import re
from ui.common_dialog.jl1FreeXYZTilesDialog import Ui_freeXYZDialog
import requests
from PyQt5.QtCore import QStringListModel,QUrl,Qt
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QAbstractItemView
from PyQt5.QtGui import QDesktopServices
from qgis.core import QgsProject,QgsMapLayer

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.qgisLayerUtils import loadWmsasLayer
import appConfig

PROJECT = QgsProject.instance()

class JL1FreeXYZTilesDialogClass(Ui_freeXYZDialog,QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.setupUi(self)
        self.initUI()
        self.connectFunc()

    def initUI(self):
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.layerName = None
        self.wmsPath = None
        self.setting = appConfig.yoyiSetting()
        preTk = self.setting.configSettingReader.value('freeTk',type=str)
        self.tkLE.setText(preTk)
        self.tileHead = "https://api.jl1mall.com/getMap/{z}/{x}/{-y}?mk="
        self.mks = {
            "2023年度全国高质量一张图" : "73ad26c4aa6957eef051ecc5a15308b4",
            "全球一张图" : "2d9bf902749f1630bc25fc720ba7c29f",
            "2022年第一季度北京市海淀区" : "436c9b6f7fac4c7dae44cec950b2835f",
            "2022年第二季度北京市海淀区" : "f02810d6a4769d4e2f32334766f1366c",
            "2022年第三季度北京市海淀区": "edb9540a94251efaaf57719df82055f6",
            "2022年第四季度北京市海淀区": "5cd3f42aed3f1dd5eeb579a58a5e0358",
            "2022年第一季度吉林省长春市农安县": "eb72df7876ad07fd265d1dbb031d6f20",
            "2022年第二季度吉林省长春市农安县": "72090756d785f86b3351c6e9e41650cd",
            "2022年第三季度吉林省长春市农安县": "2af48fbe2b97fb486e50153931f9433d",
            "2022年第四季度吉林省长春市农安县": "97f746a9e5734b05d979f342fd35cdbe",
            "2022年第一季度宁夏银川市永宁县": "50ddab6e459f028e0a96c58146e0beef",
            "2022年第二季度宁夏银川市永宁县": "fdac6ac6c0f72227aea3cd3a277f4a34",
            "2022年第三季度宁夏银川市永宁县": "59ec5df669c72a4316d2a0d15b0014f3",
            "2022年第四季度宁夏银川市永宁县": "fa53ad954a341738308ed7834591b302",
            "2022年第一季度山东省潍坊市寿光市": "22a6233295c5d76a79c9c75515122202",
            "2022年第二季度山东省潍坊市寿光市": "317b3eac36bb8fb44c70fd1c5ef9e191",
            "2022年第三季度山东省潍坊市寿光市": "e1026d4ff16a7861af00477b56278a55",
            "2022年第四季度山东省潍坊市寿光市": "4840de156930692bae89b1d77700b29a",
            "2022年第一季度河北省雄安新区": "f3c7d80b813a8a8161041b88dc3b10ac",
            "2022年第二季度河北省雄安新区": "36070b4399030492c3e8db6a92856da0",
            "2022年第三季度河北省雄安新区": "ccaf37634b664652d89bccc425433f82",
            "2022年第四季度河北省雄安新区": "611971372589aaf17cadbd7d4ea2fe38",
            "2022年第一季度浙江省杭州市余杭区": "d5bf4cd78ab3017e96e8d1baad97275e",
            "2022年第二季度浙江省杭州市余杭区": "cb1555da0103478294199e647aa6dc40",
            "2022年第三季度浙江省杭州市余杭区": "9a1c0f637ad90c2d4764f48ad75a5d35",
            "2022年第四季度浙江省杭州市余杭区": "e88a6346ce0f1bc6e3f8f95c415efa24",
            "2022年第一季度湖南省长沙市长沙县": "83ca2d4aec26e0b57f0dc36136a6a737",
            "2022年第二季度湖南省长沙市长沙县": "e100514f4b5af98381a7d3371d87473a",
            "2022年第三季度湖南省长沙市长沙县": "4aa3f1debab04db7f4e0d6c891ea9303",
            "2022年第四季度湖南省长沙市长沙县": "502323e131d58a17ca033994add011ee",
            "2022年第一季度广东省深圳市龙华区": "85c4f3d79cf95db988e91ee631a0f0b0",
            "2022年第二季度广东省深圳市龙华区": "75c35672c7804138e417dea9b43e5c31",
            "2022年第三季度广东省深圳市龙华区": "fd43ba6a4aa355ab720522faef32b971",
            "2022年第四季度广东省深圳市龙华区": "d6b26d770614da7fb2a52077dff95f42",
        }
        self.mkNames = list(self.mks.keys())

        self.slm = QStringListModel()
        self.slm.setStringList(self.mkNames)
        self.listView.setModel(self.slm)
        self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView.setCurrentIndex(self.slm.index(0,0))
        

    def connectFunc(self):
        self.intoWeb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.jl1mall.com/rskit/MyRSservices")))
        self.runPB.clicked.connect(self.runPBClicked)

    def runPBClicked(self):
        validTk = self.tkLE.text().strip()
        modelIndex = self.listView.currentIndex()
        currentMk = self.mks[ self.mkNames[modelIndex.row()] ]
        self.wmsPath = "https://api.jl1mall.com/getMap/{z}/{x}/{-y}?mk=" + currentMk + "&tk=" + validTk
        self.layerName = self.mkNames[modelIndex.row()]

        if validTk != "" :
            self.setting.changeSetting("freeTk",validTk)
        
        self.close()