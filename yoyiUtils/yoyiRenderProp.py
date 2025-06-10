from qgis.core import QgsCategorizedSymbolRenderer,QgsFillSymbol,QgsRendererCategory,\
    Qgis,QgsTask,QgsMessageLog,QgsVectorLayer,QgsFeature\
    ,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsTextFormat,QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,\
    QgsColorRampShader,QgsPalettedRasterRenderer,QgsRasterLayer,QgsMapLayer,QgsPointPatternFillSymbolLayer,\
    QgsSimpleFillSymbolLayer,QgsLinePatternFillSymbolLayer,QgsSymbolLayer,QgsLineSymbol
import os.path as osp
import yaml
from osgeo import gdal
import numpy as np
from qgis.gui import QgsMessageBar
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QThread, pyqtSignal
import random

def parse_cfg(config_path):
    """Batch
        解析yaml格式的配置文件
    """
    with open(config_path, 'rb') as stream:
        try:
            cfg = yaml.safe_load(stream)
            return cfg
        except yaml.YAMLError as exc:
            print(exc)

# tifInfo  yti文件
def getTifInfo(tifPath:str,tifInfo):
    if osp.exists(tifInfo):
        cfg = parse_cfg(tifInfo)
        print(cfg)
    else:
        tifDs:gdal.Dataset = gdal.Open(tifPath)
        tifNp = tifDs.ReadAsArray()
        print(np.unique(tifNp))

# tifInfo  yti文件
def getShpInfo(ShpPath:str,shpInfo):
    if osp.exists(shpInfo):
        cfg = parse_cfg(shpInfo)
        print(cfg)
    else:
        tifDs:gdal.Dataset = gdal.Open(ShpPath)
        tifNp = tifDs.ReadAsArray()
        print(np.unique(tifNp))

# 创建shp的标注
def createShpLabel(layer:QgsVectorLayer,fieldName="FID",r=255,g=0,b=0,size=15,isExpression=False):
    textFrom = QgsTextFormat()
    textFrom.setColor(QColor(r, g, b))
    textFrom.setSize(size)
    labelSetting = QgsPalLayerSettings()
    labelSetting.fieldName = fieldName
    labelSetting.isExpression = isExpression
    labelSetting.setFormat(textFrom)
    labeling = QgsVectorLayerSimpleLabeling(labelSetting)
    layer.setLabeling(labeling)
    layer.setLabelsEnabled(True)
    
    return labeling


