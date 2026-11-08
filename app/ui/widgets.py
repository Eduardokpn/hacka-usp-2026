"""Componentes desenhados à mão: botões circulares, ícones, spinner e toast."""
from __future__ import annotations

from PySide6.QtCore import (
    Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QGraphicsOpacityEffect, QLabel, QWidget

from app.ui import theme


def _lighter(hex_color: str, factor: int = 112) -> QColor:
    return QColor(hex_color).lighter(factor)


# ------------------------------------------------------------ ícones ----

def draw_icon(p: QPainter, kind: str, rect: QRectF, color: QColor) -> None:
    """Desenha o ícone `kind` centrado em `rect` (coordenadas em 0..1 do rect)."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

    def pt(fx, fy):
        return QPointF(x + fx * w, y + fy * h)

    pen = QPen(color, max(2.0, w * 0.09), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "x":
        p.drawLine(pt(0.25, 0.25), pt(0.75, 0.75))
        p.drawLine(pt(0.75, 0.25), pt(0.25, 0.75))
    elif kind == "check":
        path = QPainterPath(pt(0.2, 0.52))
        path.lineTo(pt(0.42, 0.72))
        path.lineTo(pt(0.8, 0.3))
        p.drawPath(path)
    elif kind == "mic":
        pen.setWidthF(max(2.0, w * 0.075))
        p.setPen(pen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x + 0.38 * w, y + 0.12 * h, 0.24 * w, 0.44 * h), 0.12 * w, 0.12 * w)
        p.setBrush(Qt.NoBrush)
        arc = QRectF(x + 0.26 * w, y + 0.28 * h, 0.48 * w, 0.42 * h)
        p.drawArc(arc, 180 * 16, 180 * 16)
        p.drawLine(pt(0.5, 0.70), pt(0.5, 0.84))
        p.drawLine(pt(0.36, 0.86), pt(0.64, 0.86))
    elif kind == "pause":
        pen.setWidthF(w * 0.14)
        p.setPen(pen)
        p.drawLine(pt(0.38, 0.28), pt(0.38, 0.72))
        p.drawLine(pt(0.62, 0.28), pt(0.62, 0.72))
    elif kind == "play":
        p.setBrush(color)
        pen.setWidthF(w * 0.06)
        p.setPen(pen)
        path = QPainterPath(pt(0.36, 0.25))
        path.lineTo(pt(0.76, 0.5))
        path.lineTo(pt(0.36, 0.75))
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "sliders":
        pen.setWidthF(max(2.0, w * 0.08))
        p.setPen(pen)
        for fx, knob in ((0.25, 0.62), (0.5, 0.32), (0.75, 0.55)):
            p.drawLine(pt(fx, 0.12), pt(fx, 0.88))
            p.setBrush(QColor(theme.BG))
            p.drawEllipse(pt(fx, knob), w * 0.09, w * 0.09)
            p.setBrush(Qt.NoBrush)
    elif kind == "copy":
        pen.setWidthF(max(1.5, w * 0.07))
        p.setPen(pen)
        p.drawRoundedRect(QRectF(x + 0.32 * w, y + 0.12 * h, 0.5 * w, 0.58 * h), 0.08 * w, 0.08 * w)
        p.setBrush(QColor(theme.SURFACE))
        p.drawRoundedRect(QRectF(x + 0.18 * w, y + 0.3 * h, 0.5 * w, 0.58 * h), 0.08 * w, 0.08 * w)
    elif kind == "done":
        pen.setWidthF(max(1.5, w * 0.09))
        p.setPen(pen)
        path = QPainterPath(pt(0.22, 0.52))
        path.lineTo(pt(0.42, 0.7))
        path.lineTo(pt(0.78, 0.32))
        p.drawPath(path)


# ---------------------------------------------------- botão circular ----

class CircleButton(QAbstractButton):
    """Botão redondo com ícone, hover suave e pulso opcional."""

    def __init__(self, color: str, icon: str, diameter: int, parent=None):
        super().__init__(parent)
        self._color = color
        self._icon = icon
        self._d = diameter
        self._hover = 0.0
        self._pulse = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(QSize(diameter + 40, diameter + 40))

        self._hover_anim = QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(140)

        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(1600)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pulse_anim.valueChanged.connect(self._on_pulse)

    # propriedades animáveis
    def _get_hover(self):
        return self._hover

    def _set_hover(self, v):
        self._hover = v
        self.update()

    hover = Property(float, _get_hover, _set_hover)

    def _on_pulse(self, v):
        self._pulse = v
        self.update()

    def set_icon(self, icon: str):
        self._icon = icon
        self.update()

    def set_pulsing(self, on: bool):
        if on and self._pulse_anim.state() != QVariantAnimation.Running:
            self._pulse_anim.start()
        elif not on:
            self._pulse_anim.stop()
            self._pulse = 0.0
            self.update()

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def sizeHint(self):
        return QSize(self._d + 40, self._d + 40)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self._d / 2
        enabled = self.isEnabled()
        base = QColor(self._color) if enabled else QColor("#D5D9DE")

        if self._pulse > 0 and enabled:
            ring = QColor(self._color)
            ring.setAlphaF(0.35 * (1 - self._pulse))
            p.setPen(Qt.NoPen)
            p.setBrush(ring)
            rr = r + 18 * self._pulse
            p.drawEllipse(c, rr, rr)

        # sombra suave
        if enabled:
            shadow = QColor(0, 0, 0, int(22 + 18 * self._hover))
            p.setPen(Qt.NoPen)
            p.setBrush(shadow)
            p.drawEllipse(QPointF(c.x(), c.y() + 3), r, r)

        fill = QColor(base)
        if enabled and self._hover > 0:
            hl = _lighter(self._color, 118) if self._color != theme.DARK else QColor("#33393F")
            fill = QColor(
                int(base.red() + (hl.red() - base.red()) * self._hover),
                int(base.green() + (hl.green() - base.green()) * self._hover),
                int(base.blue() + (hl.blue() - base.blue()) * self._hover),
            )
        if self.isDown() and enabled:
            fill = fill.darker(110)
        grow = 2 * self._hover if enabled else 0
        p.setBrush(fill)
        p.drawEllipse(c, r + grow, r + grow)

        s = self._d * 0.46
        draw_icon(p, self._icon, QRectF(c.x() - s / 2, c.y() - s / 2, s, s), QColor("white"))


class IconButton(QAbstractButton):
    """Botão plano com ícone (configurações, copiar)."""

    def __init__(self, icon: str, size: int = 36, color: str = theme.INK, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._color = color
        self._hovered = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)

    def set_icon(self, icon: str, color: str | None = None):
        self._icon = icon
        if color:
            self._color = color
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hovered and self.isEnabled():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 14))
            p.drawRoundedRect(self.rect(), 8, 8)
        color = QColor(self._color) if self.isEnabled() else QColor("#C2C8CE")
        m = self.width() * 0.2
        draw_icon(p, self._icon, QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m), color)


# --------------------------------------------------------- spinner ----

class Spinner(QWidget):
    def __init__(self, size: int = 34, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(16)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = 4
        rect = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)
        p.setPen(QPen(QColor(theme.LINE), 3.5))
        p.drawEllipse(rect)
        p.setPen(QPen(QColor(theme.ACCENT), 3.5, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, -self._angle * 16, 100 * 16)


# ----------------------------------------------------------- toast ----

class Toast(QLabel):
    """Mensagem curta flutuando no rodapé da janela."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{theme.DARK}; color:white; padding:9px 18px; border-radius:18px;"
            "font-size:10pt; font-weight:600;"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fx)
        self._anim = QPropertyAnimation(self._fx, b"opacity", self)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, ms: int = 1400):
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 64)
        self.raise_()
        self.show()
        self._anim.stop()
        self._anim.setDuration(150)
        self._anim.setStartValue(self._fx.opacity() if self.isVisible() else 0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._hide_timer.start(ms)

    def _fade_out(self):
        self._anim.stop()
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()
