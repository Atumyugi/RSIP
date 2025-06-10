# -*- coding: utf-8 -*-
# @Author  : yoyi
# @Time    : 2020/10/20 15:01
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow,QDialog, QHBoxLayout,QTableView,QVBoxLayout,QDesktopWidget,QMessageBox,QSizePolicy,QSpacerItem
from PyQt5.QtCore import QItemSelection,QItemSelectionModel,QPoint,QVariant,Qt,QCoreApplication
from PyQt5.QtGui import QCursor,QIntValidator,QIcon
from qgis.core import QgsVectorLayerCache,QgsVectorLayer,QgsField,QgsCoordinateTransform,QgsProject
from qgis.gui import QgsAttributeTableView, QgsAttributeTableModel, QgsAttributeTableFilterModel,QgsGui,QgsMapCanvas
from qfluentwidgets import RoundMenu,Action,MenuAnimationType,PushButton,ComboBox,LineEdit,MessageBox,\
    BodyLabel,ListWidget
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.yoyiTranslate import yoyiTrans

from appConfig import yoyiSetting

import yoyirs_rc

PROJECT = QgsProject.instance()

class NewFieldDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
    
        self.setWindowTitle("Create New Field")

        self.initMember()
        self.initUI()
        self.retranslateDiyUI()

        self.createFieldTypeCb.currentIndexChanged.connect(self.createFieldTypeCbChanged)

    def initMember(self):
        self.fieldName = None
        self.fieldLength = None
        self.fieldPrecision = None

    def initUI(self):
        vBoxLayout = QVBoxLayout(self)

        # 字段名称输入框
        fieldNameHLayout = QHBoxLayout(self)

        self.fieldNameLabel = BodyLabel("New field name",self)
        fieldNameHLayout.addWidget(self.fieldNameLabel)
        self.fieldNameLE = LineEdit(self)
        fieldNameHLayout.addWidget(self.fieldNameLE)

        vBoxLayout.addLayout(fieldNameHLayout)

        # 创建一个下拉框用于选择字段类型
        fieldTypeHLayout = QHBoxLayout(self)

        self.fieldTypeLabel = BodyLabel("Field type",self)
        fieldTypeHLayout.addWidget(self.fieldTypeLabel)
        self.createFieldTypeCb = ComboBox(self)
        
        fieldTypeHLayout.addWidget(self.createFieldTypeCb)

        vBoxLayout.addLayout(fieldTypeHLayout)

        # 添加一个输入框用于设置字段长度
        fieldLengthHLayout = QHBoxLayout(self)

        self.fieldLengthLabel = BodyLabel("Field length",self)
        fieldLengthHLayout.addWidget(self.fieldLengthLabel)
        self.fieldLengthLE = LineEdit(self)
        self.fieldLengthLE.setValidator(QIntValidator())
        fieldLengthHLayout.addWidget(self.fieldLengthLE)

        vBoxLayout.addLayout(fieldLengthHLayout)

        # 添加一个输入框用于设置字段精度
        fieldPrecisionHLayout = QHBoxLayout(self)
        
        self.fieldPrecisionLabel = BodyLabel("Field precision",self)
        fieldPrecisionHLayout.addWidget(self.fieldPrecisionLabel)
        self.fieldPrecisionLE = LineEdit(self)
        self.fieldPrecisionLE.setValidator(QIntValidator())
        self.fieldPrecisionLE.setEnabled(False)
        fieldPrecisionHLayout.addWidget(self.fieldPrecisionLE)
        
        vBoxLayout.addLayout(fieldPrecisionHLayout)

        # 按钮布局
        buttonHLayout = QHBoxLayout(self)

        self.okPb = PushButton("OK")
        self.okPb.clicked.connect(self.okPbClicked)
        buttonHLayout.addWidget(self.okPb)

        self.cancelPb = PushButton("Cancel")
        self.cancelPb.clicked.connect(self.reject)
        buttonHLayout.addWidget(self.cancelPb)

        vBoxLayout.addLayout(buttonHLayout)
    
    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("DIYDialog", "Create New Field"))
        self.fieldNameLabel.setText(_translate("DIYDialog", "New field name"))
        self.fieldTypeLabel.setText(_translate("DIYDialog", "Field type"))
        
        self.createFieldTypeCb.addItems([_translate("DIYDialog", "Int"),_translate("DIYDialog", "Float"),_translate("DIYDialog", "String")])

        self.fieldLengthLabel.setText(_translate("DIYDialog", "Field length"))
        self.fieldPrecisionLabel.setText(_translate("DIYDialog", "Field precision"))

        self.okPb.setText(_translate("DIYDialog", "OK"))
        self.cancelPb.setText(_translate("DIYDialog", "Cancel"))

    def createFieldTypeCbChanged(self,index:int):
        # ["整型", "浮点型", "字符串"]
        if index == 1: #浮点型
            self.fieldPrecisionLE.setEnabled(True)
        else:
            self.fieldPrecisionLE.setEnabled(False)

    def okPbClicked(self):
        fieldName = self.fieldNameLE.text().strip()
        if fieldName == "":
            MessageBox("警告","字段名为空",self).exec()
            return
        
        try:
            fieldLength = int(self.fieldLengthLE.text())
        except Exception as e:
            MessageBox("警告","字段长度输入非法",self).exec()
            return
        
        if fieldLength <= 0 or fieldLength > 10:
            MessageBox("警告","字段长度限制在1-10之间",self).exec()
            return
        
        if self.createFieldTypeCb.currentIndex() == 1:
            try:
                fieldPrecision = int(self.fieldPrecisionLE.text())
            except Exception as e:
                MessageBox("警告","字段精度输入非法",self).exec()
                return
            
            if fieldPrecision <= 0 or fieldPrecision > 10:
                MessageBox("警告","字段精度限制在1-10之间",self).exec()
                return
        else:
            fieldPrecision = 0
        
        self.fieldName = fieldName
        self.fieldLength = fieldLength
        self.fieldPrecision = fieldPrecision
        self.accept()


