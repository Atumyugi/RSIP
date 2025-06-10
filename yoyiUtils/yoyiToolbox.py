from typing import List
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon,QStandardItem

toolboxIdDict = {
    #II raster
    #III raster common
    1101 : "rasterClipPbClicked",
    1102 : "rasterMergePbClicked",
    1103 : "rasterBuildOverviewPbClicked",
    1104 : "rasterReprojectPbClicked",
    #III raster trans
    1201 : "raster2ShpPbClicked",
    1202 : "rasterExportPbClicked",
    1203 : "raster16to8PbClicked",
    1204 : "rasterRecombinePbClicked",
    #III raster cal
    1301 : "rasterCalcPbClicked",
    1302 : "rasterZonalStaticPbClicked",
    
    #II vector
    #III vector geo
    2101 : "shpClipPbClicked",
    2102 : "shpMergePbClicked",
    2103 : "shpErasePbClicked",
    2104 : "shpInterPbClicked",
    2105 : "shpDissolvePbClicked",
    2106 : "shpBufferPbClicked",
    #III vector common
    2201 : "shpRemoveSmallPbClicked",
    2202 : "shpFillHolePbClicked",
    2203 : "shpOrthPbClicked",
    2204 : "shpSimplyPbClicked",
    2205 : "shpSmoothPbClicked",
    2206 : "shpReprojectPbClicked",
    2207 : "shpCalAreaPbClicked",
    2208 : "shpFixPbClicked",
    #III vector trans
    2301 : "shp2RasterPbClicked",
    2302 : "shpExportPbClicked",
    2303 : "shp2SinglePbClicked",
    2304 : "shpCalCentroidPbClicked",
    #III vector analysis
    2402 : "shpChangeAnalysisPbClicked",


}



def getItems_shp_geo() -> List[QStandardItem]:
    itemShp_geoList = []

    item_shpClip = QStandardItem("矢量裁剪 (Vector Clip)") # 2101
    item_shpClip.setData({"ID":2101}, Qt.ItemDataRole.UserRole)
    item_shpClip.setIcon(QIcon(":/img/resources/gis/shp_clip_polygon.png"))
    itemShp_geoList.append(item_shpClip)

    item_shpMerge = QStandardItem("矢量合并 (Vector Merge)") # 2102
    item_shpMerge.setData({"ID":2102}, Qt.ItemDataRole.UserRole)
    item_shpMerge.setIcon(QIcon(":/img/resources/gis/shp_merge.png"))
    itemShp_geoList.append(item_shpMerge)

    item_shpErase = QStandardItem("矢量相减 (Vector Erase)") # 2103
    item_shpErase.setData({"ID":2103}, Qt.ItemDataRole.UserRole)
    item_shpErase.setIcon(QIcon(":/img/resources/shpProcess/shp_erase.png"))
    itemShp_geoList.append(item_shpErase)

    item_shpInter = QStandardItem("矢量相交 (Vector Intersect)") # 2104
    item_shpInter.setData({"ID":2104}, Qt.ItemDataRole.UserRole)
    item_shpInter.setIcon(QIcon(":/img/resources/shpProcess/shp_interesct.png"))
    itemShp_geoList.append(item_shpInter)

    item_shpDissolve = QStandardItem("矢量融合 (Vector Dissolve)") # 2105
    item_shpDissolve.setData({"ID":2105}, Qt.ItemDataRole.UserRole)
    item_shpDissolve.setIcon(QIcon(":/img/resources/shpProcess/shp_dissolve.png"))
    itemShp_geoList.append(item_shpDissolve)

    item_shpBuffer = QStandardItem("缓冲区 (Vector Buffer)") # 2106
    item_shpBuffer.setData({"ID":2106}, Qt.ItemDataRole.UserRole)
    item_shpBuffer.setIcon(QIcon(":/img/resources/shpProcess/shp_buffer.png"))
    itemShp_geoList.append(item_shpBuffer)
    
    return itemShp_geoList



