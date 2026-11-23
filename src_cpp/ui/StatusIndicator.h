#pragma once
#include <QWidget>
#include <QTimer>

class StatusIndicator : public QWidget {
    Q_OBJECT
public:
    enum State { Red, Yellow, Green, BlinkingBlue };

    explicit StatusIndicator(QWidget *parent = nullptr);
    void setState(State state);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    State m_state;
    QTimer *m_blinkTimer;
    bool m_blinkPhase;
};