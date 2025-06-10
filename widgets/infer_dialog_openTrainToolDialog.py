import os
import os.path as osp
import subprocess
from ui.infer_dialog.openTrainToolDialog import Ui_openTrainToolDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
from qfluentwidgets import MessageBox
from yoyiUtils.yoyiTranslate import yoyiTrans
import torch
import appConfig

class OpenTrainToolDialogClass(Ui_openTrainToolDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

        # gpu
        for deviceId in range(torch.cuda.device_count()):
            self.selectGPUCb.addItem(torch.cuda.get_device_name(deviceId) + f"_{deviceId}",userData=deviceId)

    
    def connectFunc(self):
        self.startPb.clicked.connect(self.startPbClicked)
    
    def startPbClicked(self):
        
        # 一些状态判断
        if self.selectGPUCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate("没有可用GPU"), self).exec_()
            return

        gpuId = self.selectGPUCb.currentData()
        subprocess.Popen([appConfig.TRAIN_TOOL_CMD,f"{gpuId}"],creationflags=subprocess.DETACHED_PROCESS)

        self.close()

        

        