class DeleteFieldDialog(QDialog):
    def __init__(self,fieldNames, parent):
        super().__init__(parent)
    
        self.setWindowTitle("Delete Field")
        self.fieldNames = fieldNames

        self.initMember()
        self.initUI()
        self.retranslateDiyUI()
    
    def initMember(self):
        self.beRemoveFieldNames = [] 
    
    def initUI(self):
        vBoxLayout = QVBoxLayout(self)

        # 创建一个列表框显示现有字段
        self.listWidget = ListWidget(self)
        for fieldName in self.fieldNames:
            self.listWidget.addItem(fieldName)
        self.listWidget.setSelectionMode(ListWidget.SelectionMode.MultiSelection)
        vBoxLayout.addWidget(self.listWidget)

        # 按钮布局
        buttonHLayout = QHBoxLayout(self)

        self.okPb = PushButton("OK")
        self.okPb.clicked.connect(self.okPbClicked)
        buttonHLayout.addWidget(self.okPb)

        self.cancelPb = PushButton("Cancel")
        self.cancelPb.clicked.connect(self.reject)
        buttonHLayout.addWidget(self.cancelPb)

        vBoxLayout.addLayout(buttonHLayout)
    
    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("DIYDialog", "Delete Field"))
        self.okPb.setText(_translate("DIYDialog", "OK"))
        self.cancelPb.setText(_translate("DIYDialog", "Cancel"))

    
    def okPbClicked(self):
        selectedItems = self.listWidget.selectedItems()
        if len(selectedItems) == 0:
            MessageBox("警告","选择为空",self).exec()
            return
        
        self.beRemoveFieldNames = []
        for item in selectedItems:
            self.beRemoveFieldNames.append(item.text())
        
        self.accept()

class RenameFieldDialog(QDialog):
    def __init__(self,fieldNames, parent):
        super().__init__(parent)
    
        self.setWindowTitle("重命名字段")
        self.fieldNames = fieldNames

        self.initMember()
        self.initUI()
        self.retranslateDiyUI()
       
    def initMember(self):
        self.beRenamedFieldName = None
        self.newFieldName = None
    
    def initUI(self):
        vBoxLayout = QVBoxLayout(self)

        # 创建一个列表框显示现有字段
        self.listWidget = ListWidget(self)
        for fieldName in self.fieldNames:
            self.listWidget.addItem(fieldName)
        self.listWidget.setSelectionMode(ListWidget.SelectionMode.SingleSelection)
        vBoxLayout.addWidget(self.listWidget)

        # 输入字段名的控件
        newFieldLayout = QHBoxLayout(self)
        self.newFieldNameLabel = BodyLabel("新字段名：",self)
        newFieldLayout.addWidget(self.newFieldNameLabel)
        self.newFieldNameLE = LineEdit(self)
        self.newFieldNameLE.setMaxLength(10)
        newFieldLayout.addWidget(self.newFieldNameLE)
        vBoxLayout.addLayout(newFieldLayout)

        # ok cancel
        buttonHLayout = QHBoxLayout(self)

        self.okPb = PushButton("OK")
        self.okPb.clicked.connect(self.okPbClicked)
        buttonHLayout.addWidget(self.okPb)

        self.cancelPb = PushButton("Cancel")
        self.cancelPb.clicked.connect(self.reject)
        buttonHLayout.addWidget(self.cancelPb)

        vBoxLayout.addLayout(buttonHLayout)
    
    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate
        self.okPb.setText(_translate("DIYDialog", "OK"))
        self.cancelPb.setText(_translate("DIYDialog", "Cancel"))
    
    def okPbClicked(self):
        selectedItems = self.listWidget.selectedItems()
        if len(selectedItems) == 0:
            MessageBox("警告","选择为空",self).exec()
            return
        
        if self.newFieldNameLE.text().strip() == "":
            MessageBox("警告","新字段名为空",self).exec()
            return
        
        self.beRenamedFieldName = selectedItems[0].text()
        self.newFieldName = self.newFieldNameLE.text().strip()
        self.accept()


