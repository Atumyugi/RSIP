
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import os.path as osp
import sys
from datetime import datetime
import subprocess
import traceback
from appConfig import yoyiSetting,PROJECT_STYLE_XML,TEMP_DIR,ROOT_PATH,UPDATE_APP_NEW,UPDATE_APP

mainFilePath = osp.abspath(__file__)

os.environ['PROJ_LIB'] = osp.join(osp.dirname(mainFilePath),"share","proj")
os.environ['GDAL_DATA'] = osp.join(osp.dirname(mainFilePath),"share","gdal")

TEMPBaseName = f"TEMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
TMPBaseName = f"TMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
from yoyiUtils.yoyiFile import createDir,deleteDir
from yoyiUtils.yoyiLogging import yoyiLog
createDir(osp.join(TEMP_DIR,TEMPBaseName))
createDir(osp.join(TEMP_DIR,TMPBaseName))

logPath = osp.join(TEMP_DIR,f"log_{datetime.now().strftime('%Y-%m')}.txt")
logWritter = yoyiLog(logPath)

os.environ['TEMP'] = osp.join(TEMP_DIR,TEMPBaseName)
os.environ['TMP'] = osp.join(TEMP_DIR,TMPBaseName)
os.environ['KMP_DUPLICATE_LIB_OK']='TRUE'
os.environ['PATH'] = f"{osp.join(osp.dirname(mainFilePath), 'Lib')};" + os.environ['PATH']

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from qfluentwidgets import setThemeColor

QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
from qgis.core import QgsApplication,QgsStyle,QgsSettings
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
        
        from yoyiSplash import YoyiSplashScreen
        splash = YoyiSplashScreen(mode="common")
        splash.setInfo("Loading 10% ......")
        splash.show()

        # plugin  
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

        app.setPrefixPath(osp.join(osp.dirname(__file__), "Lib"),True)

        app.setApplicationDisplayName("RSDM")
        app.setApplicationName("RSDM")
        app.setOrganizationName("RSDM")
        app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
        print("app.qgisSettingsDirPath",app.qgisSettingsDirPath())
        app.initQgis()

        splash.setInfo("Loading 40% ......")
        from widgets import mainWidget

        settings = QgsSettings()
        settings.setValue("qgis/enable_render_caching",True)
        settings.setValue("qgis/parallel_rendering", True)
        settings.setValue("qgis/max_threads",8)
        settings.sync()

        qstyles = QgsStyle.defaultStyle()
        qstyles.importXml(PROJECT_STYLE_XML)

        from qgis.analysis import QgsNativeAlgorithms

        splash.setInfo("Loading 70% ......")

        from processing.core.Processing import Processing # type: ignore
        Processing.initialize()
        from qgis import processing
        app.processingRegistry().addProvider(QgsNativeAlgorithms())

        splash.setInfo("Loading 90% ......")

        localProjectDir = yoyiSetting().configSettingReader.value('localProject',type=str)
        createDir(localProjectDir)
        createDir(osp.join(localProjectDir,"segment"))
        createDir(osp.join(localProjectDir, "changeDetection"))
        createDir(osp.join(localProjectDir,"homeProject"))

        windowColor = yoyiSetting().configSettingReader.value('windowColor',type=str)
        setThemeColor(windowColor)

        isDark = yoyiSetting().configSettingReader.value('windowStyle', type=int)

        mainWindow = mainWidget.MainWindow(app=app,TEMPBaseName=TEMPBaseName,mode='cpu',logWritter=logWritter,extraFile=extraFile)
        mainWindow.initLocalAction()
        mainWindow.changeWindowLanguage()
        mainWindow.changeWindowStyle(isDark=isDark)
        splash.finish(mainWindow)
        mainWindow.showMaximized()
        mainWindow.activateWindow()
        mainWindow.changeWindowStyle(isDark=isDark)
        splash.deleteLater()
        app.exec_()
        
        app.exitQgis()
        
        deleteDir(osp.join(TEMP_DIR,TEMPBaseName))
        deleteDir(osp.join(TEMP_DIR,TMPBaseName))

        pid = os.getpid()
        os.kill(pid,9)
    except Exception as e:
        print(traceback.format_exc())
        logWritter.write(traceback.format_exc())

