from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor
from PyQt6.QtCore import Qt

def create_gear_icon(color: str = "#d4c8e3") -> QIcon:
    pixmap = QPixmap(22, 22)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    icon_font = QFont()
    icon_font.setPointSize(18)
    painter.setFont(icon_font)
    painter.setPen(QColor(color))
    
    draw_rect = pixmap.rect()
    draw_rect.translate(0, -3) 
    
    painter.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, "⚙")
    painter.end()
    
    return QIcon(pixmap)
