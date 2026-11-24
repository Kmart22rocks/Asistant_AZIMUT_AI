#pragma once
#include <QMainWindow>
#include <QTextEdit>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QTabWidget>
#include <QSlider>
#include <QComboBox>
#include <QJsonObject>
#include <QTimer>
#include "StatusIndicator.h"
#include "core/ProcessManager.h"
#include "network/KompasBridge.h"
#include "network/OllamaClient.h"

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

protected:
    bool event(QEvent *event) override;
    bool nativeEvent(const QByteArray &eventType, void *message, qintptr *result) override;

private slots:
    void onToggleConnect();
    void onUndoClicked();
    void onClearPartClicked();
    void onSendMessage();
    void onStatusUpdated(const QString &indicator, const QString &text, const QJsonObject &context);
    void onThinkingTick();

private:
    QWidget* createChatTab();
    QWidget* createManualTab();
    QWidget* createSettingsTab();
    void startThinkingAnimation();
    void finishThinkingWithText(const QString &htmlText);
    void toggleAssistantWindow();

    StatusIndicator *m_indicator;
    QLabel *m_statusLabel;
    QPushButton *m_undoBtn;
    QPushButton *m_connectBtn;
    QTabWidget *m_tabs;
    QTextEdit *m_chatHistory;
    QLineEdit *m_inputField;
    QPushButton *m_sendBtn;

    QSlider *m_opacitySlider;
    QLabel *m_opacityValueLabel;
    double m_inactiveOpacity;

    ProcessManager *m_procManager;
    KompasBridge *m_kompasBridge;
    OllamaClient *m_ollamaClient;
    QJsonObject m_cadContext;
    bool m_isConnected;

    QTimer *m_thinkingTimer;
    QTimer *m_syncTimer;
    int m_thinkingDots;
};