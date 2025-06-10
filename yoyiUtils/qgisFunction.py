import os
import os.path as osp

from osgeo import gdal
import numpy as np
from PyQt5.QtCore import QVariant
from qgis.core import QgsProject,QgsRasterFileWriter,QgsVectorFileWriter,QgsVectorLayer,\
    QgsCoordinateReferenceSystem,QgsVectorDataProvider,QgsPointXY,QgsPoint,QgsRectangle,\
    QgsFeature,QgsGeometry,QgsRasterLayer,QgsCoordinateTransform,QgsMapLayer,QgsField
from qgis import processing

from yoyiUtils.lonlatUtil import LonlatTool
from yoyiUtils.gdalCommon import raster2shp
from yoyiUtils.buildOrthogo import shp_orthogo_process

PROJECT = QgsProject.instance()

def imagexy2geo(trans,col,row):
    px = trans[0] + col * trans[1] + row * trans[2]
    py = trans[3] + col * trans[4] + row * trans[5]
    return px, py

def geo2imagexy(trans, x, y):
    a = np.array([[trans[1], trans[2]], [trans[4], trans[5]]])
    b = np.array([x - trans[0], y - trans[3]])
    return np.linalg.solve(a, b)  # 使用numpy的linalg.solve进行二元一次方程的求解

def saveShpFunc(shpPath,shpLayer,ct=None,onlySelectedFeatures=False,fileEncoding="UTF-8",driverName="ESRI Shapefile"):
    """
    ct = QgsCoordinateTransform(srcLayer.crs(),QgsCoordinateReferenceSystem('EPSG:4326'), PROJECT.transformContext())
    save_options:
    onlySelectedFeatures = True
    """
    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = driverName  # 默认情况下没有FileGDB驱动
    save_options.fileEncoding = fileEncoding
    save_options.onlySelectedFeatures = onlySelectedFeatures
    #save_options.SHAPE_RESTORE_SHX = "YES"
    transform_context = PROJECT.transformContext()
    if ct:
        save_options.ct = ct
        error = QgsVectorFileWriter.writeAsVectorFormatV2(shpLayer,
                                                  shpPath,
                                                  transform_context,
                                                  save_options)
    else:
        error = QgsVectorFileWriter.writeAsVectorFormatV2(shpLayer,
                                                          shpPath,
                                                          transform_context,
                                                          save_options)
    if error[0] == QgsVectorFileWriter.NoError:
        return 0
    else:
        print(error)
        return 1