def getItems_shp_common() -> List[QStandardItem]:
    resList = []

    shpRemoveSmallPb = QStandardItem("滤除碎斑 (Remove Area)") # 2201
    shpRemoveSmallPb.setData({"ID":2201}, Qt.ItemDataRole.UserRole)
    shpRemoveSmallPb.setIcon(QIcon(":/img/resources/shpProcess/shp_removeArea.png"))
    resList.append(shpRemoveSmallPb)

    shpFillHolePb = QStandardItem("填充孔洞 (Fill Hole)") # 2202
    shpFillHolePb.setData({"ID":2202}, Qt.ItemDataRole.UserRole)
    shpFillHolePb.setIcon(QIcon(":/img/resources/shpProcess/shp_removeHole.png"))
    resList.append(shpFillHolePb)

    shpOrthPb = QStandardItem("矢量正交 (Vector Orth)") # 2203
    shpOrthPb.setData({"ID":2203}, Qt.ItemDataRole.UserRole)
    shpOrthPb.setIcon(QIcon(":/img/resources/shpProcess/shp_orth.png"))
    resList.append(shpOrthPb)

    shpSimplyPb = QStandardItem("矢量简化 (Vector Simply)") # 2204
    shpSimplyPb.setData({"ID":2204}, Qt.ItemDataRole.UserRole)
    shpSimplyPb.setIcon(QIcon(":/img/resources/shpProcess/shp_simply.png"))
    resList.append(shpSimplyPb)

    shpSmoothPb = QStandardItem("矢量平滑 (Vector Smooth)") # 2205
    shpSmoothPb.setData({"ID":2205}, Qt.ItemDataRole.UserRole)
    shpSmoothPb.setIcon(QIcon(":/img/resources/shpProcess/shp_smoth.png"))
    resList.append(shpSmoothPb)

    shpReprojectPb = QStandardItem("矢量重投影 (Vector Reproject)") # 2206
    shpReprojectPb.setData({"ID":2206}, Qt.ItemDataRole.UserRole)
    shpReprojectPb.setIcon(QIcon(":/img/resources/reproject.png"))
    resList.append(shpReprojectPb)

    shpCalAreaPb = QStandardItem("计算面积 (Vector CalArea)") # 2207
    shpCalAreaPb.setData({"ID":2207}, Qt.ItemDataRole.UserRole)
    shpCalAreaPb.setIcon(QIcon(":/img/resources/shpProcess/shp_calArea.png"))
    resList.append(shpCalAreaPb)

    shpFixPb = QStandardItem("修正几何 (Vector Fix)") # 2208
    shpFixPb.setData({"ID":2208}, Qt.ItemDataRole.UserRole)
    shpFixPb.setIcon(QIcon(":/img/resources/shpProcess/shp_topologic.png"))
    resList.append(shpFixPb)

    return resList



def getItems_shp_trans() -> List[QStandardItem]:
    resList = []

    shp2RasterPb = QStandardItem("矢量栅格化 (Vector Rasterization)") # 2301
    shp2RasterPb.setData({"ID":2301}, Qt.ItemDataRole.UserRole)
    shp2RasterPb.setIcon(QIcon(":/img/resources/shpProcess/shp_2raster.png"))
    resList.append(shp2RasterPb)

    shpExportPb = QStandardItem("矢量导出 (Export Vector)") # 2302
    shpExportPb.setData({"ID":2302}, Qt.ItemDataRole.UserRole)
    shpExportPb.setIcon(QIcon(":/img/resources/export.png"))
    resList.append(shpExportPb)

    shp2SinglePb = QStandardItem("多部件转单部件 (Multi to Single)") # 2303
    shp2SinglePb.setData({"ID":2303}, Qt.ItemDataRole.UserRole)
    shp2SinglePb.setIcon(QIcon(":/img/resources/shpProcess/shp_split.png"))
    resList.append(shp2SinglePb)

    shpCalCentroidPb = QStandardItem("计算质心 (Cal Centroid)") # 2304
    shpCalCentroidPb.setData({"ID":2304}, Qt.ItemDataRole.UserRole)
    shpCalCentroidPb.setIcon(QIcon(":/img/resources/shpProcess/shp_calCentorid.png"))
    resList.append(shpCalCentroidPb)

    return resList



