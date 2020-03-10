# -*- coding: utf-8 -*-
# @Author  : llc
# @Time    : 2020/3/10 14:58

import os
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor, QPixmap
from qgis.gui import QgsMapTool
from qgis.core import QgsProject, QgsMapSettings, QgsMapRendererParallelJob
from .swipe_map import SwipeMap


class MapSwipeTool(QgsMapTool):
    def __init__(self, plugin_path, combobox, iface):
        super(MapSwipeTool, self).__init__(iface.mapCanvas())
        self.combobox = combobox
        self.map_canvas = iface.mapCanvas()
        self.view = iface.layerTreeView()
        self.swipe = SwipeMap(self.map_canvas)
        self.hasSwipe = None
        self.start_point = QPoint()

        self.cursorSV = QCursor(QPixmap(os.path.join(plugin_path, 'images/split_v.png')))
        self.cursorSH = QCursor(QPixmap(os.path.join(plugin_path, 'images/split_h.png')))
        self.cursorUP = QCursor(QPixmap(os.path.join(plugin_path, 'images/up.png')))
        self.cursorDOWN = QCursor(QPixmap(os.path.join(plugin_path, 'images/down.png')))
        self.cursorLEFT = QCursor(QPixmap(os.path.join(plugin_path, 'images/left.png')))
        self.cursorRIGHT = QCursor(QPixmap(os.path.join(plugin_path, 'images/right.png')))

    def activate(self):
        self.map_canvas.setCursor(QCursor(Qt.CrossCursor))
        self._connect()
        self.hasSwipe = False
        self.setLayersSwipe()

    def canvasPressEvent(self, e):
        self.hasSwipe = True
        direction = None
        w, h = self.map_canvas.width(), self.map_canvas.height()
        if 0.25 * w < e.x() < 0.75 * w and e.y() < 0.5 * h:
            direction = 0  # '⬇'
            self.swipe.isVertical = False
        if 0.25 * w < e.x() < 0.75 * w and e.y() > 0.5 * h:
            direction = 1  # '⬆'
            self.swipe.isVertical = False
        if e.x() < 0.25 * w:
            direction = 2  # '➡'
            self.swipe.isVertical = True
        if e.x() > 0.75 * w:
            direction = 3  # '⬅'
            self.swipe.isVertical = True

        self.swipe.set_direction(direction)
        self.map_canvas.setCursor(self.cursorSV if self.swipe.isVertical else self.cursorSH)
        self.swipe.set_img_extent(e.x(), e.y())

    def canvasReleaseEvent(self, e):
        self.hasSwipe = False
        self.canvasMoveEvent(e)
        # 鼠标释放后，移除绘制的线
        self.swipe.set_img_extent(-9999, -9999)

    def canvasMoveEvent(self, e):
        if self.hasSwipe:
            self.swipe.set_img_extent(e.x(), e.y())
        else:
            # 设置当前cursor
            w, h = self.map_canvas.width(), self.map_canvas.height()
            if e.x() < 0.25 * w:
                self.canvas().setCursor(self.cursorRIGHT)
            if e.x() > 0.75 * w:
                self.canvas().setCursor(self.cursorLEFT)
            if 0.25 * w < e.x() < 0.75 * w and e.y() < 0.5 * h:
                self.canvas().setCursor(self.cursorDOWN)
            if 0.25 * w < e.x() < 0.75 * w and e.y() > 0.5 * h:
                self.canvas().setCursor(self.cursorUP)

    def _connect(self, isConnect=True):
        signal_slot = (
            {'signal': self.map_canvas.mapCanvasRefreshed, 'slot': self.setMap},
            {'signal': self.combobox.currentIndexChanged, 'slot': self.setLayersSwipe},
            {'signal': QgsProject.instance().removeAll, 'slot': self.disable}
        )
        if isConnect:
            for item in signal_slot:
                item['signal'].connect(item['slot'])
        else:
            for item in signal_slot:
                item['signal'].disconnect(item['slot'])

    def setLayersSwipe(self, ):
        current_layer = QgsProject.instance().mapLayersByName(self.combobox.currentText())
        if len(current_layer) == 0:
            return
        layers = QgsProject.instance().layerTreeRoot().layerOrder()
        layer_list = []
        for layer in layers:
            if layer.id() == current_layer[0].id():
                continue
            layer_list.append(layer)
        self.swipe.clear()
        self.swipe.setLayersId(layer_list)
        self.setMap()

    def disable(self):
        self.swipe.clear()
        self.hasSwipe = False

    def deactivate(self):
        self.deactivated.emit()
        self.swipe.clear()
        self._connect(False)

    def setMap(self):
        def finished():
            self.swipe.setContent(job.renderedImage(), self.map_canvas.extent())

        if len(self.swipe.layers) == 0:
            return

        settings = QgsMapSettings(self.map_canvas.mapSettings())
        settings.setLayers(self.swipe.layers)

        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.finished.connect(finished)
        job.waitForFinished()