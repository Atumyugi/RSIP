
from PyQt5.QtWidgets import QFileDialog
from qfluentwidgets import MessageBox


class qtTriggeredCommonDialog:
    def __init__(self):
        self.postDict = {
            "tif": "GeoTIFF(*.tif;*.tiff;*.TIF;*.TIFF;*.png;*.PNG;*.jpg;*.JPG;*.jpeg)",
            "shp": "ShapeFile(*.shp;*SHP)",
            "txt": "Txt(*.txt)",
            "pth": "pth(*.pth)",
            "py": "py(*.py)",
            "yaml": "yaml(*.yaml)",
            "cgpth": "cgpth(*.cgpth)",
            "excel" : "Excel(*.xlsx)",
            "extraShapeFile" : "ShapeFile(*.shp;*SHP);;GPKG(*.gpkg);;GeoJSON(*.geojson)"
        }

    def addFileOrFileDirTriggered(self,lineEdit,filterType='tif',parent=None,lineEditType="LineEdit"):
        w = MessageBox(
            '提示',
            '选择文件还是文件夹？',
            parent
        )
        w.yesButton.setText('选择文件')
        w.cancelButton.setText('选择文件夹')
        if w.exec():
            file, ext = QFileDialog.getOpenFileName(parent, "选择文件", "", self.postDict[filterType])
            if file:
                if lineEditType == "LineEdit":
                    lineEdit.setText(file)
                elif lineEditType == "ComboBox":
                    lineEdit.insertItem(0,file)
                    lineEdit.setCurrentIndex(0)
        else:
            fileDir = QFileDialog.getExistingDirectory(parent, "选择文件夹", "")
            if fileDir:
                if lineEditType == "LineEdit":
                    lineEdit.setText(fileDir)
                elif lineEditType == "ComboBox":
                    lineEdit.insertItem(0,fileDir)
                    lineEdit.setCurrentIndex(0)

    def addFileTriggered(self,lineEdit,filterType='tif',preDir="",parent=None):
        file, ext = QFileDialog.getOpenFileName(parent, "选择文件", preDir, self.postDict[filterType])
        if file:
            lineEdit.setText(file)

    def addFileDirTriggered(self,lineEdit,preDir=None,parent=None,lineEditType="LineEdit"):
        if preDir:
            fileDir = QFileDialog.getExistingDirectory(parent, "选择文件夹", preDir)
        else:
            fileDir = QFileDialog.getExistingDirectory(parent, "选择文件夹", "")
        if fileDir:
            if lineEditType == "LineEdit":
                lineEdit.setText(fileDir)
            elif lineEditType == "ComboBox":
                lineEdit.insertItem(0,fileDir)
                lineEdit.setCurrentIndex(0)

    def selectSaveFileTriggered(self,lineEdit,filterType='tif',preName="",parent=None):
        file, ext = QFileDialog.getSaveFileName(parent, "保存文件",preName,self.postDict[filterType])
        if file:
            lineEdit.setText(file)