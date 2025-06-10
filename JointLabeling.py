import os
import os.path as osp
import sys
import traceback
from datetime import datetime
from appConfig import yoyiSetting,ROOT_PATH,PROJECT_STYLE_XML,TEMP_DIR,ROLE_CODE_DICT,SEX_DICT
from yoyiUtils.yoyiFile import createDir,deleteDir
from yoyiUtils.yoyiLogging import yoyiLog
from yoyiUtils.yoyiTranslate import yoyiTrans
mainFilePath = osp.abspath(__file__)

os.environ['PROJ_LIB'] = osp.join(osp.dirname(mainFilePath),"share","proj")
os.environ['GDAL_DATA'] = osp.join(osp.dirname(mainFilePath),"share","gdal")


TEMPBaseName = f"TEMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
TMPBaseName = f"TMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
createDir(osp.join(TEMP_DIR,TEMPBaseName))
createDir(osp.join(TEMP_DIR,TMPBaseName))

logPath = osp.join(TEMP_DIR,f"jointLabeling_{datetime.now().strftime('%Y-%m')}.txt")
logWritter = yoyiLog(logPath)

os.environ['TEMP'] = osp.join(TEMP_DIR,TEMPBaseName)
os.environ['TMP'] = osp.join(TEMP_DIR,TMPBaseName)
os.environ['KMP_DUPLICATE_LIB_OK']='TRUE'
os.environ['PATH'] = f"{osp.join(osp.dirname(mainFilePath), 'Lib')};" + os.environ['PATH']

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt,QProcess

QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
from qgis.core import QgsApplication,QgsProcessingFeedback,QgsStyle,QgsSettings
app = QgsApplication([], True)
import yoyirs_rc

