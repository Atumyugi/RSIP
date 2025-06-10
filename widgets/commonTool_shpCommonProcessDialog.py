import sys
import os
import os.path as osp
import shutil

from ui.shp_process_dialog.shpCommonProcessDialog import Ui_shpCommonProcessDialog

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout

from qgis.core import QgsProject,QgsMapLayer,QgsLayerTree,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.qgisFunction import shpCommonProcess

PROJECT = QgsProject.instance()

class ShpCommonProcessDialogClass(Ui_shpCommonProcessDialog,QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.connectFunc()
    
    def connectFunc(self):
        self.inputFile_ToolButton.clicked.connect(
            lambda: qtTriggeredCommonDialog().addFileTriggered(
                self.inputFile_LineEdit,'shp',parent=self
            )
        )
        self.outputFile_ToolButton.clicked.connect(
            lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(
                self.outputFile_LineEdit,'shp',parent=self
            )
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.close)
        
    def accept(self):
        inputFilePath = self.inputFile_LineEdit.text()
        outputFilePath = self.outputFile_LineEdit.text()
        tolerance = float(self.tolerance_LineEdit.text())
        minHoleArea = float(self.minHoleArea_LineEdit.text())
        removeArea = float(self.removeArea_LineEdit.text())
        
        # 清理tmp文件夹
        tmp_folder = "./tmp"
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder) #递归删除文件夹
        
        if not os.path.exists(tmp_folder):
            os.mkdir(tmp_folder)
            
        print(inputFilePath)
        print(outputFilePath)
        print(tolerance)
        print(minHoleArea)
        print(removeArea)
        shpCommonProcess(inputFilePath, outputFilePath, tmp_folder, tolerance, minHoleArea, removeArea, callback=print)
        