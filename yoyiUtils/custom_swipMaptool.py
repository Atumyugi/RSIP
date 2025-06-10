from qgis.PyQt.QtCore import QRectF, Qt, QLineF
from qgis.PyQt.QtGui import QCursor, QPixmap,QPen, QColor
from qgis.core import QgsProject, QgsMapSettings, QgsMapRendererParallelJob
from qgis.gui import QgsMapTool,QgsMapCanvasItem

import yoyirs_rc

PROJECT = QgsProject.instance()


class SwipeMapItem(QgsMapCanvasItem):
    def __init__(self, mapCanvas):
        super(SwipeMapItem, self).__init__(mapCanvas)
        self.image = None
        self.line = None
        self.startPaint = False

        self.direction = -1
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0

    def updateImageRect(self, x, y):
        w = self.boundingRect().width()
        h = self.boundingRect().height()
        if self.direction == -1:  # all
            self.x = 0
            self.y = 0
            self.w = w
            self.h = h
        elif self.direction == 0:  # 0:'⬇'
            self.x = 0
            self.y = 0
            self.w = w
            self.h = y
            self.line = QLineF(0, y, w, y)
        elif self.direction == 1:  # 1:'⬆'
            self.x = 0
            self.y = y
            self.w = w
            self.h = h - y
            self.line = QLineF(0, y, w, y)
        elif self.direction == 2:  # 2:'➡'
            self.x = 0
            self.y = 0
            self.w = x
            self.h = h
            self.line = QLineF(x, 0, x, h)
        else:  # 3:'⬅'
            self.x = x
            self.y = 0
            self.w = w - x
            self.h = h
            self.line = QLineF(x, 0, x, h)
        self.startPaint = True
        self.update()

    def paint(self, painter, *args):
        if self.startPaint is False:
            return

        pen = QPen(Qt.DashDotDotLine)
        pen.setColor(QColor(18, 150, 219))
        pen.setWidth(4)
        painter.setPen(pen)
        if self.line:
            painter.drawLine(self.line)

        image = self.image.copy(int(self.x), int(self.y), int(self.w), int(self.h))
        painter.drawImage(QRectF(self.x, self.y, self.w, self.h), image)


class SwipeMapTool(QgsMapTool):
    def __init__(self, layerCombobox, mapCanvas):
        super(SwipeMapTool, self).__init__(mapCanvas)
        self.layerCombobox = layerCombobox
        self.mapCanvas = mapCanvas
        self.mapItem = SwipeMapItem(self.mapCanvas)
        self.startSwipe = False
        self.controlDown = False
        self.layers = []

        self.cursorSV = QCursor(QPixmap(":/img/resources/splitV.png"))
        self.cursorSH = QCursor(QPixmap(":/img/resources/splitH.png"))
        self.cursorUp = QCursor(QPixmap(":/img/resources/rollerUp.png"))
        self.cursorDown = QCursor(QPixmap(":/img/resources/rollerDown.png"))
        self.cursorLeft = QCursor(QPixmap(":/img/resources/rollerLeft.png"))
        self.cursorRight = QCursor(QPixmap(":/img/resources/rollerRight.png"))
        self.cursorBox = QCursor(QPixmap(":/img/resources/splitV.png"))
    
    def activate(self):
        self.connect()
        self.startSwipe = False
        self.setLayersSwipe()
    
    def connect(self, is_connect=True):
        if is_connect:
            self.mapCanvas.mapCanvasRefreshed.connect(self.setMapLayers)
            self.layerCombobox.currentIndexChanged.connect(self.setLayersSwipe)
        else:
            try:
                print("disconnect ")
                self.mapCanvas.mapCanvasRefreshed.disconnect(self.setMapLayers)
                self.layerCombobox.currentIndexChanged.disconnect(self.setLayersSwipe)
            except Exception as e:
                print(e)
    
    def setLayersSwipe(self, ):
        self.layers = PROJECT.layerTreeRoot().checkedLayers()
        currentLayer = PROJECT.mapLayer(self.layerCombobox.currentData())
        if currentLayer in self.layers:
            self.layers.remove(currentLayer)
        self.setMapLayers()
    
    def setMapLayers(self):
        def finished():
            self.mapItem.image = job.renderedImage()
            self.mapItem.setRect(self.mapCanvas.extent())

        if len(self.layers) == 0:
            return

        settings = QgsMapSettings(self.mapCanvas.mapSettings())
        settings.setLayers(self.layers)

        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.finished.connect(finished)
        job.waitForFinished()
    
    def keyPressEvent(self, e):
        if self.mapCanvas.isDrawing():
            return
        if e.modifiers() == Qt.ControlModifier:
            self.mapCanvas.setCursor(self.cursorBox)
            self.controlDown = True
    
    def keyReleaseEvent(self, e) -> None:
        if self.mapCanvas.isDrawing():
            return
        if not e.isAutoRepeat():
            self.controlDown = False
            pos = self.cursorBox.pos()
            # 触发鼠标移动事件
            self.cursorBox.setPos(pos.x() + 1, pos.y() + 1)
    
    def canvasPressEvent(self, e):
        if self.mapCanvas.isDrawing():
            return
        self.startSwipe = True
        w, h = self.mapCanvas.width(), self.mapCanvas.height()
        if not self.controlDown:
            if 0.25 * w < e.x() < 0.75 * w and e.y() < 0.5 * h:
                self.mapItem.direction = 0  # '⬇'
                self.mapCanvas.setCursor(self.cursorSH)
            elif 0.25 * w < e.x() < 0.75 * w and e.y() > 0.5 * h:
                self.mapItem.direction = 1  # '⬆'
                self.mapCanvas.setCursor(self.cursorSH)
            elif e.x() < 0.25 * w:
                self.mapItem.direction = 2  # '➡'
                self.mapCanvas.setCursor(self.cursorSV)
            else:  # elif e.x() > 0.75 * w:
                self.mapItem.direction = 3  # '⬅'
                self.mapCanvas.setCursor(self.cursorSV)
            self.mapItem.updateImageRect(e.x(), e.y())
        else:
            self.mapItem.direction = -1  # all
            self.mapItem.updateImageRect(w, h)

    def canvasMoveEvent(self, e):
        if self.mapCanvas.isDrawing():
            return
        if self.controlDown:
            return
        if self.startSwipe:
            self.mapItem.updateImageRect(e.x(), e.y())
        else:
            # 设置当前cursor
            w, h = self.mapCanvas.width(), self.mapCanvas.height()
            if e.x() < 0.25 * w:
                self.mapCanvas.setCursor(self.cursorRight)
            if e.x() > 0.75 * w:
                self.mapCanvas.setCursor(self.cursorLeft)
            if 0.25 * w < e.x() < 0.75 * w and e.y() < 0.5 * h:
                self.mapCanvas.setCursor(self.cursorDown)
            if 0.25 * w < e.x() < 0.75 * w and e.y() > 0.5 * h:
                self.mapCanvas.setCursor(self.cursorUp)

    def canvasReleaseEvent(self, e):
        self.startSwipe = False
        self.canvasMoveEvent(e)
        # 鼠标释放后重新绘制
        self.mapItem.startPaint = False
        self.mapItem.update()

    def deactivate(self):
        self.connect(False)
        super().deactivate()
        