# layer = iface.activeLayer()
# layer.renderer().symbol().symbolLayers()[0].properties()
class yoyiShpPropClass:
    def __init__(self):
        self.fillDict = {'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 'color': '0,254,0,255', 'joinstyle': 'bevel', 'offset': '0,0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'outline_color': '35,35,35,255', 'outline_style': 'solid', 'outline_width': '0.26', 'outline_width_unit': 'MM', 'style': 'solid'}
        self.lineDict = {'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 'color': '0,0,0,0', 'joinstyle': 'bevel', 'offset': '0,0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'outline_color': '53,121,177,255', 'outline_style': 'solid', 'outline_width': '0.96', 'outline_width_unit': 'MM', 'style': 'solid'}
        self.lineDictNew = {'align_dash_pattern': '0', 'capstyle': 'square', 'customdash': '5;2', 'customdash_map_unit_scale': '3x:0,0,0,0,0,0', 'customdash_unit': 'MM', 'dash_pattern_offset': '0', 'dash_pattern_offset_map_unit_scale': '3x:0,0,0,0,0,0', 'dash_pattern_offset_unit': 'MM', 'draw_inside_polygon': '0', 'joinstyle': 'bevel', 'line_color': '228,26,28,255', 'line_style': 'solid', 'line_width': '0.96', 'line_width_unit': 'MM', 'offset': '0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'ring_filter': '0', 'tweak_dash_pattern_on_corners': '0', 'use_custom_dash': '0', 'width_map_unit_scale': '3x:0,0,0,0,0,0'}
        self.lineFillDict = {'angle': '45', 'color': '55,126,184,255', 'distance': '2', 'distance_map_unit_scale': '3x:0,0,0,0,0,0', 'distance_unit': 'MM', 'line_width': '0.26', 'line_width_map_unit_scale': '3x:0,0,0,0,0,0', 'line_width_unit': 'MM', 'offset': '0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'outline_width_map_unit_scale': '3x:0,0,0,0,0,0', 'outline_width_unit': 'MM'}

    def getFillDict(self,color):
        fillDictTemp = self.fillDict
        fillDictTemp['color'] = color
        return fillDictTemp

    def getLinePatternFillDict(self,color,line_width,distance):
        linePatternDictTemp = self.lineFillDict
        linePatternDictTemp['color'] = color
        linePatternDictTemp['line_width'] = line_width
        linePatternDictTemp['distance'] = distance
        return linePatternDictTemp

    def getLineDict(self,color,linewidth):
        #lineDictTemp = self.dotLineDictNew
        lineDictTemp = self.lineDictNew
        lineDictTemp['line_color'] = color
        lineDictTemp['line_width'] = linewidth
        return lineDictTemp

    def createDiySymbol(self,color="254,0,0",lineWidth="0.2",opacity=1,isFull=True,returnSymbo=False,fullPattern="simple",distance=0.5):
        if isFull:
            if fullPattern == "simple":
                symbol = QgsFillSymbol.createSimple(self.getFillDict(color))
                symbol.setOpacity(opacity)
            elif fullPattern == "line":
                symbol = QgsFillSymbol()
                symbolLayer0 = QgsLinePatternFillSymbolLayer.create(self.getLinePatternFillDict(color,line_width=lineWidth,distance=str(distance)))
                symbolLayer1 = QgsSimpleLineSymbolLayer.create(self.getLineDict(color, lineWidth))
                symbol.changeSymbolLayer(0, symbolLayer0)
                symbol.appendSymbolLayer(symbolLayer1)
                symbol.setOpacity(opacity)
            return symbol if returnSymbo else QgsSingleSymbolRenderer(symbol)
        else:
            symbol = QgsFillSymbol()
            symbolLayer = QgsSimpleLineSymbolLayer.create(self.getLineDict(color, lineWidth))
            symbol.changeSymbolLayer(0, symbolLayer)
            return symbol if returnSymbo else QgsSingleSymbolRenderer(symbol)

    def getDialogProp(self,layer:QgsVectorLayer):
        symbolLayerType = type(layer.renderer().symbol().symbolLayers()[0])
        prop = layer.renderer().symbol().symbolLayers()[0].properties()
        if symbolLayerType == QgsSimpleFillSymbolLayer:
            renderType = 1  # 0 空心 1 实心 2 空心线条填充
            colorStr : str = prop['color']
            colorR, colorG, colorB, colorAlpha = colorStr.split(",")
            renderOutline = prop['outline_width']
        elif symbolLayerType == QgsSimpleLineSymbolLayer:
            renderType = 0  # 0 空心 1 实心 2 空心线条填充
            colorStr : str = prop['line_color']
            colorR,colorG,colorB,colorAlpha = colorStr.split(",")
            renderOutline = prop['line_width']
        elif symbolLayerType == QgsLinePatternFillSymbolLayer:
            renderType = 2
            colorStr: str = prop['color']
            colorR, colorG, colorB, colorAlpha = colorStr.split(",")
            renderOutline = prop['line_width']
        return renderType,int(colorR),int(colorG),int(colorB),float(renderOutline)

    def getCategoryRenderByColorMap(self,field,colorMap,isFull=False):
        categorized_renderer = QgsCategorizedSymbolRenderer()
        for keyTemp, valueTemp in colorMap.items():
            color = f"{valueTemp[1]},{valueTemp[2]},{valueTemp[3]}"
            symbol = self.createDiySymbol(color,lineWidth='0.7',isFull=isFull,returnSymbo=True)
            cateTemp = QgsRendererCategory(keyTemp,symbol,valueTemp[0])
            categorized_renderer.addCategory(cateTemp)
        # 其他类
        otherSymbol = self.createDiySymbol("74,111,163",lineWidth='0.7',isFull=True,returnSymbo=True)
        otherCate = QgsRendererCategory(None,otherSymbol,None)
        categorized_renderer.addCategory(otherCate)
        categorized_renderer.setClassAttribute(field)
        return categorized_renderer

    # 74 111 163
    def getHighLightRender(self,field,value,mainColor="255,0,0",otherColor="74,111,163",isFull=False):
        categorized_renderer = QgsCategorizedSymbolRenderer()
        mainSymbol = self.createDiySymbol(mainColor,lineWidth='0.7',isFull=isFull,returnSymbo=True)
        mainCate = QgsRendererCategory(value,mainSymbol,value)
        categorized_renderer.addCategory(mainCate)
        otherSymbol = self.createDiySymbol(otherColor,lineWidth='0.7',isFull=isFull,returnSymbo=True)
        otherCate = QgsRendererCategory(None,otherSymbol,None)
        categorized_renderer.addCategory(otherCate)
        categorized_renderer.setClassAttribute(field)
        return categorized_renderer



    def changeSimpleSingleTifRender(self,tifLayer,pixelValue,r,g,b,opacity=0.5):
        pcolor = []
        pcolor.append(QgsColorRampShader.ColorRampItem(pixelValue, QColor(r,g,b),"1"))
        render = QgsPalettedRasterRenderer(tifLayer.dataProvider(), 1, QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
        render.setOpacity(opacity)
        tifLayer.setRenderer(render)


if __name__ == '__main__':
    pass


