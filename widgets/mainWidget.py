

import sys
import os
import os.path as osp
import atexit
from datetime import datetime
import traceback
from appConfig import *
from yoyiUtils.yoyiFile import createDir,deleteDir
from yoyiUtils.yoyiTranslate import yoyiTrans

from PyQt5.QtCore import QUrl,QRect,QPoint,QTranslator
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QDesktopServices,QColor,QCursor

from qfluentwidgets import (NavigationItemPosition,NavigationAvatarWidget, MessageBox, MSFluentWindow, SubtitleLabel, 
    setFont,setThemeColor,setTheme, Theme,NavigationWidget,isDarkTheme,RoundMenu,Action,MenuAnimationType)
from qfluentwidgets import FluentIcon as FIF
from yoyiUtils.custom_widget import AvatarTextWidget
from widgets.homeLocalWidget import HomeLocalWindowClass
from widgets.drawWidget_SegmentLocal import DrawWidgetSegmentLocalWindowClass
from widgets.drawWidget_ChangeDetectionLocal import DrawWidgetCdLocalWindowClass
from widgets.settingWidget import SettingWidgetWindowClass

class MainWindow(MSFluentWindow):
        def __init__(self,app,TEMPBaseName,mode,logWritter=None,extraFile=None):
            super().__init__()
            self.app = app
            self.mode = mode
            self.old_hook = sys.excepthook
            sys.excepthook = self.catch_exceptions

            self.logWritter = logWritter
            self.TEMPDIR = osp.join(TEMP_DIR,TEMPBaseName)

            self.tsTrans = QTranslator()
            self.tsTrans.load(r'.\Ch.qm')
            language = yoyiSetting().configSettingReader.value('appLanguage',type=str)
            print(language)
            if language == "Ch":
                self.yoyiTrans = yoyiTrans(language)
                app.installTranslator(self.tsTrans) 
            else:
                language = "En"
                self.yoyiTrans = yoyiTrans(language)
                app.removeTranslator(self.tsTrans)
            
            #sam
            if GPUENABLE:
                from mobile_sam import sam_model_registry,SamPredictor,SamAutomaticMaskGenerator
                import numpy as np
                if torch.cuda.device_count() > 0:
                    device = f"cuda:{0}"
                else:
                    device = "cpu"
                sam = sam_model_registry["vit_t"](checkpoint=SAM_MOBILE_PTH)
                sam.to(device)
                sam.eval()
                self.predictor = SamPredictor(sam)
                self.predictor.set_image(np.ones((512,512,3),dtype=np.uint8))
                self.maskGenerator = SamAutomaticMaskGenerator(sam,points_per_side=16,points_per_batch=64)
            else:
                self.predictor = None
                self.maskGenerator = None
            
            self.closeUpdate = False
            
            self.homeInterface = HomeLocalWindowClass(self,extraFile,mode=self.mode)
            self.homeInterface.setObjectName("homeWindowObj")
            
            self.segDrawInterface = DrawWidgetSegmentLocalWindowClass(self)
            self.segDrawInterface.setObjectName("segDrawWindowObj")

            self.cdDrawInterface = DrawWidgetCdLocalWindowClass(self)
            self.cdDrawInterface.setObjectName("cdDrawWindowObj")

            self.settingInterface = SettingWidgetWindowClass(self,mode=self.mode)
            self.settingInterface.setObjectName("settingWindowObj")

        def initLocalAction(self):
            self.initLocalNavigation()
            self.initWindow(local=True)

        def changeWindowStyle(self,isDark=True):
            if isDark:
                setTheme(Theme.DARK)
                BGCOLOR = yoyiSetting().configSettingReader.value('darkBgColor', type=tuple)
                FontColor = "rgb(254, 254, 254)"
                with open(osp.join(ROOT_PATH,"qss","dark.qss"), encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                self.segDrawInterface.dockWidget_left.setStyleSheet('color: white;')
                self.cdDrawInterface.dockWidget_left.setStyleSheet('color: white;')
            else:
                setTheme(Theme.LIGHT)
                BGCOLOR = yoyiSetting().configSettingReader.value('lightBgColor', type=tuple)
                FontColor = "rgb(32, 32, 32)"
                with open(osp.join(ROOT_PATH,"qss","light.qss"), encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                self.segDrawInterface.dockWidget_left.setStyleSheet('color: black;')
                self.cdDrawInterface.dockWidget_left.setStyleSheet('color: black;')

            self.homeInterface.mapCanvas.setCanvasColor(QColor(BGCOLOR[0], BGCOLOR[1], BGCOLOR[2]))
            self.homeInterface.layerTreeView.setStyleSheet(f"background-color: rgb({BGCOLOR[0]}, {BGCOLOR[1]}, {BGCOLOR[2]}); font-size: 10pt; color: {FontColor}")
            self.segDrawInterface.spMapCanvas.setCanvasColor(QColor(BGCOLOR[0], BGCOLOR[1], BGCOLOR[2]))
            self.cdDrawInterface.spMapCanvas.setCanvasColor(QColor(BGCOLOR[0], BGCOLOR[1], BGCOLOR[2]))
            self.cdDrawInterface.rightMapCanvas.setCanvasColor(QColor(BGCOLOR[0], BGCOLOR[1], BGCOLOR[2]))

        def changeWindowLanguage(self):
            language = yoyiSetting().configSettingReader.value('appLanguage',type=str)
            print(language)
            if language == "Ch":
                self.yoyiTrans = yoyiTrans(language)
                self.app.installTranslator(self.tsTrans)
            else:
                language = "En"
                self.yoyiTrans = yoyiTrans(language)
                self.app.removeTranslator(self.tsTrans)

            self.homeInterface.retranslateUi(self)
            self.homeInterface.retranslateDiyUI()
            self.settingInterface.retranslateUi(self)
            self.settingInterface.retranslateDiyUI()
            self.segDrawInterface.retranslateUi(self)
            self.segDrawInterface.retranslateDiyUI()
            self.cdDrawInterface.retranslateUi(self)
            self.cdDrawInterface.retranslateDiyUI()

            homeW = self.navigationInterface.widget("homeWindowObj")
            homeW.setText(self.yoyiTrans._translate("主页"))

            segDrawW = self.navigationInterface.widget("segDrawWindowObj")
            segDrawW.setText(self.yoyiTrans._translate("单景标注"))

            cdDrawW = self.navigationInterface.widget("cdDrawWindowObj")
            cdDrawW.setText(self.yoyiTrans._translate("变化标注"))

            jointDraw = self.navigationInterface.widget("JointLabelingObj")
            jointDraw.setText(self.yoyiTrans._translate("协同标注"))

            aboutW = self.navigationInterface.widget("AboutWindowObj")
            aboutW.setText(self.yoyiTrans._translate("关于"))

            settingW = self.navigationInterface.widget("settingWindowObj")
            settingW.setText(self.yoyiTrans._translate("设置"))

            self.setWindowTitle(f'{self.yoyiTrans._translate("吉林一号遥感解译平台")} -- {self.yoyiTrans._translate("无标题")}')

        def catch_exceptions(self, ty, value, trace):
            """
            捕获异常，并弹窗显示
            :param ty: 异常的类型
            :param value: 异常的对象
            :param traceback: 异常的traceback
            """
            traceback_format = traceback.format_exception(ty, value, trace,limit=500)
            traceback_string = "".join(traceback_format)
            print(traceback_string)
            MessageBox(self.yoyiTrans._translate("错误"), self.yoyiTrans._translate("未知错误"), self).exec()
            self.old_hook(ty, value, trace)
            if self.logWritter:
                self.logWritter.write(traceback_string)

        def closeEvent(self, e):
            if self.closeUpdate:
                self.homeInterface.deleteChildDialog()
                e.accept()
            else:
                reply = MessageBox(
                    self.yoyiTrans._translate("退出"),
                    self.yoyiTrans._translate("确定要退出吗？"),
                    self
                )
                reply.yesButton.setText(self.yoyiTrans._translate("退出"))
                reply.cancelButton.setText(self.yoyiTrans._translate("取消"))
                if reply.exec():
                    self.homeInterface.deleteChildDialog()
                    e.accept()
                else:
                    e.ignore()
        
        def closeAppForUpdate(self):
            self.closeUpdate = True
            self.close()


        def resizeEvent(self, a0, QResizeEvent=None):
            super().resizeEvent(a0)
            yoyiSetting().changeSetting('width', self.width())
            yoyiSetting().changeSetting('height', self.height())

        def setCurrentStackWidget(self,widgetName):
            if widgetName == "segmentDraw":
                self.stackedWidget.setCurrentIndex( self.stackedWidget.indexOf(self.segDrawInterface) )
            elif widgetName == "cdDraw":
                self.stackedWidget.setCurrentIndex( self.stackedWidget.indexOf(self.cdDrawInterface))
            elif widgetName == "setting":
                self.stackedWidget.setCurrentIndex( self.stackedWidget.indexOf(self.settingInterface))

        def initLocalNavigation(self):

            self.addSubInterface(self.homeInterface, ':/img/resources/title/t1-home.png', '主页')
            self.addSubInterface(self.segDrawInterface, ':/img/resources/title/t2-singleLabeling.png', '单景标注')
            self.addSubInterface(self.cdDrawInterface, ':/img/resources/title/t3-cdLabeling.png', '变化标注')
            self.navigationInterface.addItem(
                routeKey='JointLabelingObj',
                icon=':/img/resources/title/t4-jointLabeling.png',
                text=self.yoyiTrans._translate("协同标注"),
                onClick=self.homeInterface.jointLabelingPbClicked,
                selectable=False,
            )

            #self.addSubInterface(self.settingInterface,FIF.SETTING,'设置', FIF.SETTING, NavigationItemPosition.BOTTOM)
            self.stackedWidget.addWidget(self.settingInterface)
            self.navigationInterface.addItem(
                routeKey='settingWindowObj',
                icon=FIF.SETTING,
                text=self.yoyiTrans._translate("设置"),
                onClick=self.showSettingWindow,
                selectable=True,
                position=NavigationItemPosition.BOTTOM,
            )
            self.navigationInterface.addItem(
                routeKey='AboutWindowObj',
                icon=FIF.INFO,
                text=self.yoyiTrans._translate("关于"),
                onClick=self.showAboutMessageBox,
                selectable=False,
                position=NavigationItemPosition.BOTTOM,
            )

            self.navigationInterface.setCurrentItem(self.homeInterface.objectName())

        def initWindow(self,local=False):
            width = yoyiSetting().configSettingReader.value('width',type=int)
            height = yoyiSetting().configSettingReader.value('height',type=int)
            self.resize(width, height)
            self.setWindowIcon(QIcon(':/img/resources/logo.png'))

            desktop = QApplication.desktop().availableGeometry()
            w, h = desktop.width(), desktop.height()
            self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        
        def showSettingWindow(self):
            self.settingInterface.refreshUI()
            self.stackedWidget.setCurrentIndex( self.stackedWidget.indexOf(self.settingInterface), popOut=False)

        def showAboutMessageBox(self):
            w = MessageBox(
                    self.yoyiTrans._translate("吉林一号遥感解译平台"),
                    f'{self.yoyiTrans._translate("吉林一号遥感解译平台")}，{self.yoyiTrans._translate("长光卫星技术股份有限公司")}',
                    self
                )
            w.yesButton.setText(self.yoyiTrans._translate("进入官网"))
            w.cancelButton.setText(self.yoyiTrans._translate("取消"))

            if w.exec():
                QDesktopServices.openUrl(QUrl("https://www.jl1mall.com"))