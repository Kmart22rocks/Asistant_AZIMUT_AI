#include "StatusIndicator.h"
#include <QPainter>

StatusIndicator::StatusIndicator(QWidget *parent)
    : QWidget(parent),
      m_state(Red),
      m_blinkTimer(new QTimer(this)),
      m_blinkPhase(false) {
    setFixedSize(18, 18);
    connect(m_blinkTimer, &QTimer::timeout, this, [this]() {
        m_blinkPhase = !m_blinkPhase;
        update();
    });
}

void StatusIndicator::setState(State state) {
    m_state = state;
    if (m_state == BlinkingBlue) {
        if (!m_blinkTimer->isActive()) {
            m_blinkTimer->start(350);
        }
    } else {
        m_blinkTimer->stop();
    }
    update();
}

void StatusIndicator::paintEvent(QPaintEvent *) {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    QColor color;
    switch (m_state) {
        case Red: color = QColor("#E53935"); break;
        case Yellow: color = QColor("#FDD835"); break;
        case Green: color = QColor("#43A047"); break;
        case BlinkingBlue:
            color = m_blinkPhase ? QColor("#1E88E5") : QColor("#90CAF9");
            break;
    }

    p.setPen(QPen(QColor("#555555"), 1));
    p.setBrush(color);
    p.drawEllipse(2, 2, width() - 4, height() - 4);
}