def getItems_shp_analysis() -> List[QStandardItem]:
    resList = []

    # shpCommonProcessPb = QStandardItem(["矢量后处理(Vector Post-Processing)"],) # 2401
    # shpCommonProcessPb.setData({"ID":2401}, Qt.ItemDataRole.UserRole)
    # shpCommonProcessPb.setIcon(QIcon(":/img/resources/shpProcess/commonProcess.png"))
    # resList.append(shpCommonProcessPb)

    shpChangeAnalysisPb = QStandardItem("变化分析 (Change Analysis)") # 2402
    shpChangeAnalysisPb.setData({"ID":2402}, Qt.ItemDataRole.UserRole)
    shpChangeAnalysisPb.setIcon(QIcon(":/img/resources/shpProcess/commonProcess.png"))
    resList.append(shpChangeAnalysisPb)

    return resList



def getItems_tif_common() -> List[QStandardItem]:
    resList = []

    rasterClipPb = QStandardItem("栅格裁剪 (Raster Clip)") # 1101
    rasterClipPb.setData({"ID":1101}, Qt.ItemDataRole.UserRole)
    rasterClipPb.setIcon(QIcon(":/img/resources/tifProcess/tif_clip.png"))
    resList.append(rasterClipPb)

    rasterMergePb = QStandardItem("栅格合并 (Raster Merge)") # 1102
    rasterMergePb.setData({"ID":1102}, Qt.ItemDataRole.UserRole)
    rasterMergePb.setIcon(QIcon(":/img/resources/tifProcess/tif_merge.png"))
    resList.append(rasterMergePb)

    rasterBuildOverviewPb = QStandardItem("建金字塔 (Generate OVR)") # 1103
    rasterBuildOverviewPb.setData({"ID":1103}, Qt.ItemDataRole.UserRole)
    rasterBuildOverviewPb.setIcon(QIcon(":/img/resources/tifProcess/tif_ovr.png"))
    resList.append(rasterBuildOverviewPb)

    rasterReprojectPb = QStandardItem("栅格重投影 (Raster Reproject)") # 1104
    rasterReprojectPb.setData({"ID":1104}, Qt.ItemDataRole.UserRole)
    rasterReprojectPb.setIcon(QIcon(":/img/resources/reproject.png"))
    resList.append(rasterReprojectPb)

    return resList



def getItems_tif_trans() -> List[QStandardItem]:
    resList = []

    raster2ShpPb = QStandardItem("栅格矢量化 (Raster vectorization)") # 1201
    raster2ShpPb.setData({"ID":1201}, Qt.ItemDataRole.UserRole)
    raster2ShpPb.setIcon(QIcon(":/img/resources/tifProcess/tif_2shp.png"))
    resList.append(raster2ShpPb)

    rasterExportPb = QStandardItem("栅格导出 (Export Raster)") # 1202
    rasterExportPb.setData({"ID":1202}, Qt.ItemDataRole.UserRole)
    rasterExportPb.setIcon(QIcon(":/img/resources/export.png"))
    resList.append(rasterExportPb)

    raster16to8Pb = QStandardItem("16位栅格降位 (Raster Uint16 to Uint8)") # 1203
    raster16to8Pb.setData({"ID":1203}, Qt.ItemDataRole.UserRole)
    raster16to8Pb.setIcon(QIcon(":/img/resources/rollerDown.png"))
    resList.append(raster16to8Pb)

    rasterReprojectPb = QStandardItem("波段重组合 (Raster Reproject)") # 1204
    rasterReprojectPb.setData({"ID":1204}, Qt.ItemDataRole.UserRole)
    rasterReprojectPb.setIcon(QIcon(":/img/resources/reproject.png"))
    resList.append(rasterReprojectPb)

    return resList



def getItems_tif_cal() -> List[QStandardItem]:
    resList = []

    rasterCalcPb = QStandardItem("栅格计算 (Raster Calculator)") # 1301
    rasterCalcPb.setData({"ID":1301}, Qt.ItemDataRole.UserRole)
    rasterCalcPb.setIcon(QIcon(":/img/resources/tifProcess/calNorm.png"))
    resList.append(rasterCalcPb)

    rasterZonalStaticPb = QStandardItem("栅格分区统计 (Raster Zonal Static)") # 1302
    rasterZonalStaticPb.setData({"ID":1302}, Qt.ItemDataRole.UserRole)
    rasterZonalStaticPb.setIcon(QIcon(":/img/resources/tifProcess/tif_calStatic.png"))
    resList.append(rasterZonalStaticPb)

    return resList