class AttributeDialog(QDialog):
    def __init__(self, parent,mapCanvas,layer,extraMapcanvas=None):
        #mainWindows : MainWindow
        super(AttributeDialog, self).__init__(parent)

        self.mapCanvas : QgsMapCanvas = mapCanvas
        self.layer : QgsVectorLayer = layer
        self.extraMapcanvas = extraMapcanvas
        self.setObjectName("attrWidget"+self.layer.id())
        self.setWindowTitle("属性表(Attribute):"+self.layer.name())
        self.setAttribute(Qt.WA_DeleteOnClose)  # 设置关闭时销毁
        self.initUI()
        self.retranslateDiyUI()
        self.connectFunc()

    def initUI(self):

        self.setWindowIcon(QIcon(':/img/resources/logo.png'))

        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint | Qt.WindowMinimizeButtonHint)

        vl = QVBoxLayout(self)
        
        # 添加工具栏按钮
        toolsQHBoxLayout = QHBoxLayout(self)

        self.scaleToExtentPb = PushButton('缩放到图层',self)
        toolsQHBoxLayout.addWidget(self.scaleToExtentPb)

        self.scaleToSelected = PushButton('缩放到选中',self)
        toolsQHBoxLayout.addWidget(self.scaleToSelected)
        
        self.createFieldPb = PushButton('Create New Field',self)
        toolsQHBoxLayout.addWidget(self.createFieldPb)

        self.deleteFieldPb = PushButton('Delete Field',self)
        toolsQHBoxLayout.addWidget(self.deleteFieldPb)

        self.renameFieldPb = PushButton('重命名字段',self)
        toolsQHBoxLayout.addWidget(self.renameFieldPb)

        spacerItem = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolsQHBoxLayout.addItem(spacerItem)

        vl.addLayout(toolsQHBoxLayout)
        
        # 添加字段赋值栏
        fieldValueQHBoxLayer = QHBoxLayout(self)

        self.fieldNamesCb = ComboBox(self)
        fieldValueQHBoxLayer.addWidget(self.fieldNamesCb)

        self.fieldValueLE = LineEdit(self)
        fieldValueQHBoxLayer.addWidget(self.fieldValueLE)

        self.updateAllFieldPb = PushButton('Update All',self)
        fieldValueQHBoxLayer.addWidget(self.updateAllFieldPb)

        self.updateSelectedFieldPb = PushButton('Update Selected',self)
        fieldValueQHBoxLayer.addWidget(self.updateSelectedFieldPb)

        vl.addLayout(fieldValueQHBoxLayer)

        # 属性表栏
        self.tableView : QTableView  = QgsAttributeTableView(self)
        isDark = yoyiSetting().configSettingReader.value('windowStyle', type=int)
        if isDark:
            self.tableView.setStyleSheet('color: white;')
            self.tableView.horizontalHeader().setStyleSheet("color: black;")
            self.tableView.verticalHeader().setStyleSheet("color: black;")
        else:
            self.tableView.setStyleSheet('color: black;')

        vl.addWidget(self.tableView)

        # 筛选模式
        stateQHBoxLayout = QHBoxLayout()
        # 添加状态栏的表格显示筛选模式下拉框
        self.displayFilterCb = ComboBox(self)
        
        # 设置水平策略为最小
        self.displayFilterCb.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        stateQHBoxLayout.addWidget(self.displayFilterCb)
        spacerItem = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        stateQHBoxLayout.addItem(spacerItem)

        vl.addLayout(stateQHBoxLayout)

        # 刷新控件状态
        self.refreshEditingButtonStatus()
        self.syncFieldNameToComboBox()

        # 改变窗格大小与位置
        self.resize(800, 600)
        self.center()
        self.openAttributeDialog()
        QgsGui.editorWidgetRegistry().initEditors(self.mapCanvas)
    
    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate

        self.createFieldPb.setText(_translate("DIYDialog", "Create New Field"))
        self.deleteFieldPb.setText(_translate("DIYDialog", "Delete Field"))
        self.updateAllFieldPb.setText(_translate("DIYDialog", "Update All"))
        self.updateSelectedFieldPb.setText(_translate("DIYDialog", "Update Selected"))

        self.displayFilterCb.addItems([_translate("DIYDialog", "Show All"), _translate("DIYDialog", "Show Selected")])

    
    def refreshEditingButtonStatus(self):
        stauts = self.layer.isEditable()
        
        self.createFieldPb.setHidden(not stauts)
        self.deleteFieldPb.setHidden(not stauts)
        self.renameFieldPb.setHidden(not stauts)

        self.fieldNamesCb.setHidden(not stauts)
        self.fieldValueLE.setHidden(not stauts)
        self.updateAllFieldPb.setHidden(not stauts)
        self.updateSelectedFieldPb.setHidden(not stauts)
    
    def syncFieldNameToComboBox(self):
        self.fieldNamesCb.clear()
        self.fieldNamesCb.addItems(
            [field.name() for field in self.layer.fields()])
    
    def connectFunc(self):

        self.layer.editingStarted.connect(self.refreshEditingButtonStatus)
        self.layer.editingStopped.connect(self.refreshEditingButtonStatus)

        self.scaleToExtentPb.clicked.connect(self.zoomToLayer)
        self.scaleToSelected.clicked.connect(self.zommToSelected)

        self.createFieldPb.clicked.connect(self.createFieldPbClicked)
        self.deleteFieldPb.clicked.connect(self.deleteFieldPbClicked)
        self.renameFieldPb.clicked.connect(self.renameFieldPbClicked)

        # 连接赋值按钮
        self.updateAllFieldPb.clicked.connect(lambda: self.updateFieldValue("all"))
        self.updateSelectedFieldPb.clicked.connect(lambda: self.updateFieldValue("selected"))

        # 筛选组合框 信号连接
        self.displayFilterCb.currentIndexChanged.connect(self.updateDisplayFilterMode)

    def zoomToLayer(self):
        mapSetting = self.mapCanvas.mapSettings()
        mapCrs = mapSetting.destinationCrs()
        crsDest = self.layer.crs()
        transformContext = PROJECT.transformContext()
        xform = QgsCoordinateTransform(crsDest, mapCrs, transformContext)
        trueExtent = xform.transformBoundingBox(self.layer.extent())
        self.mapCanvas.setExtent(trueExtent)
        self.mapCanvas.refresh()
    
    def zommToSelected(self):
        if self.layer.selectedFeatureCount() > 0:
            mapSetting = self.mapCanvas.mapSettings()
            mapCrs = mapSetting.destinationCrs()
            crsDest = self.layer.crs()
            transformContext = PROJECT.transformContext()
            xform = QgsCoordinateTransform(crsDest, mapCrs, transformContext)
            trueExtent = xform.transformBoundingBox(self.layer.boundingBoxOfSelected())
            self.mapCanvas.setExtent(trueExtent)
            self.mapCanvas.refresh()

    def createFieldPbClicked(self):
        if not self.layer.isEditable():
            MessageBox("提示","图层未开启编辑模式",self).exec()
            return
        
        # 创建一个对话框
        dialog = NewFieldDialog(self)
        
        if dialog.exec_() and dialog.fieldName:
            fieldTypeIndex = dialog.createFieldTypeCb.currentIndex()
            # 整型
            if fieldTypeIndex == 0:
                fieldType = QVariant.Type.Int
            # 浮点型
            elif fieldTypeIndex == 1:
                fieldType = QVariant.Type.Double
            # 字符串
            elif fieldTypeIndex == 2:
                fieldType = QVariant.Type.String
            
            # 创建新字段
            if self.layer.addAttribute(
                QgsField(dialog.fieldName, fieldType, len=dialog.fieldLength, prec=dialog.fieldPrecision,)
            ):
                self.layer.updateFields()
                # 刷新字段名选项列表
                self.syncFieldNameToComboBox()
                # 刷新表格视图
                # self.tableModel.loadLayer()
            else:
                MessageBox("提示",f"字段 {dialog.fieldName} 创建失败",self).exec()
        dialog.deleteLater()
            
    def deleteFieldPbClicked(self):
        if not self.layer.isEditable():
            MessageBox("提示","图层未开启编辑模式",self).exec()
            return
        
        # 创建一个对话框
        fieldNames = [ i.name() for i in self.layer.fields() ]
        dialog = DeleteFieldDialog(fieldNames,self)

        if dialog.exec_() and dialog.beRemoveFieldNames:
            for fieldName in dialog.beRemoveFieldNames:
                fieldIndex = self.layer.fields().indexFromName(fieldName)
                if fieldIndex <0:
                    continue
                self.layer.deleteAttribute(fieldIndex)
            
            self.layer.updateFields()
            # 刷新字段名选项列表
            self.syncFieldNameToComboBox()
        dialog.deleteLater()
    
    def renameFieldPbClicked(self):
        if not self.layer.isEditable():
            MessageBox("提示","图层未开启编辑模式",self).exec()
            return
        
        # 创建一个对话框
        fieldNames = [ i.name() for i in self.layer.fields() ]
        dialog = RenameFieldDialog(fieldNames,self)

        if dialog.exec_() and dialog.beRenamedFieldName:
            fieldIndex = self.layer.fields().indexFromName(dialog.beRenamedFieldName)
            if fieldIndex < 0:
                MessageBox("提示","重命名失败",self).exec()
            else:
                self.layer.renameAttribute(fieldIndex,dialog.newFieldName)
        dialog.deleteLater()
        self.layer.updateFields()
        # 刷新字段名选项列表
        self.syncFieldNameToComboBox()
        
    def updateFieldValue(self, mode):
        """ 更新指定字段的属性值 """
        if not self.layer.isEditable():
            MessageBox("提示", "请先进入编辑模式", self).exec()
            return
            
        field_name = self.fieldNamesCb.currentText()
        field_index = self.layer.fields().indexFromName(field_name)
        if field_index == -1:
            MessageBox("错误", "字段不存在", self).exec()
            return
        # 获取输入值并转换类型
        value = self.fieldValueLE.text()
        field_type = self.layer.fields().field(field_index).type()
        try:
            if field_type in [QVariant.Type.Int, QVariant.Type.LongLong]:
                value = int(value)
            elif field_type == QVariant.Type.Double:
                value = float(value)
            elif field_type == QVariant.Type.String:
                value = str(value)
        except ValueError:
            MessageBox("错误", f"输入非法", self).exec()
            return
            
        # 根据模式获取要素ID
        if mode == "all":
            features = self.layer.getFeatures()
        elif mode == "selected":
            features = self.layer.selectedFeatures()
        else:
            features = []
            
        # 批量修改属性
        edit_buffer = self.layer.editBuffer()
        
        for feature in features:
            edit_buffer.changeAttributeValue(feature.id(), field_index, value)
        
        # 刷新表格
        self.tableModel.loadLayer()
        MessageBox("提示", "属性赋值完成", self).exec()
    
    def updateDisplayFilterMode(self, index):
        """ 根据下拉选项更新表格过滤模式 """
        if index == 0:  # 显示所有要素
            self.tableFilterModel.setFilterMode(QgsAttributeTableFilterModel.FilterMode.ShowAll)
        elif index == 1:  # 显示选中的要素
            self.tableFilterModel.setFilterMode(QgsAttributeTableFilterModel.FilterMode.ShowSelected)
        
        # 强制更新过滤器并重置视图
        # 刷新表格视图
        self.tableModel.loadLayer()
        self.tableView.resizeColumnsToContents()

    #def test(self, a:):
    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def openAttributeDialog(self):
        #iface
        self.layerCache = QgsVectorLayerCache(self.layer, 10000)
        self.tableModel = QgsAttributeTableModel(self.layerCache)
        self.tableModel.loadLayer()

        self.tableFilterModel = QgsAttributeTableFilterModel(self.mapCanvas, self.tableModel, parent=self.tableModel)
        self.tableFilterModel.setFilterMode(QgsAttributeTableFilterModel.ShowAll)  #显示问题
        self.tableView.setModel(self.tableFilterModel)
        #self.tableView.edit()
    
    def zoomToSelected(self):
        self.mapCanvas.zoomToSelected(self.layer)
        if self.extraMapcanvas:
            self.extraMapcanvas.zoomToSelected(self.layer)
        
        self.mapCanvas.refresh()
        if self.extraMapcanvas:
            self.extraMapcanvas.refresh()



