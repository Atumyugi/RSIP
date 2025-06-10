import os
import os.path as osp

from PyQt5.QtCore import Qt
from qfluentwidgets import StateToolTip,InfoBar,InfoBarPosition

from yoyiUtils.yoyiTranslate import yoyiTrans

class YoyiStateToolTip(StateToolTip):
    def __init__(self, title, content,yoyiTrs, parent=None,finishAddLayer=True):
        super().__init__(title,content,parent)
        self.closeButton.hide()
        self.parentWindow = parent
        self.yoyiTrs:yoyiTrans = yoyiTrs
        self.finishAddLayer = finishAddLayer

    def changeStateProcess(self,process):
        self.setContent(f"{self.yoyiTrs._translate('运行中')} {self.yoyiTrs._translate('进度')} : {process:.2f}%")

    def stateEnd(self,resInfo:str):
        print(resInfo)
        self.closeTip()
        if osp.exists(resInfo):
            InfoBar.success(
                title=f"{self.title} {self.yoyiTrs._translate('运行结束')}",
                content=f"{self.yoyiTrs._translate('结果路径')} {resInfo}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                # position='Custom',   # NOTE: use custom info bar manager
                duration=10000,
                parent=self.parent()
            )
            if self.finishAddLayer:
                if osp.basename(resInfo).split(".")[-1] == "shp":
                    self.parentWindow.addVectorLayer(resInfo)
                elif osp.basename(resInfo).split(".")[-1] == "tif":
                    self.parentWindow.addRasterLayer(resInfo)
            else:
                self.parentWindow.mapCanvas.refreshAllLayers()
        else:
            InfoBar.error(
                title=f"{self.title} {self.yoyiTrs._translate('运行错误')}",
                content=resInfo[:100],
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=10000,
                parent=self.parent()
            )

    def closeTip(self):
        self.closedSignal.emit()
        self.close()