if __name__ == '__main__':
    try:
        sysList = sys.argv
        if len(sysList) >= 2:
            extraFile = sysList[1]
            print(sysList)
        else:
            extraFile = None
        
        from widgets.loginWidget import LoginWidgetClass
        loginDialog = LoginWidgetClass()
        loginDialog.exec()
        closeUpdate = False
        if loginDialog.loginStatus >= 0:
            status = loginDialog.loginStatus
            userName = loginDialog.user
            password = loginDialog.pswd
            userInfo = loginDialog.resultDict
            from yoyiSplash import YoyiSplashScreen
            splash = YoyiSplashScreen()
            splash.setInfo("Loading 10% ......")
            splash.show()

            # plugin  中间的import都不能注释删除，打包时有用
            from qgis.utils import *
            import multiprocessing
            import uuid
            import logging
            from PyQt5 import uic
            from PyQt5 import sip
            from PyQt5 import QtXml
            from PyQt5 import Qsci
            import psycopg2
            from concurrent.futures import ThreadPoolExecutor
            import shutil
            from affine import Affine
            # plugin end

            splash.setInfo("Loading 20% ......")

            APP_PATH = osp.dirname(__file__)
            from PyQt5.QtCore import QTranslator

            app.setPrefixPath(osp.join(osp.dirname(__file__), "Lib"),True)
            app.setApplicationDisplayName("RSDM")
            app.setApplicationName("RSDM")
            app.setOrganizationName("RSDM")
            app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

            print("app.qgisSettingsDirPath",app.qgisSettingsDirPath())

            app.initQgis()
            
            settings = QgsSettings()
            settings.setValue("qgis/enable_render_caching",True)
            settings.setValue("qgis/parallel_rendering", True)
            settings.setValue("qgis/max_threads",8)
            settings.sync()

            qstyles = QgsStyle.defaultStyle()
            qstyles.importXml(PROJECT_STYLE_XML)

            splash.setInfo("Loading 30% ......")
            from PyQt5.QtCore import QUrl,QPoint
            from PyQt5.QtGui import QIcon, QDesktopServices,QColor,QCursor
            from qfluentwidgets import (NavigationItemPosition, MessageBox, MSFluentWindow, 
                setThemeColor,setTheme, Theme,RoundMenu,Action,MenuAnimationType)
            from qfluentwidgets import FluentIcon as FIF
            from yoyiUtils.custom_widget import AvatarTextWidget
            splash.setInfo("Loading 40% ......")
            from widgets.settingWidget import SettingWidgetWindowClass
            from widgets.drawWidget import JointWorkWindowClass
            
            class MainWindow(MSFluentWindow):
                def __init__(self,loginStatus,userName,password,userInfo,logWritter=None,extraFile=None):
                    super().__init__()

                    self.loginStatus = loginStatus
                    self.userName = userName
                    self.password = password
                    self.userId = userInfo['id']
                    self.userRealname = userInfo['realname']
                    self.userBirthday = userInfo['birthday']
                    self.userSex = userInfo['sex']
                    self.userPhone = userInfo['phone']
                    self.userRoleCode = userInfo['roleCode']
                    
                    self.old_hook = sys.excepthook
                    sys.excepthook = self.catch_exceptions

                    self.logWritter = logWritter

                    self.TEMPDIR = osp.join(TEMP_DIR,TEMPBaseName)

                    self.closeUpdate = False

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

                    self.webDrawInterface = JointWorkWindowClass(self)
                    self.webDrawInterface.setObjectName("webDrawWindowObj")

                    self.settingInterface = SettingWidgetWindowClass(self)
                    self.settingInterface.setObjectName("settingWindowObj")

                def initLocalAction(self):
                    self.initLocalNavigation()
                    self.initWindow(local=True)

                def changeWindowStyle(self,isDark=True):
                    if isDark:
                        setTheme(Theme.DARK)
                        BGCOLOR = yoyiSetting().configSettingReader.value('darkBgColor', type=tuple)
                        FontColor = "rgb(254, 254, 254)"
                        LayerBgColor = "rgb(62, 62, 62)"
                        with open(osp.join(ROOT_PATH,"qss","dark.qss"), encoding='utf-8') as f:
                            self.setStyleSheet(f.read())
                        self.webDrawInterface.dockWidget.setStyleSheet('color: white;')
                        self.webDrawInterface.dockWidget_left.setStyleSheet('color: white;')
                        self.webDrawInterface.dockWidget_leftDown.setStyleSheet('color: white;')
                        self.webDrawInterface.dockWidgetTop.setStyleSheet('color: white;')
                    else:
                        setTheme(Theme.LIGHT)
                        BGCOLOR = yoyiSetting().configSettingReader.value('lightBgColor', type=tuple)
                        FontColor = "rgb(32, 32, 32)"
                        LayerBgColor = "rgb(254, 254, 254)"
                        with open(osp.join(ROOT_PATH,"qss","light.qss"), encoding='utf-8') as f:
                            self.setStyleSheet(f.read())
                        self.webDrawInterface.dockWidget.setStyleSheet('color: black;')
                        self.webDrawInterface.dockWidget_left.setStyleSheet('color: black;')
                        self.webDrawInterface.dockWidget_leftDown.setStyleSheet('color: black;')
                        self.webDrawInterface.dockWidgetTop.setStyleSheet('color: black;')
                        
                    self.webDrawInterface.spMapCanvas.setCanvasColor(QColor(BGCOLOR[0], BGCOLOR[1], BGCOLOR[2]))
                    self.webDrawInterface.rightMapCanvas.setCanvasColor(QColor(BGCOLOR[0], BGCOLOR[1], BGCOLOR[2]))
                    self.webDrawInterface.layerTree.layerTreeView.setStyleSheet(f"background-color: {LayerBgColor}; font-size: 10pt; color: {FontColor}; QTreeView::item {{color: {FontColor}; }}")

                def changeWindowLanguage(self):
                    language = yoyiSetting().configSettingReader.value('appLanguage',type=str)
                    print(language)
                    if language == "Ch":
                        self.yoyiTrans = yoyiTrans(language)
                        app.installTranslator(self.tsTrans)
                    else:
                        language = "En"
                        self.yoyiTrans = yoyiTrans(language)
                        app.removeTranslator(self.tsTrans)

                    self.settingInterface.retranslateUi(self)
                    self.settingInterface.retranslateDiyUI()
                    self.webDrawInterface.retranslateDiyUI()

                    webDrawW = self.navigationInterface.widget("webDrawWindowObj")
                    webDrawW.setText(self.yoyiTrans._translate("协同勾画"))

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
                    traceback_format = traceback.format_exception(ty, value, trace)
                    traceback_string = "".join(traceback_format)
                    print(traceback_string)
                    MessageBox(self.yoyiTrans._translate("错误"), self.yoyiTrans._translate("未知错误"), self).exec()
                    self.old_hook(ty, value, trace)
                    if self.logWritter:
                        self.logWritter.write(traceback_string)

                def closeEvent(self, e):
                    if self.closeUpdate:
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

                def initLocalNavigation(self):

                    self.addSubInterface(self.webDrawInterface,FIF.WIFI,'协同勾画')
                    
                    self.navigationInterface.addWidget(
                        routeKey='avatarWindowObj',
                        widget=AvatarTextWidget(self.userRealname),
                        position=NavigationItemPosition.BOTTOM,
                        onClick=self.avatarMenuClicked
                    )

                    self.addSubInterface(self.settingInterface,FIF.SETTING,'设置', FIF.SETTING, NavigationItemPosition.BOTTOM)

                    self.navigationInterface.addItem(
                        routeKey='AboutWindowObj',
                        icon=FIF.INFO,
                        text=self.yoyiTrans._translate("关于"),
                        onClick=self.showAboutMessageBox,
                        selectable=False,
                        position=NavigationItemPosition.BOTTOM,
                    )

                    self.navigationInterface.setCurrentItem(self.webDrawInterface.objectName())

                def avatarMenuClicked(self):
                    cusMenu = RoundMenu(parent=self)
                    cusMenu.setItemHeight(50)

                    userNameAction = Action(FIF.GLOBE, f"{self.yoyiTrans._translate('账号')}: {self.userName}")
                    cusMenu.addAction(userNameAction)

                    userLVAction = Action(FIF.TAG, f"{self.yoyiTrans._translate('账号角色')}: {ROLE_CODE_DICT[self.userRoleCode] if self.userRoleCode in ROLE_CODE_DICT.keys() else self.userRoleCode}")
                    cusMenu.addAction(userLVAction)

                    nameAction = Action(FIF.CLOUD, f"{self.yoyiTrans._translate('姓名')}: {self.userRealname}")
                    cusMenu.addAction(nameAction)

                    birthdayAction = Action(FIF.DATE_TIME,f"{self.yoyiTrans._translate('生日')}: {self.userBirthday}")
                    cusMenu.addAction(birthdayAction)

                    sexAction = Action(FIF.PEOPLE,f"{self.yoyiTrans._translate('性别')}: {SEX_DICT[self.userSex] if self.userSex in SEX_DICT.keys() else self.userSex}")
                    cusMenu.addAction(sexAction)

                    phoneAction = Action(FIF.PHONE,f"{self.yoyiTrans._translate('电话')}: {self.userPhone}")
                    cusMenu.addAction(phoneAction)

                    # editPasswordAction = Action(FIF.EDIT,f"{self.yoyiTrans._translate('修改密码')}")
                    # cusMenu.addAction(editPasswordAction)

                    curPos : QPoint = QCursor.pos()
                    cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)

                def initWindow(self,local=False):
                    width = yoyiSetting().configSettingReader.value('width',type=int)
                    height = yoyiSetting().configSettingReader.value('height',type=int)
                    self.resize(width, height)
                    self.setWindowIcon(QIcon(':/img/resources/CGlogo.ico'))

                    desktop = QApplication.desktop().availableGeometry()
                    w, h = desktop.width(), desktop.height()
                    self.move(w//2 - self.width()//2, h//2 - self.height()//2)

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

            splash.setInfo("Loading 90% ......")

            localProjectDir = yoyiSetting().configSettingReader.value('localProject',type=str)
            createDir(localProjectDir)
            createDir(osp.join(localProjectDir,"segment"))
            createDir(osp.join(localProjectDir, "changeDetection"))
            createDir(osp.join(localProjectDir,"homeProject"))

            windowColor = yoyiSetting().configSettingReader.value('windowColor',type=str)
            setThemeColor(windowColor)

            isDark = yoyiSetting().configSettingReader.value('windowStyle', type=int)

            mainWindow = MainWindow(loginStatus=status,userName=userName,password=password,userInfo=userInfo,logWritter=logWritter,extraFile=extraFile)
            mainWindow.initLocalAction()
            mainWindow.changeWindowLanguage()
            mainWindow.changeWindowStyle(isDark=isDark)
            splash.finish(mainWindow)
            mainWindow.showMaximized()
            mainWindow.activateWindow()
            mainWindow.raise_()
            mainWindow.changeWindowStyle(isDark=isDark)
            splash.deleteLater()
            app.exec_()
            print("closeUpdate:",mainWindow.closeUpdate)

            closeUpdate = mainWindow.closeUpdate
        
        app.exitQgis()
        deleteDir(osp.join(TEMP_DIR,TEMPBaseName))
        deleteDir(osp.join(TEMP_DIR,TMPBaseName))

        if closeUpdate:
            os.startfile(osp.join(ROOT_PATH,"点我自动更新.exe"))
        pid = os.getpid()
        os.kill(pid,9)
    except Exception as e:
        logWritter.write(traceback.format_exc())