# 根据尺寸创建渔网
def createFishNet(tifPath,netSize,outShpPath,driverName="ESRI Shapefile"):
    tifLonLatTool = LonlatTool(tifPath)
    XX,YY = tifLonLatTool.getXYSize()
    print(XX,YY)
    drawLayer = QgsVectorLayer("Polygon", "", "memory")
    drawLayer.setCrs(QgsCoordinateReferenceSystem.fromWkt(tifLonLatTool.getWkt()))
    pr : QgsVectorDataProvider = drawLayer.dataProvider()
    #pr.addAttributes([QgsField("FID", QVariant.LongLong),QgsField("tag", QVariant.Int)])
    y1 = 0
    y2 = netSize
    while(y2<=YY):
        x1 = 0
        x2 = netSize
        while(x2<=XX):
            geox1,geoy1 = tifLonLatTool.imagexy2geo(x1,y1)
            geox2,geoy2 = tifLonLatTool.imagexy2geo(x2,y2)
            recTemp = QgsRectangle(QgsPointXY(geox1,geoy1),QgsPointXY(geox2,geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
            x1 = x2
            x2 += netSize
        if x1 < XX:
            x2 = XX
            geox1, geoy1 = tifLonLatTool.imagexy2geo(x1, y1)
            geox2, geoy2 = tifLonLatTool.imagexy2geo(x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1,geoy1),QgsPointXY(geox2,geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
        y1 = y2
        y2 += netSize
    if y1 < YY:
        y2 = YY
        x1 = 0
        x2 = netSize
        while (x2 <= XX):
            geox1, geoy1 = tifLonLatTool.imagexy2geo(x1, y1)
            geox2, geoy2 = tifLonLatTool.imagexy2geo(x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1,geoy1),QgsPointXY(geox2,geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
            x1 = x2
            x2 += netSize
        if x1 < XX:
            x2 = XX
            geox1, geoy1 = tifLonLatTool.imagexy2geo(x1, y1)
            geox2, geoy2 = tifLonLatTool.imagexy2geo(x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1,geoy1),QgsPointXY(geox2,geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)

    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = driverName  # 默认情况下没有FileGDB驱动
    save_options.fileEncoding = "UTF-8"
    transform_context = PROJECT.transformContext()
    error = QgsVectorFileWriter.writeAsVectorFormatV2(drawLayer,
                                                      outShpPath,
                                                      transform_context,
                                                      save_options)
    if error[0] == QgsVectorFileWriter.NoError:
        return 0
    else:
        return 1

# 根据尺寸和影像范围创建渔网  guideTifPath 是一个里面包含了geoTrans、Projection的影像 要用它
def createFishNetByExtent(guideTifPath,netSize,outShpPath,xmin,xmax,ymin,ymax):
    tifDs : gdal.Dataset = gdal.Open(guideTifPath,0)
    tifGeoTrans = tifDs.GetGeoTransform()
    transTemp = (xmin, tifGeoTrans[1], tifGeoTrans[2], ymax, tifGeoTrans[4], tifGeoTrans[5])
    XX,YY = geo2imagexy(transTemp,xmax,ymin)
    print(XX,YY)
    drawLayer = QgsVectorLayer("Polygon", "", "memory")
    drawLayer.setCrs(QgsCoordinateReferenceSystem.fromWkt(tifDs.GetProjection()))
    pr: QgsVectorDataProvider = drawLayer.dataProvider()
    y1 = 0
    y2 = netSize
    while (y2 <= YY):
        x1 = 0
        x2 = netSize
        while (x2 <= XX):
            geox1, geoy1 = imagexy2geo(transTemp,x1, y1)
            geox2, geoy2 = imagexy2geo(transTemp,x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1, geoy1), QgsPointXY(geox2, geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
            x1 = x2
            x2 += netSize
        if x1 < XX:
            x2 = XX
            geox1, geoy1 = imagexy2geo(transTemp,x1, y1)
            geox2, geoy2 = imagexy2geo(transTemp,x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1, geoy1), QgsPointXY(geox2, geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
        y1 = y2
        y2 += netSize
    if y1 < YY:
        y2 = YY
        x1 = 0
        x2 = netSize
        while (x2 <= XX):
            geox1, geoy1 = imagexy2geo(transTemp,x1, y1)
            geox2, geoy2 = imagexy2geo(transTemp,x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1, geoy1), QgsPointXY(geox2, geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
            x1 = x2
            x2 += netSize
        if x1 < XX:
            x2 = XX
            geox1, geoy1 = imagexy2geo(transTemp,x1, y1)
            geox2, geoy2 = imagexy2geo(transTemp,x2, y2)
            recTemp = QgsRectangle(QgsPointXY(geox1, geoy1), QgsPointXY(geox2, geoy2))
            featTemp = QgsFeature(drawLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)

    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = "ESRI Shapefile"  # 默认情况下没有FileGDB驱动
    save_options.fileEncoding = "UTF-8"
    transform_context = PROJECT.transformContext()
    error = QgsVectorFileWriter.writeAsVectorFormatV2(drawLayer,
                                                      outShpPath,
                                                      transform_context,
                                                      save_options)
    if error[0] == QgsVectorFileWriter.NoError:
        return 0
    else:
        return 1



# 根据x y 间隔数量创建渔网
def createFishNetByXYInterval(extentPath,outShpPath,xSegNum,ySegNum):
    extentLayer = QgsVectorLayer(extentPath)

    mergeGeo: QgsGeometry = None
    for feature in extentLayer.getFeatures():
        feature: QgsFeature
        if mergeGeo == None:
            mergeGeo = feature.geometry()
        else:
            mergeGeo = mergeGeo.combine(feature.geometry())

    tempLayer = QgsVectorLayer("Polygon", "temp", "memory")
    tempLayer.setCrs(extentLayer.crs())
    pr : QgsVectorDataProvider = tempLayer.dataProvider()
    extent : QgsRectangle = extentLayer.extent()
    xInterval = (extent.xMaximum() - extent.xMinimum()) / xSegNum
    yInterval = (extent.yMaximum() - extent.yMinimum()) / ySegNum
    for i in range(ySegNum):
        for j in range(xSegNum):
            x1 = extent.xMinimum() + j*xInterval
            x2 = min(extent.xMinimum() + (j+1) * xInterval, extent.xMaximum())
            y1 = extent.yMinimum() + i*yInterval
            y2 = min(extent.yMinimum() + (i+1) * yInterval, extent.yMaximum())
            recTemp = QgsRectangle(x1,y1,x2,y2)
            recTempGeo = QgsGeometry.fromRect(recTemp)
            if mergeGeo and mergeGeo.isGeosValid() and not mergeGeo.intersects(recTempGeo):
                pass
            else:
                featTemp = QgsFeature(tempLayer.fields())
                featTemp.setGeometry(recTempGeo)
                pr.addFeature(featTemp)
    ct = QgsCoordinateTransform(tempLayer.crs(), QgsCoordinateReferenceSystem('EPSG:3857'), PROJECT.transformContext())
    status = saveShpFunc(outShpPath,tempLayer,ct=ct,driverName="GPKG") #0 success 1 error
    return status

# 根据外接矩形框和XY分割数量创建渔网
def createFishNetByXYExtent(crs,extent,outShpPath,xSegNum,ySegNum):
    tempLayer = QgsVectorLayer("Polygon", "temp", "memory")
    tempLayer.setCrs(crs)
    pr : QgsVectorDataProvider = tempLayer.dataProvider()
    extent : QgsRectangle = extent
    xInterval = (extent.xMaximum() - extent.xMinimum()) / xSegNum
    yInterval = (extent.yMaximum() - extent.yMinimum()) / ySegNum
    for i in range(ySegNum):
        for j in range(xSegNum):
            x1 = extent.xMinimum() + j*xInterval
            x2 = min(extent.xMinimum() + (j+1) * xInterval, extent.xMaximum())
            y1 = extent.yMinimum() + i*yInterval
            y2 = min(extent.yMinimum() + (i+1) * yInterval, extent.yMaximum())
            recTemp = QgsRectangle(x1,y1,x2,y2)
            featTemp = QgsFeature(tempLayer.fields())
            featTemp.setGeometry(QgsGeometry.fromRect(recTemp))
            pr.addFeature(featTemp)
    status = saveShpFunc(outShpPath,tempLayer,driverName="ESRI Shapefile") #0 success 1 error
    return status



# 通用解译矢量后处理
def shpCommonProcess(inputFile,outShp,tempDir,tolerance=2,minHoleArea=100,removeArea=100,orth=False,dissolve=False,onlyTrans=False,typeName=None,callback=None):
    '''通用解译矢量后处理
    参数说明:
    - inputFile: 输入文件
    - outShp: 输出文件
    - tempDir: 存放中间过程的临时文件夹
    - tolerance: 矢量要素简化的容差
    - minHoleArea: 删除空洞工具中，删除小于此面积的空洞
    - removeArea: 删除小于此面积的多边形
    - orth: 
    - dissolve: 是否进行矢量融合
    - onlyTrans: 
    - callback: 接收处理进度的回调函数
    '''
    if inputFile.split(".")[-1] in ["tif","TIF"]:
        initShp = osp.join(tempDir,"init_shp.shp")
        raster2shp(inputFile,initShp,"value")
    else:
        initShp = inputFile
    
    if callback:
        callback(10)

    if onlyTrans:
        init3857Shp = osp.join(tempDir,"init_3857_shp.shp")
        processing.run("native:reprojectlayer", {
            'INPUT':initShp,
            'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:3857'),
            'OUTPUT':init3857Shp
        })
        calAreaShp = osp.join(tempDir,"calArea.shp")
        resultCalArea = processing.run("native:fieldcalculator", {
            'INPUT':init3857Shp,
            'FIELD_NAME':'area',
            'FIELD_TYPE':0,
            'FIELD_LENGTH':10,
            'FIELD_PRECISION':2,
            'FORMULA':' $area ',
            'OUTPUT':calAreaShp
        })

        if typeName:
            typeNameShp = osp.join(tempDir,"addTypeName.shp")
            resultAddTypeName = processing.run("native:fieldcalculator", {
                'INPUT':calAreaShp,
                'FIELD_NAME':'typename',
                'FIELD_TYPE':2,
                'FIELD_LENGTH':10,
                'FIELD_PRECISION':0,
                'FORMULA':f'\'{typeName}\'',
                'OUTPUT':typeNameShp
            })
            calAreaShp = typeNameShp

        processing.run("native:reprojectlayer", {
            'INPUT':calAreaShp,
            'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:4326'),
            'OUTPUT':outShp
        })
    elif orth:
        if callback:
            callback(50)
        shp_orthogo_process(initShp,outShp)
    else:
        init3857Shp = osp.join(tempDir,"init_3857_shp.shp")

        processing.run("native:reprojectlayer", {
            'INPUT':initShp,
            'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:3857'),
            'OUTPUT':init3857Shp
        })
        
        if dissolve:
            dissolve1Shp = osp.join(tempDir,"temp_dissolve1.shp")
            resultDissolve1 = processing.run("native:dissolve", {
                'INPUT':init3857Shp,
                'FIELD':[],
                'OUTPUT':dissolve1Shp
            })
            dissolveShp = osp.join(tempDir,"temp_dissolve.shp")
            resultSinglePart = processing.run("native:multiparttosingleparts", {
                'INPUT':dissolve1Shp,
                'OUTPUT':dissolveShp
            })
        else:
            dissolveShp = init3857Shp
        
        if callback:
            callback(20)

        simplyShp = osp.join(tempDir,"temp_simply.shp")
        resultSimply = processing.run("native:simplifygeometries", {
            'INPUT':dissolveShp,
            'METHOD':0,
            'TOLERANCE':tolerance,
            'OUTPUT':simplyShp
        })

        if callback:
            callback(30)

        deleteHolesShp = osp.join(tempDir,"temp_deleteHoles.shp")
        resultDeleteHoles = processing.run("native:deleteholes", {
            'INPUT':simplyShp,
            'MIN_AREA':minHoleArea,
            'OUTPUT':deleteHolesShp
        })

        if callback:
            callback(40)

        buffer1Shp = osp.join(tempDir,"temp_buffer1.shp")
        resultBuffer1 = processing.run("native:buffer", {
            'INPUT':deleteHolesShp,
            'DISTANCE':-2,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':buffer1Shp
        })
        
        if callback:
            callback(50)

        fixTopoShp = osp.join(tempDir,"temp_fixTopo.shp")
        resultFixTopo = processing.run("native:fixgeometries", {
            'INPUT':buffer1Shp,
            'OUTPUT':fixTopoShp
        })

        if callback:
            callback(60)

        singlePartShp = osp.join(tempDir,"temp_singlePart.shp")
        resultSinglePart = processing.run("native:multiparttosingleparts", {
            'INPUT':fixTopoShp,
            'OUTPUT':singlePartShp
        })

        buffer2Shp = osp.join(tempDir,"temp_buffer2.shp")
        resultBuffer2 = processing.run("native:buffer", {
            'INPUT':singlePartShp,
            'DISTANCE':4,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':buffer2Shp
        })

        buffer3Shp = osp.join(tempDir,"temp_buffer3.shp")
        resultBuffer3 = processing.run("native:buffer", {
            'INPUT':buffer2Shp,
            'DISTANCE':-2,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':buffer3Shp
        })

        if callback:
            callback(70)

        fixTopo2Shp = osp.join(tempDir,"temp_fixTopo2.shp")
        resultFixTopo = processing.run("native:fixgeometries", {
            'INPUT':buffer3Shp,
            'OUTPUT':fixTopo2Shp
        })

        if callback:
            callback(80)

        calAreaShp = osp.join(tempDir,"calArea.shp")
        resultCalArea = processing.run("native:fieldcalculator", {
            'INPUT':fixTopo2Shp,
            'FIELD_NAME':'area',
            'FIELD_TYPE':0,
            'FIELD_LENGTH':10,
            'FIELD_PRECISION':2,
            'FORMULA':' $area ',
            'OUTPUT':calAreaShp
        })

        if typeName:
            typeNameShp = osp.join(tempDir,"addTypeName.shp")
            resultAddTypeName = processing.run("native:fieldcalculator", {
                'INPUT':calAreaShp,
                'FIELD_NAME':'typename',
                'FIELD_TYPE':2,
                'FIELD_LENGTH':0,
                'FIELD_PRECISION':0,
                'FORMULA':f'\'{typeName}\'',
                'OUTPUT':typeNameShp
            })
            calAreaShp = typeNameShp

        outLayer = QgsVectorLayer(calAreaShp)
        outLayer.startEditing()
        outLayer.selectByExpression(f" \"area\" < {removeArea} or \"area\" is None",QgsVectorLayer.SetSelection)
        
        outLayer.deleteSelectedFeatures()
        outLayer.commitChanges()

        if callback:
            callback(90)

        ct = QgsCoordinateTransform(outLayer.crs(),QgsCoordinateReferenceSystem('EPSG:4326'), PROJECT.transformContext())
        saveShpFunc(outShp,outLayer,ct)
        # processing.run("native:reprojectlayer", {
        #     'INPUT':calAreaShp,
        #     'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:4326'),
        #     'OUTPUT':outShp
        # })
        

def shpChangeAnalysis(preShpFile,lastShpFile,tempDir,outShp,miniWidth=6,callback=None):
    
    removalShp = osp.join(tempDir,"removalShp.shp")
    additionShp = osp.join(tempDir,"additionShp.shp")

    processing.run("native:difference",{
        'INPUT' : preShpFile,
        'OVERLAY' : lastShpFile,
        'OUTPUT':removalShp
    })

    if callback:
        callback(20)

    if osp.exists(removalShp):
        removalShp_cal = osp.join(tempDir,"removalShpCal.shp")
        processing.run("native:fieldcalculator", {
            'INPUT':removalShp,
            'FIELD_NAME':'width',
            'FIELD_TYPE':0,
            'FIELD_LENGTH':10,
            'FIELD_PRECISION':2,
            'FORMULA':' if($perimeter*$perimeter-16*$area>0,(4*$area)/($perimeter+ sqrt( $perimeter*$perimeter-16*$area)),1000) ',
            'OUTPUT':removalShp_cal
        })
        removalLayer = QgsVectorLayer(removalShp_cal)
        removalLayer.dataProvider().addAttributes([QgsField('change', QVariant.String)])
        removalLayer.updateFields()
        removalLayer.startEditing()

        bedeleteIds = []
        for feature in removalLayer.getFeatures():
            width = feature.attribute('width')
            if width < miniWidth:
                bedeleteIds.append(feature.id())
            else:
                feature.setAttribute('change','remove')
                removalLayer.updateFeature(feature)
        
        removalLayer.deleteFeatures(bedeleteIds)
        removalLayer.commitChanges()
    else:
        removalShp_cal = None
        removalLayer = None

    if callback:
        callback(40)

    processing.run("native:difference",{
        'INPUT' : lastShpFile,
        'OVERLAY' : preShpFile,
        'OUTPUT':additionShp
    })

    if callback:
        callback(60)

    if osp.exists(additionShp):
        additionShp_cal = osp.join(tempDir,"additionShpCal.shp")
        processing.run("native:fieldcalculator", {
            'INPUT':additionShp,
            'FIELD_NAME':'width',
            'FIELD_TYPE':0,
            'FIELD_LENGTH':10,
            'FIELD_PRECISION':2,
            'FORMULA':' if($perimeter*$perimeter-16*$area>0,(4*$area)/($perimeter+ sqrt( $perimeter*$perimeter-16*$area)),1000) ',
            'OUTPUT':additionShp_cal
        })
        additionLayer = QgsVectorLayer(additionShp_cal)
        additionLayer.dataProvider().addAttributes([QgsField('change', QVariant.String)])
        additionLayer.updateFields()
        additionLayer.startEditing()

        bedeleteIds = []
        for feature in additionLayer.getFeatures():
            width = feature.attribute('width')
            if width < miniWidth:
                bedeleteIds.append(feature.id())
            else:
                feature.setAttribute('change','addition')
                additionLayer.updateFeature(feature)
        
        additionLayer.deleteFeatures(bedeleteIds)
        additionLayer.commitChanges()
    else:
        additionShp_cal = None
        additionLayer = None

    if callback:
        callback(80)
    if removalShp_cal and osp.exists(removalShp_cal) and additionShp_cal and osp.exists(additionShp_cal):
        params = {'LAYERS':[removalShp_cal,additionShp_cal],'OUTPUT':outShp}
        processing.run("native:mergevectorlayers", params)
    elif removalShp_cal and osp.exists(removalShp_cal):
        saveShpFunc(outShp,removalLayer)
    elif additionShp_cal and osp.exists(additionShp_cal):
        saveShpFunc(outShp,additionLayer)
    
    del removalLayer
    del additionLayer 
    return outShp
    